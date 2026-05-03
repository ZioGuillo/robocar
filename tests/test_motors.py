from unittest.mock import patch

# M1: dir=1=fwd, dir=0=rev  |  M2: dir=0=fwd, dir=1=rev  (M2 wired reversed)


def test_forward(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.get_distance", return_value=float("inf")), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/forward", json={"speed": 0.8})
        assert r.status_code == 200
        assert r.json() == {"ok": True, "action": "forward"}
        mock.assert_called_once_with(0.8, 1, 0.8, 0)


def test_forward_blocked_by_obstacle(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.get_distance", return_value=15.0), \
         patch("app.routes.motors.driver.set_motors") as mock_set, \
         patch("app.routes.motors.settings.obstacle_threshold_cm", 20.0), \
         patch("app.routes.motors.asyncio.sleep"):
        r = client.post("/api/motors/forward", json={"speed": 0.75})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert data["blocked"] is True
        assert "15" in data["message"]
        assert "obstacle" in data["message"].lower()
        calls = mock_set.call_args_list
        assert calls[0].args == (0, 0, 0, 0)
        assert calls[-1].args == (0, 0, 0, 0)


def test_forward_clears_path(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.get_distance", return_value=100.0), \
         patch("app.routes.motors.settings.obstacle_threshold_cm", 20.0), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/forward", json={"speed": 0.75})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        mock.assert_called_once_with(0.75, 1, 0.75, 0)


def test_reverse(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/reverse", json={"speed": 0.5})
        assert r.status_code == 200
        mock.assert_called_once_with(0.5, 0, 0.5, 1)


def test_left(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/left", json={"speed": 0.6})
        assert r.status_code == 200
        mock.assert_called_once_with(0.3, 0, 0.3, 0)


def test_right(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/right", json={"speed": 0.6})
        assert r.status_code == 200
        mock.assert_called_once_with(0.3, 1, 0.3, 1)


def test_stop(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.set_motors") as mock:
        r = client.post("/api/motors/stop")
        assert r.status_code == 200
        mock.assert_called_once_with(0, 0, 0, 0)


def test_auto_returns_501(client):
    r = client.post("/api/motors/auto")
    assert r.status_code == 501
    assert r.json()["detail"]["ok"] is False


def test_unknown_action_returns_400(client):
    with patch("app.routes.motors.driver.available", True):
        r = client.post("/api/motors/dance")
        assert r.status_code == 400


def test_motor_unavailable_returns_503(client):
    with patch("app.routes.motors.driver.available", False):
        r = client.post("/api/motors/forward")
        assert r.status_code == 503


def test_speed_defaults_to_config(client):
    with patch("app.routes.motors.driver.available", True), \
         patch("app.routes.motors.driver.get_distance", return_value=float("inf")), \
         patch("app.routes.motors.driver.set_motors") as mock, \
         patch("app.routes.motors.settings.motor_speed_default", 0.75):
        r = client.post("/api/motors/forward")
        assert r.status_code == 200
        mock.assert_called_once_with(0.75, 1, 0.75, 0)
