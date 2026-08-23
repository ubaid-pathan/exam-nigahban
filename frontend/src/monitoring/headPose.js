// Pure, framework-free head-pose math. No DOM/MediaPipe/React dependency,
// so it can be unit-tested with plain numbers.

import { HEAD_POSE_ANGLE_THRESHOLD_DEG, LOOKING_AWAY_ANGLE_THRESHOLD_DEG } from './constants'

const RAD_TO_DEG = 180 / Math.PI

/**
 * Extracts yaw/pitch (in degrees) from MediaPipe's facial transformation
 * matrix (a flattened 4x4 rotation+translation matrix, row-major).
 *
 * Assumes the standard Tait-Bryan (X-Y-Z) decomposition used for head-pose
 * estimation. The exact sign/axis convention is hardware- and
 * model-version-dependent, so this is intentionally isolated from the
 * classification logic below — if calibration testing shows the signs are
 * flipped for a given camera setup, only this function needs adjusting.
 *
 * @param {number[] | Float32Array} m - 16-element row-major matrix.
 */
export function extractYawPitchDegFromMatrix(m) {
  if (!m || m.length !== 16) {
    return { yawDeg: 0, pitchDeg: 0 }
  }
  // Row-major 4x4: m[row*4 + col]
  const r20 = m[8]
  const r21 = m[9]
  const r22 = m[10]

  const pitchDeg = Math.atan2(r21, r22) * RAD_TO_DEG
  const yawDeg = Math.atan2(-r20, Math.sqrt(r21 * r21 + r22 * r22)) * RAD_TO_DEG

  return { yawDeg, pitchDeg }
}

/**
 * Classifies a single frame's yaw/pitch into a head-pose label. Pure
 * function of the angles and configured thresholds — no temporal logic.
 *
 * @returns {'CENTER'|'HEAD_LEFT'|'HEAD_RIGHT'|'HEAD_UP'|'HEAD_DOWN'|'LOOKING_AWAY'}
 */
export function classifyHeadPose(
  { yawDeg, pitchDeg },
  angleThresholds = HEAD_POSE_ANGLE_THRESHOLD_DEG,
  lookingAwayThresholds = LOOKING_AWAY_ANGLE_THRESHOLD_DEG,
) {
  if (Math.abs(yawDeg) >= lookingAwayThresholds.yaw || Math.abs(pitchDeg) >= lookingAwayThresholds.pitch) {
    return 'LOOKING_AWAY'
  }
  if (yawDeg <= angleThresholds.yawLeft) return 'HEAD_LEFT'
  if (yawDeg >= angleThresholds.yawRight) return 'HEAD_RIGHT'
  if (pitchDeg >= angleThresholds.pitchUp) return 'HEAD_UP'
  if (pitchDeg <= angleThresholds.pitchDown) return 'HEAD_DOWN'
  return 'CENTER'
}
