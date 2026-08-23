// Pure helper turning a single frame's raw detector output into the
// `activeConditions` set the temporal rule engine expects. Kept separate so
// the precedence rules (face-count conditions take priority over pose,
// since pose is meaningless with zero or multiple faces) are independently
// testable and not buried inside the detection loop.

/**
 * @param {object} frame
 * @param {number} frame.faceCount
 * @param {string|null} frame.headPose - one of the labels from headPose.js, or null
 * @returns {Set<string>}
 */
export function buildActiveConditions({ faceCount, headPose }) {
  const conditions = new Set()

  if (faceCount === 0) {
    conditions.add('FACE_ABSENT')
    return conditions
  }

  if (faceCount > 1) {
    conditions.add('MULTIPLE_FACES')
    return conditions
  }

  if (headPose && headPose !== 'CENTER') {
    conditions.add(headPose)
  }

  return conditions
}
