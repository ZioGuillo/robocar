from fastapi import APIRouter
from app import telemetry
from app.hardware import rrb3_driver as driver

router = APIRouter(prefix="/api/telemetry")


@router.get("")
def get_telemetry():
    data = telemetry.snapshot()
    data["battery_v"] = driver.get_battery_voltage()
    data["battery_motor_ok"] = driver.available
    data["battery_pi_ok"] = True
    return data
