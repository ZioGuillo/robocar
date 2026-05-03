import logging
import threading

import numpy as np

_log = logging.getLogger(__name__)

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
        main={"size": (640, 480), "format": "MJPEG"},
    ))
    available = True
    _backend = "picamera2"
except Exception:
    pass


def _capture_loop() -> None:
    global _latest_frame, _frame_counter, _running
    try:
        _cam.start()
        while _running:
            request = _cam.capture_request()
            try:
                buf = request.make_buffer("main")
                # buf is a numpy array preallocated to max size; find actual JPEG end
                ff_pos = np.where((buf[:-1] == 0xFF) & (buf[1:] == 0xD9))[0]
                if len(ff_pos):
                    data = bytes(buf[: int(ff_pos[-1]) + 2])
                    with _lock:
                        _latest_frame = data
                        _frame_counter += 1
            finally:
                request.release()
    except Exception as exc:
        _log.error("camera capture loop error: %s", exc)
        _running = False
    finally:
        try:
            _cam.stop()
        except Exception:
            pass


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
