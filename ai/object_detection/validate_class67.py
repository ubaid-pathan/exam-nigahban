"""Milestone 1 validation script: confirms COCO class 67 (cell phone) is
empirically detectable from the exported yolox_nano_320 ONNX model.

Preprocessing here mirrors yolox/data/data_augment.py::preproc exactly
(verified by reading that source, not assumed): top-left letterbox padded
with constant value 114, BGR channel order (no RGB conversion), raw 0-255
float32 pixel values (no mean/std normalization), HWC -> CHW.

Grid/stride decode mirrors yolox/models/yolo_head.py::decode_outputs
(verified by reading that source): for a 320x320 input, YOLOXHead's
default strides are [8, 16, 32], producing grid sizes 40x40, 20x20, 10x10
= 1600 + 400 + 100 = 2100 anchors total, matching the verified [1,2100,85]
output shape exactly.
"""
import sys
import numpy as np
import onnxruntime as ort
from PIL import Image

import os
MODEL_PATH = os.environ.get("VALIDATE_MODEL_PATH", "yolox_nano_320.onnx")
INPUT_SIZE = 320
STRIDES = [8, 16, 32]
CELL_PHONE_CLASS_ID = 67  # COCO 80-class ordering, 0-indexed


def letterbox_preproc(img_rgb: np.ndarray, input_size: int):
    """img_rgb: HWC uint8 RGB array (as PIL loads it)."""
    # Convert RGB -> BGR to match YOLOX's cv2-based training preprocessing.
    img_bgr = img_rgb[:, :, ::-1]
    h, w = img_bgr.shape[:2]
    padded = np.ones((input_size, input_size, 3), dtype=np.uint8) * 114
    r = min(input_size / h, input_size / w)
    new_h, new_w = int(h * r), int(w * r)
    resized = np.array(
        Image.fromarray(img_bgr).resize((new_w, new_h), Image.BILINEAR)
    )
    padded[:new_h, :new_w] = resized
    chw = padded.transpose(2, 0, 1).astype(np.float32)  # no /255, no mean/std
    return chw[None, ...], r


def build_grids(input_size: int, strides: list[int]):
    grids = []
    expanded_strides = []
    for stride in strides:
        size = input_size // stride
        yv, xv = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
        grid = np.stack((xv, yv), axis=2).reshape(1, -1, 2)
        grids.append(grid)
        expanded_strides.append(np.full((1, grid.shape[1], 1), stride))
    return np.concatenate(grids, axis=1), np.concatenate(expanded_strides, axis=1)


def decode(output: np.ndarray, input_size: int, strides: list[int]):
    """Mirrors YOLOXHead.decode_outputs: box xy/wh decode only (obj/cls
    already sigmoid-activated in the exported graph, per empirical check
    in the readiness verification step)."""
    grids, exp_strides = build_grids(input_size, strides)
    out = output.copy()
    out[..., :2] = (out[..., :2] + grids) * exp_strides
    out[..., 2:4] = np.exp(out[..., 2:4]) * exp_strides
    return out


def run(image_path: str, label: str):
    img = np.array(Image.open(image_path).convert("RGB"))
    tensor, ratio = letterbox_preproc(img, INPUT_SIZE)

    sess = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    raw = sess.run(None, {input_name: tensor})[0]  # [1, 2100, 85]

    decoded = decode(raw, INPUT_SIZE, STRIDES)

    obj = decoded[0, :, 4]
    cls_scores = decoded[0, :, 5:]
    phone_conf = obj * cls_scores[:, CELL_PHONE_CLASS_ID]

    best_idx = int(np.argmax(phone_conf))
    best_conf = float(phone_conf[best_idx])

    overall_best_class = int(np.argmax(cls_scores[best_idx]))
    overall_best_conf = float(obj[best_idx] * cls_scores[best_idx].max())

    box = decoded[0, best_idx, :4] / ratio
    print(f"--- {label} ({image_path}) ---")
    print(f"  image size: {img.shape[1]}x{img.shape[0]}, letterbox ratio: {ratio:.4f}")
    print(f"  max cell-phone (class {CELL_PHONE_CLASS_ID}) confidence: {best_conf:.6f} at anchor {best_idx}")
    print(f"  box (xc,yc,w,h) in original-image pixels: {box}")
    print(f"  for reference, this anchor's single best class overall: id={overall_best_class}, conf={overall_best_conf:.6f}")
    top5 = np.argsort(phone_conf)[-5:][::-1]
    print(f"  top-5 anchors by cell-phone confidence: {[(int(i), float(phone_conf[i])) for i in top5]}")
    print()
    return best_conf


if __name__ == "__main__":
    results = {}
    results["phone1.jpg (selfie, no phone visible)"] = run("samples/phone1.jpg", "MISLABELED sample - no phone actually visible in frame")
    results["phone2_wikimedia.jpg (genuine positive)"] = run("samples/phone2_wikimedia.jpg", "GENUINE POSITIVE sample (Samsung phone clearly held in hand)")
    results["negative_control_dog.jpg (negative)"] = run("samples/negative_control_dog.jpg", "NEGATIVE control (expected: no phone)")
    print("=== SUMMARY ===")
    for k, v in results.items():
        print(f"{k}: max cell-phone confidence = {v:.6f}")
