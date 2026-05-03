available = False
_rr = None

try:
    import rrb3 as rrb
    _rr = rrb.RRB3(6, 3)
    available = True
except Exception:
    pass


def set_motors(speed1: float, dir1: int, speed2: float, dir2: int) -> None:
    if not available:
        raise RuntimeError("rrb3 not available")
    _rr.set_motors(speed1, dir1, speed2, dir2)


def get_distance() -> float:
    """Returns sonar distance in cm. Returns inf when hardware unavailable."""
    if not available:
        return float("inf")
    try:
        return _rr.get_distance()
    except Exception:
        return float("inf")


def get_battery_voltage() -> float | None:
    """Returns battery voltage in volts, or None when unavailable."""
    if not available:
        return None
    try:
        return float(_rr.get_battery_voltage())
    except Exception:
        return None
