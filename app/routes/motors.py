import asyncio
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.hardware import rrb3_driver as driver
from app.config import settings
from app import telemetry, metrics as m

router = APIRouter(prefix="/api/motors")

VALID_ACTIONS = {"forward", "reverse", "left", "right", "stop"}

# M1 (left): dir=1=forward, dir=0=reverse
# M2 (right): dir=0=forward, dir=1=reverse  (wired with reversed polarity)
_M1_FWD, _M1_REV = 1, 0
_M2_FWD, _M2_REV = 0, 1


class MotorRequest(BaseModel):
    speed: float | None = Field(default=None, ge=0.0, le=1.0)


@router.post("/auto")
async def auto_drive():
    # ── IMPLEMENT: Auto-Drive ──────────────────────────────────────────────────
    # Goal: autonomous obstacle-avoidance loop (runs until client disconnects
    # or a stop signal is received).
    #
    # Suggested steps:
    #   1. Use a streaming response (StreamingResponse + asyncio.Queue) so the
    #      client receives real-time status updates while the car roams.
    #   2. Loop:
    #        dist = driver.get_distance()
    #        if dist < settings.obstacle_threshold_cm: turn right/left
    #        else: drive forward at settings.motor_speed_default
    #        await asyncio.sleep(0.1)   # control loop tick
    #   3. Yield JSON events per tick so the UI can show distance + action.
    #   4. Stop motors when the generator exits (try/finally).
    #
    # Useful imports already at the top of this file:
    #   driver, settings, asyncio
    # ──────────────────────────────────────────────────────────────────────────
    raise HTTPException(
        status_code=501,
        detail={"ok": False, "message": "Auto-drive not yet implemented"},
    )


@router.post("/{action}")
async def motor_action(action: str, body: MotorRequest = None):
    if body is None:
        body = MotorRequest()
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "message": f"Unknown action: {action}"},
        )
    if not driver.available:
        raise HTTPException(
            status_code=503,
            detail={"ok": False, "message": "GPIO unavailable: rrb3 not initialized"},
        )
    speed = body.speed if body.speed is not None else settings.motor_speed_default
    t0 = time.monotonic()
    try:
        if action == "forward":
            dist = driver.get_distance()
            if 0 < dist < settings.obstacle_threshold_cm:
                driver.set_motors(0, 0, 0, 0)
                driver.set_motors(speed / 2, _M1_FWD, speed / 2, _M2_REV)  # turn right to evade
                await asyncio.sleep(0.5)
                driver.set_motors(0, 0, 0, 0)
                telemetry.record_obstacle(dist)
                telemetry.record_command((time.monotonic() - t0) * 1000, action, speed)
                m.MOTOR_CMDS_TOTAL.labels(action=action).inc()
                m.MOTOR_BLOCKED_TOTAL.inc()
                m.OBSTACLES_TOTAL.inc()
                m.SONAR_DISTANCE_CM.set(dist)
                return {
                    "ok": False,
                    "action": "forward",
                    "blocked": True,
                    "message": f"Obstacle detected ({dist:.0f} cm) — stopping",
                }
            driver.set_motors(speed, _M1_FWD, speed, _M2_FWD)
        elif action == "reverse":
            driver.set_motors(speed, _M1_REV, speed, _M2_REV)
        elif action == "left":
            driver.set_motors(speed / 2, _M1_REV, speed / 2, _M2_FWD)
        elif action == "right":
            driver.set_motors(speed / 2, _M1_FWD, speed / 2, _M2_REV)
        elif action == "stop":
            driver.set_motors(0, 0, 0, 0)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail={"ok": False, "message": str(e)})
    telemetry.record_command((time.monotonic() - t0) * 1000, action, speed)
    m.MOTOR_CMDS_TOTAL.labels(action=action).inc()
    return {"ok": True, "action": action}
