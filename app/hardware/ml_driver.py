import io
import logging
import threading
import time
from pathlib import Path

from app.config import settings
from app.hardware import camera_driver

_log = logging.getLogger(__name__)

available = False
library_available = False
model_found = False
enabled = False
_interpreter = None
_labels: list[str] = []
_lock = threading.Lock()
_detections: list[dict] = []
_running = False

_MODEL_PATH = settings.data_dir / "models" / "mobilenet_ssd_v1.tflite"
_LABELS_PATH = Path(__file__).parent.parent / "models" / "coco_labels.txt"

model_found = _MODEL_PATH.exists() and _LABELS_PATH.exists()

try:
    import numpy as np
    import tflite_runtime.interpreter as tflite
    from PIL import Image
    library_available = True

    if model_found:
        _interpreter = tflite.Interpreter(model_path=str(_MODEL_PATH))
        _interpreter.allocate_tensors()
        _labels = _LABELS_PATH.read_text().strip().splitlines()
        available = True
except Exception as exc:
    _log.debug("ml_driver unavailable: %s", exc)


def _run_inference(frame: bytes) -> list[dict]:
    if _interpreter is None:
        return []

    img = Image.open(io.BytesIO(frame)).convert("RGB").resize((300, 300))
    arr = np.array(img, dtype=np.uint8)[np.newaxis, :]

    input_details = _interpreter.get_input_details()
    output_details = _interpreter.get_output_details()

    _interpreter.set_tensor(input_details[0]["index"], arr)
    _interpreter.invoke()

    boxes = _interpreter.get_tensor(output_details[0]["index"])[0]
    classes = _interpreter.get_tensor(output_details[1]["index"])[0]
    scores = _interpreter.get_tensor(output_details[2]["index"])[0]
    num = int(_interpreter.get_tensor(output_details[3]["index"])[0])

    results = []
    for i in range(num):
        score = float(scores[i])
        if score < 0.5:
            continue
        class_id = int(classes[i])
        label = _labels[class_id] if class_id < len(_labels) else str(class_id)
        results.append({
            "label": label,
            "score": round(score, 2),
            "box": [float(v) for v in boxes[i]],  # [y1, x1, y2, x2] normalized
        })
    return results


def _detection_loop() -> None:
    global _detections, _running

    while _running:
        with _lock:
            is_enabled = enabled
        if not is_enabled:
            time.sleep(0.2)
            continue
        frame = camera_driver.get_frame()
        if frame is None:
            time.sleep(0.5)
            continue
        try:
            found = _run_inference(frame)
            with _lock:
                _detections = found
        except Exception as exc:
            _log.warning("inference error: %s", exc)
            time.sleep(2.0)
        time.sleep(0.5)


def start() -> None:
    global _running, enabled
    if not available or _running:
        return
    from app import db  # local import — db not available at module import time
    enabled = db.get_setting("ml_detection_enabled") == "true"
    _running = True
    threading.Thread(target=_detection_loop, daemon=True).start()


def stop() -> None:
    global _running
    _running = False


def set_enabled(value: bool) -> None:
    # Memory-only: persistence is the caller's responsibility.
    global enabled
    with _lock:
        enabled = value


def get_detections() -> list[dict]:
    with _lock:
        return list(_detections)
