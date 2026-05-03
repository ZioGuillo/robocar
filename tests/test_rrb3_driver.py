import pytest
import app.hardware.rrb3_driver as driver


def test_set_motors_raises_when_unavailable():
    original = driver.available
    driver.available = False
    try:
        with pytest.raises(RuntimeError, match="rrb3 not available"):
            driver.set_motors(1.0, 0, 1.0, 0)
    finally:
        driver.available = original


def test_available_is_false_without_hardware():
    assert driver.available is False


def test_get_distance_returns_inf_when_unavailable():
    original = driver.available
    driver.available = False
    try:
        assert driver.get_distance() == float("inf")
    finally:
        driver.available = original
