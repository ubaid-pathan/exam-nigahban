// Milestone 6 Phase 2 Step 6: focused contract test for postMonitoringEvent's
// optional `source` field (added in Step 5/6 to let a YOLOX-produced event
// identify itself as "browser_yolox" instead of the backend's implicit
// "browser_mediapipe" default -- see backend/app/schemas/monitoring.py).
// The other thin api/*.js wrappers in this codebase have no dedicated test
// files (they're direct axios pass-throughs); this one exists specifically
// to verify the exact request-body contract this milestone's "most
// important" check depends on.

import { describe, expect, it, vi } from 'vitest'

const { post } = vi.hoisted(() => ({ post: vi.fn(async () => ({ data: { id: 1 } })) }))
vi.mock('../client', () => ({ default: { post } }))

import { postMonitoringEvent } from '../monitoring'

describe('postMonitoringEvent - source contract', () => {
  it('includes source in the request body when the event sets one (YOLOX path)', async () => {
    await postMonitoringEvent(42, {
      eventType: 'MOBILE_PHONE',
      severity: 'high',
      confidence: 0.9213,
      durationSeconds: 1.1,
      occurrences: 1,
      source: 'browser_yolox',
    })

    expect(post).toHaveBeenCalledWith(
      '/api/monitoring/events',
      expect.objectContaining({ event_type: 'MOBILE_PHONE', source: 'browser_yolox' }),
    )
  })

  it('omits source entirely when the event does not set one (MediaPipe path, unchanged)', async () => {
    await postMonitoringEvent(42, {
      eventType: 'HEAD_LEFT',
      severity: 'medium',
      confidence: 0.87,
      durationSeconds: 4.2,
      occurrences: 3,
    })

    const [, body] = post.mock.calls.at(-1)
    expect('source' in body).toBe(false)
  })

  it('still includes evidence_image_base64 alongside source when both are present', async () => {
    await postMonitoringEvent(42, {
      eventType: 'MOBILE_PHONE',
      severity: 'high',
      confidence: 0.92,
      durationSeconds: 1,
      occurrences: 1,
      source: 'browser_yolox',
      evidenceImageBase64: 'base64-jpeg',
    })

    const [, body] = post.mock.calls.at(-1)
    expect(body).toMatchObject({ source: 'browser_yolox', evidence_image_base64: 'base64-jpeg' })
  })
})
