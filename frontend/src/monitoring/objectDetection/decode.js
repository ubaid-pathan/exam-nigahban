// Pure, framework-free YOLOX output decode + NMS. No DOM, no ONNX Runtime
// types -- mirrors the isolation pattern already used by
// frontend/src/monitoring/headPose.js, so this is independently unit
// testable and can run inside a Web Worker with no rework.
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/decode.js -- no logic change.
//
// Grid/stride decode logic is a direct, verified port of
// yolox/models/yolo_head.py::decode_outputs (read during Milestone 1):
//   box_xy = (raw_xy + grid_xy) * stride
//   box_wh = exp(raw_wh) * stride
// Objectness and class scores are used as-is (already sigmoid-activated in
// the exported graph -- confirmed empirically in Milestone 1). Applying a
// second sigmoid here would be wrong and is deliberately not done.

import {
  BOX_ATTRS,
  INPUT_SIZE,
  STRIDES,
  TOTAL_ANCHORS,
} from './constants'

/**
 * Builds the flattened (grid-x, grid-y, stride) triple for every anchor, in
 * the exact concatenation order the model's output uses: stride 8 first
 * (1600 cells, row-major y-outer/x-inner), then stride 16 (400), then
 * stride 32 (100) -- verified against yolox_head.py's own grid/stride
 * concatenation order and cross-checked empirically (output.shape[1] must
 * equal 2100 for a 320 input, matching Milestone 1's verified ONNX output).
 *
 * @returns {{gx:number, gy:number, stride:number}[]} length TOTAL_ANCHORS
 */
export function buildGrids(inputSize = INPUT_SIZE, strides = STRIDES) {
  const grids = []
  for (const stride of strides) {
    const size = inputSize / stride
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        grids.push({ gx: x, gy: y, stride })
      }
    }
  }
  return grids
}

/**
 * Validates that a raw model output is shaped as expected before decoding.
 * Returns a descriptive reason string if invalid, or null if valid.
 */
export function validateRawOutput(rawOutput, totalAnchors = TOTAL_ANCHORS, boxAttrs = BOX_ATTRS) {
  if (!rawOutput || typeof rawOutput.length !== 'number') {
    return 'raw output is missing or not array-like'
  }
  const expectedLength = totalAnchors * boxAttrs
  if (rawOutput.length !== expectedLength) {
    return `raw output length ${rawOutput.length} does not match expected ${expectedLength} (${totalAnchors} anchors x ${boxAttrs} attrs)`
  }
  return null
}

/**
 * Decodes the raw [totalAnchors * boxAttrs] flat model output into
 * detections for a single target class, already confidence-thresholded and
 * NMS-suppressed. Boxes are returned in the model's 320x320 letterboxed
 * input space (cx, cy, w, h) -- callers map back to original-image pixels
 * by dividing by the letterbox ratio (see preprocess.js), exactly matching
 * the Python validation script's approach.
 *
 * @param {Float32Array|number[]} rawOutput - flat, length totalAnchors*boxAttrs
 * @param {object} [options]
 * @param {number} [options.classId] - COCO class id to filter to (67 = cell phone)
 * @param {number} [options.confidenceThreshold]
 * @param {number} [options.iouThreshold]
 * @param {number} [options.inputSize]
 * @param {number[]} [options.strides]
 * @returns {{cx:number,cy:number,w:number,h:number,confidence:number,classId:number}[]}
 */
export function decodeDetections(rawOutput, options = {}) {
  const {
    classId = 67,
    confidenceThreshold = 0.8,
    iouThreshold = 0.45,
    inputSize = INPUT_SIZE,
    strides = STRIDES,
  } = options

  const totalAnchors = strides.reduce((sum, s) => sum + (inputSize / s) ** 2, 0)
  const invalidReason = validateRawOutput(rawOutput, totalAnchors, BOX_ATTRS)
  if (invalidReason) {
    throw new Error(`decodeDetections: ${invalidReason}`)
  }

  const grids = buildGrids(inputSize, strides)
  const candidates = []

  for (let i = 0; i < totalAnchors; i++) {
    const base = i * BOX_ATTRS
    const objectness = rawOutput[base + 4]
    const classScore = rawOutput[base + 5 + classId]
    // NaN-safe by construction: any comparison against NaN is false, so a
    // malformed/NaN-filled row is naturally excluded without special-casing.
    const confidence = objectness * classScore
    if (!(confidence >= confidenceThreshold)) continue

    const { gx, gy, stride } = grids[i]
    const rawCx = rawOutput[base + 0]
    const rawCy = rawOutput[base + 1]
    const rawW = rawOutput[base + 2]
    const rawH = rawOutput[base + 3]

    const cx = (rawCx + gx) * stride
    const cy = (rawCy + gy) * stride
    const w = Math.exp(rawW) * stride
    const h = Math.exp(rawH) * stride

    if (![cx, cy, w, h, confidence].every(Number.isFinite)) continue

    candidates.push({ cx, cy, w, h, confidence, classId })
  }

  return nonMaxSuppression(candidates, iouThreshold)
}

function toCorners(box) {
  return {
    x1: box.cx - box.w / 2,
    y1: box.cy - box.h / 2,
    x2: box.cx + box.w / 2,
    y2: box.cy + box.h / 2,
  }
}

function iou(a, b) {
  const A = toCorners(a)
  const B = toCorners(b)
  const interX1 = Math.max(A.x1, B.x1)
  const interY1 = Math.max(A.y1, B.y1)
  const interX2 = Math.min(A.x2, B.x2)
  const interY2 = Math.min(A.y2, B.y2)
  const interW = Math.max(0, interX2 - interX1)
  const interH = Math.max(0, interY2 - interY1)
  const interArea = interW * interH
  const areaA = Math.max(0, A.x2 - A.x1) * Math.max(0, A.y2 - A.y1)
  const areaB = Math.max(0, B.x2 - B.x1) * Math.max(0, B.y2 - B.y1)
  const union = areaA + areaB - interArea
  return union <= 0 ? 0 : interArea / union
}

/**
 * Standard greedy NMS: highest-confidence box wins, anything overlapping it
 * by more than iouThreshold is suppressed, repeat. Pure function, single
 * class at a time (this module only ever calls it with class-67 candidates).
 */
export function nonMaxSuppression(boxes, iouThreshold = 0.45) {
  const sorted = [...boxes].sort((a, b) => b.confidence - a.confidence)
  const kept = []
  for (const candidate of sorted) {
    const suppressed = kept.some((keptBox) => iou(candidate, keptBox) > iouThreshold)
    if (!suppressed) kept.push(candidate)
  }
  return kept
}
