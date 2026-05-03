from unittest.mock import patch, call


def test_wiggle_fires_when_hardware_available():
    with patch("app.hardware.rrb3_driver.available", True), \
         patch("app.hardware.rrb3_driver.set_motors") as mock_motors, \
         patch("app.hardware.servo_driver.init"), \
         patch("app.hardware.servo_driver.available", False):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app):
            pass
    calls = mock_motors.call_args_list
    # must stop at end (last call is all zeros)
    assert calls[-1] == call(0, 0, 0, 0)
    # must have at least one left and one right move
    assert len(calls) >= 3


def test_wiggle_skipped_when_hardware_unavailable():
    with patch("app.hardware.rrb3_driver.available", False), \
         patch("app.hardware.rrb3_driver.set_motors") as mock_motors, \
         patch("app.hardware.servo_driver.init"), \
         patch("app.hardware.servo_driver.available", False):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app):
            pass
    mock_motors.assert_not_called()
