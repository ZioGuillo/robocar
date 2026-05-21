import asyncio
import importlib
import json
import pkgutil
from base64 import b64decode
from contextlib import asynccontextmanager
from pathlib import Path

import itsdangerous
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.routes as _routes_pkg
from app.config import settings
from app.hardware import servo_driver, rrb3_driver as driver, camera_driver, ml_driver
from app.security import rate_limiter
from app.templates_env import templates
from app import db


async def _ready_wiggle():
    if not driver.available:
        return
    speed = 0.4
    try:
        driver.set_motors(speed / 2, 0, speed / 2, 0)
        await asyncio.sleep(0.3)
        driver.set_motors(0, 0, 0, 0)
        await asyncio.sleep(0.1)
        driver.set_motors(speed / 2, 1, speed / 2, 1)
        await asyncio.sleep(0.3)
        driver.set_motors(0, 0, 0, 0)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if servo_driver.available:
        servo_driver.init(settings.pan_servo_pin, settings.tilt_servo_pin)
    camera_driver.start()
    ml_driver.start()
    await _ready_wiggle()
    yield
    ml_driver.stop()
    camera_driver.stop()


app = FastAPI(lifespan=lifespan)
_https_only = settings.base_url.startswith("https://") if settings.base_url else False
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key, https_only=_https_only)

_PUBLIC_PATHS = {"/login", "/auth/github", "/auth/callback", "/api/ping"}
_signer = itsdangerous.TimestampSigner(settings.session_secret_key)


def _get_session_token(request: Request) -> str | None:
    """Decode the session cookie directly (works inside BaseHTTPMiddleware)."""
    raw = request.cookies.get("session")
    if not raw:
        return None
    try:
        unsigned = _signer.unsign(raw, max_age=14 * 24 * 60 * 60)
        data = json.loads(b64decode(unsigned))
        return data.get("token")
    except Exception:
        return None


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path

    if path.startswith("/static") or path in _PUBLIC_PATHS:
        return await call_next(request)

    # Brute-force protection on login
    if path == "/login" and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(f"login:{client_ip}", 5):  # 5 attempts/second
            return JSONResponse(
                {"ok": False, "message": "Too many login attempts — please wait"},
                status_code=429,
            )

    token = _get_session_token(request)
    user = db.get_session_user(token) if token else None

    if user is None:
        return RedirectResponse("/login", status_code=302)

    if path.startswith("/settings") and path != "/settings/icon" and user["role"] != "admin":
        return Response("Forbidden", status_code=403)

    request.state.user = user

    if (settings.motor_rate_limit > 0
            and path.startswith("/api/motors/")
            and request.method == "POST"):
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(f"motor:{client_ip}", settings.motor_rate_limit):
            return JSONResponse(
                {"ok": False, "message": "Rate limit exceeded — slow down"},
                status_code=429,
            )

    return await call_next(request)


for _mod_info in pkgutil.iter_modules(_routes_pkg.__path__):
    if _mod_info.name.startswith("_"):
        continue
    _mod = importlib.import_module(f"app.routes.{_mod_info.name}")
    _router = getattr(_mod, "router", None)
    if _router is not None:
        app.include_router(_router)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def index(request: Request):
    user = request.state.user
    ctx = {
        "camera_stream_url": settings.camera_stream_url,
        "camera_available": camera_driver.available,
        "motor_speed_default": settings.motor_speed_default,
        "user": dict(user),
    }
    if user["role"] == "admin":
        ctx.update({
            "github_enabled": db.get_setting("github_oauth_enabled") == "true",
            "github_client_id": db.get_setting("github_client_id"),
            "github_users": [dict(u) for u in db.get_all_github_users()],
            "ml_available": ml_driver.available,
            "ml_library_available": ml_driver.library_available,
            "ml_model_found": ml_driver.model_found,
            "ml_enabled": db.get_setting("ml_detection_enabled") == "true",
        })
    return templates.TemplateResponse(request, "base.html", ctx)
