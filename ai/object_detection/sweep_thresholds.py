"""Measure phone-detection recall and false positives across thresholds.

Why this exists
---------------
The confidence gate for MOBILE_PHONE was chosen by reasoning, not by
measurement. That is fine as a starting point and poor as a final answer:
the right threshold depends on your camera, your lighting, and how a phone
actually appears in your exam room -- none of which can be inferred from a
model card.

This runs the SAME model and the SAME preprocessing the browser uses
(validate_class67.py mirrors yolox/data/data_augment.py::preproc exactly)
over a folder of frames, and reports, for each candidate threshold, how
many positives were caught and how many negatives fired.

What to capture first
---------------------
Two folders of frames from YOUR setup, at YOUR distance and lighting. Ten
of each is enough to be useful.

  positives/ -- a phone genuinely visible. Include the HARD cases, because
                those are the ones the threshold decides: at the very edge
                of frame, half out of shot, held low near the desk, face
                down, screen off, partially behind a hand.

  negatives/ -- no phone, but plausible confusions. An empty desk, a
                wallet, a calculator, a dark notebook, a water bottle, an
                ID card, a hand alone.

Usage
-----
    python sweep_thresholds.py positives/ negatives/

Read the table for the lowest threshold whose false-positive count you are
willing to have an administrator glance at. Remember every detection here
is human-reviewed with an evidence image, so a false positive costs a few
seconds while a miss is silent and unrecoverable -- the trade is usually
worth making further toward recall than instinct suggests.

Whatever you choose must then be set in THREE places or the change does
nothing (see the comments on each):

  frontend/src/monitoring/objectDetection/constants.js  DEFAULT_CONFIDENCE_THRESHOLD
  frontend/src/monitoring/constants.js                  MOBILE_PHONE_RULE.confidenceThreshold
  backend/app/db/seed_monitoring_rules.py               MOBILE_PHONE confidence_threshold
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from validate_class67 import (
    CELL_PHONE_CLASS_ID,
    INPUT_SIZE,
    letterbox_preproc,
)

try:
    import onnxruntime as ort
    from PIL import Image
except ImportError:  # pragma: no cover - dependency guidance only
    print("This script needs onnxruntime and Pillow:\n  pip install onnxruntime pillow")
    raise SystemExit(1)

MODEL_PATH = os.environ.get("VALIDATE_MODEL_PATH", "yolox_nano_320.onnx")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# The range worth considering. Above 0.8 nothing partial survives; below
# 0.2 almost any dark rectangle scores.
THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80]


def best_phone_score(session, image_path: Path) -> float:
    """The highest cell-phone confidence anywhere in one frame.

    Confidence is objectness x classScore, exactly as the browser computes
    it in objectDetection/decode.js -- both factors are already sigmoid
    activated in the exported graph, so nothing is applied on top.

    Returns the maximum rather than a thresholded list: the sweep needs the
    raw score so one pass can be evaluated against every threshold.
    """
    image = Image.open(image_path).convert("RGB")
    tensor, _ratio = letterbox_preproc(np.array(image), INPUT_SIZE)
    raw = session.run(None, {session.get_inputs()[0].name: tensor})[0][0]

    objectness = raw[:, 4]
    class_score = raw[:, 5 + CELL_PHONE_CLASS_ID]
    scores = objectness * class_score
    return float(scores.max()) if scores.size else 0.0


def collect(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    positives_dir, negatives_dir = Path(sys.argv[1]), Path(sys.argv[2])
    for folder in (positives_dir, negatives_dir):
        if not folder.is_dir():
            print(f"Not a directory: {folder}")
            return 1

    positives, negatives = collect(positives_dir), collect(negatives_dir)
    if not positives and not negatives:
        print("No images found. See the docstring for what to capture.")
        return 1

    session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])

    print(f"Model: {MODEL_PATH}")
    print(f"Positives: {len(positives)}   Negatives: {len(negatives)}\n")

    positive_scores = {path.name: best_phone_score(session, path) for path in positives}
    negative_scores = {path.name: best_phone_score(session, path) for path in negatives}

    print("Per-frame best cell-phone score")
    print("-" * 58)
    for name, score in sorted(positive_scores.items(), key=lambda kv: kv[1]):
        print(f"  positive  {name:<38} {score:.3f}")
    for name, score in sorted(negative_scores.items(), key=lambda kv: -kv[1]):
        print(f"  negative  {name:<38} {score:.3f}")

    print()
    print("Threshold sweep")
    print("-" * 58)
    print(f"{'threshold':>10} {'detected':>10} {'recall':>9} {'false pos':>11}")
    for threshold in THRESHOLDS:
        detected = sum(1 for s in positive_scores.values() if s >= threshold)
        false_positives = sum(1 for s in negative_scores.values() if s >= threshold)
        recall = detected / len(positive_scores) if positive_scores else 0.0
        print(
            f"{threshold:>10.2f} {detected:>4}/{len(positive_scores):<5} "
            f"{recall:>8.0%} {false_positives:>6}/{len(negative_scores):<4}"
        )

    if positive_scores:
        weakest = min(positive_scores.values())
        print()
        print(
            f"Weakest positive scores {weakest:.3f} -- a threshold above this "
            "misses it entirely."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
