// Centralized AI-monitoring configuration for Phase 5 (Face Monitoring).
//
// These are the baseline MVP values from CLAUDE.md / PROJECT_SPEC.md. Every
// threshold used anywhere in the monitoring engine or UI must come from
// here rather than being hard-coded inline, so recalibration during testing
// only requires touching this one file.

// Detection loop cadence: how often a video frame is actually run through
// the face landmarker. MediaPipe can run faster than this, but sampling at
// ~4-5 fps is enough for temporal rules measured in seconds and keeps CPU
// usage low during a long exam session.
export const DETECTION_INTERVAL_MS = 220

// Degrees beyond which the head is considered turned in a cardinal
// direction. These are intentionally modest so HEAD_LEFT/RIGHT/UP/DOWN
// capture a clear, sustained turn rather than normal micro-movement.
export const HEAD_POSE_ANGLE_THRESHOLD_DEG = {
  yawLeft: -15,
  yawRight: 15,
  pitchUp: 12,
  pitchDown: -12,
}

// Beyond this larger angle the head/gaze is considered oriented away from
// the screen altogether (LOOKING_AWAY), rather than a moderate directional
// turn. Chosen to be a technically-justified escalation of the same
// yaw/pitch signal already used for the directional rules, not a separate
// unproven detector.
export const LOOKING_AWAY_ANGLE_THRESHOLD_DEG = {
  yaw: 30,
  pitch: 22,
}

// Baseline temporal rules — see CLAUDE.md section 4.5 / PROJECT_SPEC.md
// section 13. FACE_ABSENT / MULTIPLE_FACES use a "configurable" confidence
// threshold per the spec; 0.5 is the MVP default (face-count based
// conditions are less confidence-sensitive than pose classification).
export const MONITORING_RULES = {
  HEAD_LEFT: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  HEAD_RIGHT: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  HEAD_UP: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  HEAD_DOWN: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  LOOKING_AWAY: { minDurationSec: 3, requiredOccurrences: 3, confidenceThreshold: 0.75, severity: 'medium' },
  FACE_ABSENT: { minDurationSec: 3, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
  MULTIPLE_FACES: { minDurationSec: 2, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
}

export const MONITORING_EVENT_TYPES = Object.freeze(Object.keys(MONITORING_RULES))

// Milestone 6 Phase 2 Step 3: mobile-phone detection (YOLOX) temporal rule
// and scheduling interval. Deliberately kept OUT of MONITORING_RULES /
// MONITORING_EVENT_TYPES above (the face-monitoring engine's own rule
// table) -- useMobilePhoneMonitoring.js constructs a second, fully
// independent createTemporalRuleEngine() instance scoped to only this one
// rule, so its state never shares a Map (or anything else) with the face
// engine's. Baseline values are this file's own MOBILE_PHONE row from
// CLAUDE.md/PROJECT_SPEC.md's temporal-rule table (~1s persistence, 1
// occurrence, High severity). The confidence bar was lowered from the
// original 0.80: the temporal engine compares this against the MINIMUM
// confidence observed across the whole episode (see temporalRuleEngine.js
// minConfidenceSeen), so at 0.80 a single dipped frame -- motion blur, a
// hand passing over the phone -- discarded an otherwise solid one-second
// sighting. Persistence, not the confidence bar, is what filters noise.
export const MOBILE_PHONE_RULE = {
  minDurationSec: 1,
  requiredOccurrences: 1,
  confidenceThreshold: 0.4,
  severity: 'high',
}

// YOLOX Worker detection-loop cadence: 200ms, the ~5 FPS rate validated
// end-to-end in Milestone 5.6's real combined-mode browser benchmark (see
// RECOMMENDED_YOLOX_TARGET_FPS in spike/objectDetection/constants.js, that
// benchmark's own source of truth) -- reused as the production value here,
// not re-derived.
export const YOLOX_DETECTION_INTERVAL_MS = 200

// Evidence capture (Phase 6): a single downsized still frame is captured
// only for a frame that already produced a stabilized monitoring event
// above -- never captured continuously. Kept small so upload stays fast
// and well under the backend's server-side size cap.
export const EVIDENCE_CAPTURE_MAX_WIDTH_PX = 480
export const EVIDENCE_JPEG_QUALITY = 0.7
