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
  FACE_ABSENT: { minDurationSec: 5, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
  MULTIPLE_FACES: { minDurationSec: 2, requiredOccurrences: 1, confidenceThreshold: 0.5, severity: 'high' },
}

export const MONITORING_EVENT_TYPES = Object.freeze(Object.keys(MONITORING_RULES))
