// Preprocessing for YOLOX-Nano browser inference. Deliberately mirrors
// yolox/data/data_augment.py::preproc exactly (read during Milestone 1)
// rather than a "typical" ImageNet-style preprocessing, since the model was
// trained against this specific pipeline:
//
//   - top-left letterbox (NOT centered) padded with constant value 114
//   - resize ratio r = min(inputSize / height, inputSize / width)
//   - BGR channel order (the source repo reads images via cv2, which is
//     BGR-native, with no explicit RGB conversion in preproc())
//   - NO normalization: raw 0-255 pixel values kept as float32 (no /255,
//     no mean/std subtraction)
//   - HWC -> CHW (channels-first), batch dimension of 1
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim, from
// frontend/src/spike/objectDetection/preprocess.js -- no logic change.
//
// The dimension math is a pure function (independently testable without a
// real canvas/image). Only letterboxImageToTensor touches the DOM.
//
// letterboxImageToTensor also needs to run inside a Web Worker
// (yoloxWorker.js), where `document` does not exist. OffscreenCanvas is
// used whenever available (true in both a Worker and a modern main thread)
// so this single implementation serves both contexts unchanged;
// `document.createElement('canvas')` remains the fallback for a main
// thread without OffscreenCanvas support.

import { INPUT_SIZE, LETTERBOX_PAD_VALUE } from './constants'

function createCanvas(width, height) {
  if (typeof OffscreenCanvas !== 'undefined') {
    return new OffscreenCanvas(width, height)
  }
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  return canvas
}

/**
 * Pure function: given a source image's natural width/height, computes the
 * letterbox resize ratio and the resized (pre-padding) dimensions, top-left
 * aligned inside an inputSize x inputSize square -- exactly matching
 * yolox/data/data_augment.py::preproc's own math (r = min(...), no centering).
 */
export function computeLetterboxLayout(sourceWidth, sourceHeight, inputSize = INPUT_SIZE) {
  if (!sourceWidth || !sourceHeight || sourceWidth <= 0 || sourceHeight <= 0) {
    return null
  }
  const ratio = Math.min(inputSize / sourceHeight, inputSize / sourceWidth)
  const resizedWidth = Math.round(sourceWidth * ratio)
  const resizedHeight = Math.round(sourceHeight * ratio)
  return { ratio, resizedWidth, resizedHeight, offsetX: 0, offsetY: 0 }
}

/**
 * Draws `source` (an <img>, <video>, or ImageBitmap) onto an inputSize x
 * inputSize canvas using the letterbox layout above, reads back the pixel
 * data, and returns a Float32Array tensor in NCHW/BGR/[0,255] layout ready
 * for ONNX Runtime Web, plus the layout (needed to map detected boxes back
 * to the source image's original pixel coordinates).
 *
 * @param {HTMLImageElement|HTMLVideoElement|ImageBitmap} source
 * @param {number} sourceWidth
 * @param {number} sourceHeight
 * @param {number} [inputSize]
 * @returns {{ tensorData: Float32Array, layout: ReturnType<typeof computeLetterboxLayout> }}
 */
export function letterboxImageToTensor(source, sourceWidth, sourceHeight, inputSize = INPUT_SIZE) {
  const layout = computeLetterboxLayout(sourceWidth, sourceHeight, inputSize)
  if (!layout) {
    throw new Error('letterboxImageToTensor: invalid source dimensions')
  }

  const canvas = createCanvas(inputSize, inputSize)
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) {
    throw new Error('letterboxImageToTensor: unable to obtain 2D canvas context')
  }

  // Fill with the same constant pad value YOLOX's own preprocessing uses,
  // then draw the resized source top-left aligned (no centering).
  ctx.fillStyle = `rgb(${LETTERBOX_PAD_VALUE}, ${LETTERBOX_PAD_VALUE}, ${LETTERBOX_PAD_VALUE})`
  ctx.fillRect(0, 0, inputSize, inputSize)
  ctx.drawImage(source, 0, 0, layout.resizedWidth, layout.resizedHeight)

  const { data } = ctx.getImageData(0, 0, inputSize, inputSize) // RGBA, 0-255

  const tensorData = new Float32Array(3 * inputSize * inputSize)
  const plane = inputSize * inputSize
  for (let pixel = 0; pixel < plane; pixel++) {
    const r = data[pixel * 4 + 0]
    const g = data[pixel * 4 + 1]
    const b = data[pixel * 4 + 2]
    // BGR channel order, matching YOLOX's cv2-native training pipeline.
    tensorData[pixel] = b
    tensorData[plane + pixel] = g
    tensorData[2 * plane + pixel] = r
  }

  return { tensorData, layout }
}

/**
 * Maps a detection box from the 320x320 letterboxed model space back to the
 * original source image's pixel coordinates -- same `/ ratio` approach the
 * Milestone 1 Python validation script used.
 */
export function boxToSourcePixels(box, layout) {
  const { ratio } = layout
  return {
    x: (box.cx - box.w / 2) / ratio,
    y: (box.cy - box.h / 2) / ratio,
    width: box.w / ratio,
    height: box.h / ratio,
  }
}
