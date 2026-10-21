import { deleteOk, getJson, postJson } from '@/api/http'
import type {
  DeviceEvent,
  DeviceStates,
  ReaderEvent,
  RunCreateInput,
  RunDetail,
  RunRound,
  RunSummary,
  Timeline,
} from '@/types/thesis'

const BASE = '/api/thesis-simulator'

export function fetchRuns(sectionId: number): Promise<RunSummary[]> {
  return getJson(`${BASE}/sections/${sectionId}/runs`)
}

export function createRun(sectionId: number, body: RunCreateInput): Promise<RunDetail> {
  return postJson(`${BASE}/sections/${sectionId}/runs`, body)
}

export function fetchRun(id: number): Promise<RunDetail> {
  return getJson(`${BASE}/runs/${id}`)
}

export function deleteRun(id: number): Promise<void> {
  return deleteOk(`${BASE}/runs/${id}`)
}

export function stopRun(id: number): Promise<RunSummary> {
  return postJson(`${BASE}/runs/${id}/stop`, {})
}

export function fetchRunSummary(id: number): Promise<RunSummary> {
  return getJson(`${BASE}/runs/${id}/summary`)
}

export function fetchDeviceEvents(
  id: number,
  params: { device_id?: number; since?: number; limit?: number } = {},
): Promise<{ events: DeviceEvent[]; next_since: number | null }> {
  const search = new URLSearchParams()
  if (params.device_id != null) search.set('device_id', String(params.device_id))
  if (params.since != null) search.set('since', String(params.since))
  if (params.limit != null) search.set('limit', String(params.limit))
  const qs = search.toString()
  return getJson(`${BASE}/runs/${id}/device-events${qs ? `?${qs}` : ''}`)
}

export function fetchReaderEvents(
  id: number,
  params: { reader_id?: number; since?: number; limit?: number } = {},
): Promise<{ events: ReaderEvent[]; next_since: number | null }> {
  const search = new URLSearchParams()
  if (params.reader_id != null) search.set('reader_id', String(params.reader_id))
  if (params.since != null) search.set('since', String(params.since))
  if (params.limit != null) search.set('limit', String(params.limit))
  const qs = search.toString()
  return getJson(`${BASE}/runs/${id}/reader-events${qs ? `?${qs}` : ''}`)
}

export function fetchRounds(id: number, readerId?: number): Promise<RunRound[]> {
  const qs = readerId != null ? `?reader_id=${readerId}` : ''
  return getJson(`${BASE}/runs/${id}/rounds${qs}`)
}

export function fetchTimeline(id: number, deviceId: number): Promise<Timeline> {
  return getJson(`${BASE}/runs/${id}/device/${deviceId}/timeline`)
}

export function fetchDeviceStates(id: number): Promise<{ states: DeviceStates }> {
  return getJson(`${BASE}/runs/${id}/device-states`)
}
