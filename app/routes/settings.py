from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import db
from app.hardware import camera_driver, ml_driver
from app.templates_env import templates

router = APIRouter(prefix="/settings")


@router.get("")
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "base.html", {
        "camera_stream_url": "",
        "camera_available": camera_driver.available,
        "motor_speed_default": 0.75,
        "user": dict(request.state.user),
        "github_enabled": db.get_setting("github_oauth_enabled") == "true",
        "github_client_id": db.get_setting("github_client_id"),
        "github_users": [dict(u) for u in db.get_all_github_users()],
        "active_tab": "settings",
        "ml_available": ml_driver.available,
        "ml_library_available": ml_driver.library_available,
        "ml_model_found": ml_driver.model_found,
        "ml_enabled": db.get_setting("ml_detection_enabled") == "true",
    })


@router.post("/users/{user_id}/approve")
async def approve_user(user_id: int, request: Request):
    db.set_user_role(user_id, "approved")
    return RedirectResponse("/?tab=settings", status_code=302)


@router.post("/users/{user_id}/revoke")
async def revoke_user(user_id: int, request: Request):
    db.set_user_role(user_id, "revoked")
    return RedirectResponse("/?tab=settings", status_code=302)


@router.post("/github")
async def save_github_settings(
    request: Request,
    github_enabled: str = Form(default=""),
    github_client_id: str = Form(default=""),
    github_client_secret: str = Form(default=""),
):
    db.set_setting("github_oauth_enabled", "true" if github_enabled == "on" else "false")
    db.set_setting("github_client_id", github_client_id.strip())
    if github_client_secret.strip():
        db.set_setting("github_client_secret", github_client_secret.strip())
    return RedirectResponse("/?tab=settings&saved=github", status_code=302)


@router.post("/ml")
async def save_ml_settings(
    request: Request,
    ml_enabled: str = Form(default=""),
):
    value = "true" if ml_enabled == "on" else "false"
    db.set_setting("ml_detection_enabled", value)
    if ml_driver.available:
        ml_driver.set_enabled(value == "true")
    return RedirectResponse("/?tab=settings&saved=ml", status_code=302)


@router.post("/icon")
async def save_icon(request: Request, icon: str = Form(...)):
    user = request.state.user
    try:
        db.set_user_icon(user["id"], icon)
    except ValueError:
        pass
    return RedirectResponse("/", status_code=302)


@router.post("/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    admin = db.get_user_by_username("admin")
    if not admin or not db.verify_password(current_password, admin["password_hash"]):
        return RedirectResponse("/?tab=settings&error=wrong_password", status_code=302)
    if new_password != confirm_password:
        return RedirectResponse("/?tab=settings&error=password_mismatch", status_code=302)
    if len(new_password) < 8:
        return RedirectResponse("/?tab=settings&error=password_too_short", status_code=302)
    db.update_admin_password(db.hash_password(new_password))
    return RedirectResponse("/?tab=settings&saved=password", status_code=302)
