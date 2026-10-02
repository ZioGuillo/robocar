import io
import logging
import threading
import time
from pathlib import Path

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

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_MODEL_PATH = _MODELS_DIR / "efficientdet_lite0.tflite"
_LABELS_PATH = _MODELS_DIR / "coco_labels.txt"

model_found = _MODEL_PATH.exists() and _LABELS_PATH.exists()

try:
    import numpy as np
    from PIL import Image
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        import ai_edge_litert.interpreter as tflite  # type: ignore[no-redef]
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

    input_details = _interpreter.get_input_details()
    output_details = _interpreter.get_output_details()

    _, in_h, in_w, _ = input_details[0]["shape"]
    img = Image.open(io.BytesIO(frame)).convert("RGB").resize((in_w, in_h))
    arr = np.array(img, dtype=np.uint8)[np.newaxis, :]

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
        # The TFLite_Detection_PostProcess op's class ids are background-
        # exclusive (0 == the first real category), but _labels[0] is the
        # "???" background placeholder from the standard 91-entry COCO
        # label map — so the real label is one index further in, e.g.
        # class_id 0 -> _labels[1] == "person". Skipping this +1 silently
        # mislabeled every detection (verified: cats detected as "bird",
        # people as "???").
        class_id = int(classes[i]) + 1
        if class_id >= len(_labels):
            continue
        label = _labels[class_id]
        if label == "???":
            # One of COCO's 11 retired/placeholder category slots — never
            # a meaningful detection, so not worth showing.
            continue
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
