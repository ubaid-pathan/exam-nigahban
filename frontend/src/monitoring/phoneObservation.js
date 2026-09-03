// Pure helper turning a single frame's reduced YOLOX output into the
// `activeConditions` set the temporal rule engine expects. Deliberately
// separate from observation.js (face-count/head-pose precedence): a phone
// sighting is an orthogonal signal with no precedence interaction with
// face conditions, so it gets its own tiny, independently-testable
// mapping rather than being folded into that file.

/**
 * @param {object} frame
 * @param {boolean} frame.phoneDetected
 * @returns {Set<string>}
 */
export function buildPhoneActiveConditions({ phoneDetected }) {
  const conditions = new Set()
  if (phoneDetected) {
    conditions.add('MOBILE_PHONE')
  }
  return conditions
}
