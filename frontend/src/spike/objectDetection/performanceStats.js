// Pure, framework-free performance-measurement helpers for the Milestone 3
// real-time camera performance test. No DOM, no React -- independently
// testable, mirroring the isolation pattern already used by decode.js.

/**
 * Accumulates a stream of millisecond latency samples and can report
 * count/min/max/avg on demand without needing to store the full history
 * externally.
 */
export function createLatencyTracker() {
  const values = []
  return {
    record(ms) {
      if (Number.isFinite(ms)) values.push(ms)
    },
    count: () => values.length,
    min: () => (values.length ? Math.min(...values) : null),
    max: () => (values.length ? Math.max(...values) : null),
    avg: () => (values.length ? values.reduce((a, b) => a + b, 0) / values.length : null),
    values: () => [...values],
    reset() {
      values.length = 0
    },
  }
}

/**
 * Effective FPS from a processed-frame count and the wall-clock window it
 * was measured over -- deliberately separate from "1000/avgLatencyMs",
 * since a throttled scheduler's effective FPS is capped by the schedule
 * interval, not just by how fast a single inference happens to run.
 */
export function computeEffectiveFps(processedFrameCount, elapsedMs) {
  if (!elapsedMs || elapsedMs <= 0 || !processedFrameCount) return 0
  return (processedFrameCount * 1000) / elapsedMs
}

/**
 * Frames "dropped" by a throttled scheduler: frames the camera produced
 * (approximated by scheduledFrameCount, i.e. how many scheduler ticks
 * occurred) that were not actually run through inference because a
 * previous inference was still in flight when the next tick arrived.
 */
export function computeDroppedFrames(scheduledFrameCount, processedFrameCount) {
  return Math.max(0, scheduledFrameCount - processedFrameCount)
}

/**
 * Reduces raw performance.memory samples (Chromium-only; undefined on
 * browsers without the API) into a simple before/after delta report. Never
 * throws on a missing/partial sample.
 */
export function summarizeMemory(beforeSample, afterSample) {
  if (!beforeSample || !afterSample) {
    return { available: false }
  }
  return {
    available: true,
    usedJSHeapSizeBeforeMB: beforeSample.usedJSHeapSize / (1024 * 1024),
    usedJSHeapSizeAfterMB: afterSample.usedJSHeapSize / (1024 * 1024),
    deltaMB: (afterSample.usedJSHeapSize - beforeSample.usedJSHeapSize) / (1024 * 1024),
  }
}
