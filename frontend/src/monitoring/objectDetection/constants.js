// YOLOX-Nano mobile-phone-detection model/protocol constants.
//
// Milestone 6 Phase 2 Step 1: mechanically relocated here, verbatim (this
// file's export list only), from frontend/src/spike/objectDetection/
// constants.js -- no value changed. RECOMMENDED_YOLOX_TARGET_FPS stayed
// behind in the spike (it is a benchmarking-derived scheduling suggestion
// for the spike's own schedule-comparison UI, not a detection-implementation
// constant).
//
// Every value below is a VERIFIED fact from the Milestone 1 export/validation
// pass (ai/object_detection/validate_class67.py), not assumed:
//   - model: yolox_nano_320.onnx, FP32 only (INT8 was rejected -- confidence
//     collapsed from 0.924 to 0.000037 on the same positive sample)
//   - input tensor name "images", shape [1,3,320,320], float32
//   - output tensor name "output", shape [1,2100,85], float32
//   - objectness and the 80 class scores are ALREADY sigmoid-activated in
//     the exported graph (empirically confirmed: bounded to [0,1] on a
//     dummy-noise input) -- do not apply another sigmoid here.
//   - box coordinates (first 4 of the 85) are NOT decoded -- grid/stride
//     decode is required, matching yolox/models/yolo_head.py::decode_outputs
//     exactly (verified against that source).

export const MODEL_URL = '/models/yolox-nano-phone.onnx'
export const MODEL_INPUT_NAME = 'images'
export const MODEL_OUTPUT_NAME = 'output'
export const INPUT_SIZE = 320
export const STRIDES = [8, 16, 32]
export const NUM_CLASSES = 80
export const BOX_ATTRS = 4 + 1 + NUM_CLASSES // cx,cy,w,h + objectness + 80 class scores = 85
export const TOTAL_ANCHORS = STRIDES.reduce((sum, s) => sum + (INPUT_SIZE / s) ** 2, 0) // 1600+400+100=2100

export const CELL_PHONE_CLASS_ID = 67
export const CELL_PHONE_LABEL = 'Cell Phone'

// Per-frame detection gate: a box scoring below this never becomes a
// detection at all.
//
// Lowered from the original 0.80 so a phone that is only PARTIALLY visible
// is still caught. Confidence here is objectness x classScore, so a phone
// half out of frame loses ground on both factors at once and realistically
// scores 0.25-0.55 -- far under 0.80, meaning it was not detected weakly,
// it was invisible. A fully visible phone measured 0.92 in the Milestone 1
// validation, so this does not weaken the clear-cut case.
//
// The recall/precision trade is deliberate and specific to this system:
// every detection is reviewed by a human against a captured evidence
// image, so a false positive costs an administrator a few seconds, while a
// miss is silent and unrecoverable. Noise is filtered by the one-second
// persistence rule (see MOBILE_PHONE_RULE) rather than by a high
// confidence bar -- a stray hit on a wallet does not survive five
// consecutive frames, a real phone does.
export const DEFAULT_CONFIDENCE_THRESHOLD = 0.4
export const DEFAULT_IOU_THRESHOLD = 0.45

// Padding value YOLOX's own preprocessing (yolox/data/data_augment.py::preproc)
// fills the letterbox canvas with, verified against that source.
export const LETTERBOX_PAD_VALUE = 114
