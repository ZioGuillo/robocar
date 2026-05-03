import io
import threading

available = False
_cam = None
_lock = threading.Lock()
_latest_frame: bytes | None = None
_frame_counter: int = 0
_running = False
_backend: str = "none"

try:
    from picamera2 import Picamera2

    _cam = Picamera2()
    _cam.configure(_cam.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        controls={"FrameRate": 30},
    ))
    available = True
    _backend = "picamera2"
except Exception:
    pass


def _capture_loop() -> None:
    global _latest_frame, _frame_counter, _running
    _cam.start()
    try:
        while _running:
            request = _cam.capture_request()
            try:
                buf = io.BytesIO()
                request.save("main", buf, format="jpeg", quality=75)
                data = buf.getvalue()
                if data:
                    with _lock:
                        _latest_frame = data
                        _frame_counter += 1
            finally:
                request.release()
    finally:
        _cam.stop()


def start() -> None:
    global _running
    if not available or _running:
        return
    _running = True
    threading.Thread(target=_capture_loop, daemon=True).start()


def stop() -> None:
    global _running
    _running = False


def get_frame() -> bytes | None:
    with _lock:
        return _latest_frame


def get_frame_if_new(last_counter: int) -> tuple[bytes | None, int]:
    """Return (frame, counter). frame is None when no new frame since last_counter."""
    with _lock:
        if _frame_counter == last_counter:
            return None, last_counter
        return _latest_frame, _frame_counter
