// Pure temporal-rule state machine. No DOM, no React, no MediaPipe types —
// it only knows about plain "raw observation" objects and timestamps, so it
// can be constructed and driven entirely from unit tests.
//
// Responsibility boundary:
//   raw observation  -->  stabilized (debounced) observation  -->  event
//
// A single noisy frame must never produce a monitoring event. A condition
// must hold continuously for its configured minimum duration to count as
// one "occurrence"; an event is only emitted once the configured number of
// occurrences has been reached, matching the baseline rule table
// (e.g. HEAD_RIGHT needs 3 separate >3s occurrences before an event fires).

import { MONITORING_RULES } from './constants'

function createRuleState() {
  return {
    activeSinceMs: null,
    minConfidenceSeen: null,
    occurrenceCount: 0,
    countedThisEpisode: false,
  }
}

/**
 * @param {object} [rules] - activityType -> { minDurationSec, requiredOccurrences, confidenceThreshold, severity }
 */
export function createTemporalRuleEngine(rules = MONITORING_RULES) {
  const stateByRule = new Map(Object.keys(rules).map((type) => [type, createRuleState()]))

  /**
   * Feed one stabilized raw observation for this frame.
   *
   * @param {object} observation
   * @param {Set<string>|string[]} observation.activeConditions - activity
   *   types that are true for this frame (e.g. ['HEAD_LEFT']). At most one
   *   pose-based condition and/or the face-count conditions may be active
   *   in the same frame.
   * @param {number} observation.confidence - detector confidence for this
   *   frame's classification, 0-1.
   * @param {number} timestampMs - monotonic time of this frame.
   * @returns {Array<object>} zero or more newly satisfied monitoring events.
   */
  function observe(observation, timestampMs) {
    const activeConditions = new Set(observation.activeConditions || [])
    const confidence = observation.confidence ?? 0
    const emitted = []

    for (const [activityType, rule] of Object.entries(rules)) {
      const state = stateByRule.get(activityType)
      const conditionMet = activeConditions.has(activityType)

      if (conditionMet) {
        if (state.activeSinceMs === null) {
          state.activeSinceMs = timestampMs
          state.minConfidenceSeen = confidence
          state.countedThisEpisode = false
        } else {
          state.minConfidenceSeen = Math.min(state.minConfidenceSeen, confidence)
        }

        const durationSec = (timestampMs - state.activeSinceMs) / 1000
        const durationSatisfied = durationSec >= rule.minDurationSec
        const confidenceSatisfied = state.minConfidenceSeen >= rule.confidenceThreshold

        if (durationSatisfied && confidenceSatisfied && !state.countedThisEpisode) {
          state.countedThisEpisode = true
          state.occurrenceCount += 1

          if (state.occurrenceCount >= rule.requiredOccurrences) {
            emitted.push({
              eventType: activityType,
              severity: rule.severity,
              confidence: state.minConfidenceSeen,
              durationSeconds: durationSec,
              occurrences: state.occurrenceCount,
              detectedAtMs: timestampMs,
            })
            state.occurrenceCount = 0
          }
        }
      } else if (state.activeSinceMs !== null) {
        // Episode broken before it produced an event: the completed partial
        // episode does not count as an occurrence.
        state.activeSinceMs = null
        state.minConfidenceSeen = null
        state.countedThisEpisode = false
      }
    }

    return emitted
  }

  function reset() {
    for (const key of stateByRule.keys()) {
      stateByRule.set(key, createRuleState())
    }
  }

  return { observe, reset }
}
