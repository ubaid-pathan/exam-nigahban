// Pure, framework-free performance-measurement helpers for the Milestone 3
// real-time camera performance test. No DOM, no React -- independently
// testable, mirroring the isolation pattern already used by decode.js.

/**
 * Accumulates a stream of millisecond latency samples and can report
 * count/min/max/avg/median on demand without needing to store the full
 * history externally.
 *
 * Milestone 5.4: count/min/max/avg are maintained incrementally in
 * record() (O(1) per sample) rather than rescanning the full `values`
 * array on every read, per Milestone 5.3's finding that recomputing these
 * from scratch on every 500ms live-stats tick was real, if modest, cost
 * that also grows with session length. `values` itself is still kept
 * (needed for median, which has no O(1) incremental form without a more
 * complex two-heap structure that would be over-engineering for this
 * spike) -- but median is no longer computed automatically on every read;
 * see the `includeMedian` param on updateLiveStatsDisplay in
 * PhoneDetectionSpikePage.jsx, which now only requests it on the final
 * (test-stop) stats update, not on every periodic live tick.
 */
export function createLatencyTracker() {
  const values = []
  let sum = 0
  let runningMin = null
  let runningMax = null
  return {
    record(ms) {
      if (!Number.isFinite(ms)) return
      values.push(ms)
      sum += ms
      if (runningMin === null || ms < runningMin) runningMin = ms
      if (runningMax === null || ms > runningMax) runningMax = ms
    },
    count: () => values.length,
    min: () => runningMin,
    max: () => runningMax,
    avg: () => (values.length ? sum / values.length : null),
    // Milestone 5.1: median alongside mean, since a handful of slow outliers
    // (GC pauses, contention spikes) can otherwise skew the average without
    // reflecting the "typical" inference the schedule comparison cares about.
    // Deliberately NOT maintained incrementally (median has no cheap O(1)
    // running update) -- calling code is expected to request it only when
    // actually needed (see the doc comment above), not on every tick.
    median: () => {
      if (!values.length) return null
      const sorted = [...values].sort((a, b) => a - b)
      const mid = Math.floor(sorted.length / 2)
      return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
    },
    values: () => [...values],
    reset() {
      values.length = 0
      sum = 0
      runningMin = null
      runningMax = null
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
