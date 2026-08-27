import { describe, expect, it } from 'vitest'
import {
  buildAdminAlertsSocketUrl,
  connectAdminAlertsSocket,
  parseAdminAlertMessage,
} from '../adminAlertsSocket'

describe('buildAdminAlertsSocketUrl', () => {
  it('derives ws:// from an http:// base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('derives wss:// from an https:// base URL', () => {
    const url = buildAdminAlertsSocketUrl('https://api.example.com', 'abc123')
    expect(url).toBe('wss://api.example.com/ws/admin/alerts?token=abc123')
  })

  it('strips a trailing slash from the base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000/', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('strips multiple trailing slashes from the base URL', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000//', 'abc123')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=abc123')
  })

  it('URL-encodes the token', () => {
    const url = buildAdminAlertsSocketUrl('http://127.0.0.1:8000', 'a b+c/d')
    expect(url).toBe('ws://127.0.0.1:8000/ws/admin/alerts?token=a%20b%2Bc%2Fd')
  })
})

describe('parseAdminAlertMessage', () => {
  it('accepts a well-formed monitoring_event payload', () => {
    const raw = JSON.stringify({
      type: 'monitoring_event',
      event_id: 1,
      session_id: 2,
      event_type: 'FACE_ABSENT',
      severity: 'high',
      status: 'PENDING_REVIEW',
    })

    expect(parseAdminAlertMessage(raw)).toEqual({
      type: 'monitoring_event',
      event_id: 1,
      session_id: 2,
      event_type: 'FACE_ABSENT',
      severity: 'high',
      status: 'PENDING_REVIEW',
    })
  })

  it('returns null for malformed JSON without throwing', () => {
    expect(() => parseAdminAlertMessage('{not valid json')).not.toThrow()
    expect(parseAdminAlertMessage('{not valid json')).toBeNull()
  })

  it('returns null for a non-object JSON value', () => {
    expect(parseAdminAlertMessage('"just a string"')).toBeNull()
    expect(parseAdminAlertMessage('42')).toBeNull()
    expect(parseAdminAlertMessage('null')).toBeNull()
  })

  it('ignores an unrelated message type', () => {
    const raw = JSON.stringify({ type: 'something_else', foo: 'bar' })
    expect(parseAdminAlertMessage(raw)).toBeNull()
  })
})

describe('connectAdminAlertsSocket', () => {
  it('does not open a connection when no token is supplied', () => {
    expect(connectAdminAlertsSocket({ token: '' })).toBeNull()
    expect(connectAdminAlertsSocket({})).toBeNull()
  })
})
