import { deleteOk, getJson, postJson } from '@/api/http'
import type {
  DeviceEvent,
  DeviceStates,
  DeviceTrace,
  ReaderEvent,
  ReaderTimeFreq,
  RunAnalysis,
  RunCreateInput,
  RunDetail,
  RoundSlots,
  RunRound,
  RunSnapshot,
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

export function pauseRun(id: number): Promise<RunSummary> {
  return postJson(`${BASE}/runs/${id}/pause`, {})
}

export function resumeRun(id: number): Promise<RunSummary> {
  return postJson(`${BASE}/runs/${id}/resume`, {})
}

export function setRunSpeed(id: number, speed: number | null): Promise<RunSummary> {
  return postJson(`${BASE}/runs/${id}/speed`, { speed })
}

export function setRunName(id: number, name: string | null): Promise<RunSummary> {
  return postJson(`${BASE}/runs/${id}/name`, { name })
}

/** Server-Sent Events feed of a run; consume with the browser's EventSource. */
export function runStreamUrl(id: number): string {
  return `${BASE}/runs/${id}/stream`
}

export function fetchRoundSlots(runId: number, roundId: number): Promise<RoundSlots> {
  return getJson(`${BASE}/runs/${runId}/rounds/${roundId}/slots`)
}

export type DeviceMap = { device_ids: number[]; subtypes: string[]; coverage: Record<string, number[]> }
export type Identifications = { t: number[]; device: number[]; reader: (number | null)[] }

/** Subtype of every device and, per reader, the device indices inside its coverage (engine's own test). */
export function fetchDeviceMap(id: number): Promise<DeviceMap> {
  return getJson(`${BASE}/runs/${id}/device-map`)
}

/** All identifications so far in time order (device index, time, reader). */
export function fetchIdentifications(id: number): Promise<Identifications> {
  return getJson(`${BASE}/runs/${id}/identifications`)
}

export function fetchSnapshotTimes(id: number): Promise<{ times: number[] }> {
  return getJson(`${BASE}/runs/${id}/snapshots`)
}

export function fetchSnapshot(id: number, t?: number): Promise<RunSnapshot> {
  return getJson(`${BASE}/runs/${id}/snapshot${t != null ? `?t=${t}` : ''}`)
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

export function fetchReaderTimeFreq(id: number, readerId: number, t0: number, t1: number): Promise<ReaderTimeFreq> {
  return getJson(`${BASE}/runs/${id}/readers/${readerId}/timefreq?t0=${t0}&t1=${t1}`)
}

export function fetchDeviceTrace(id: number, deviceId: number): Promise<DeviceTrace> {
  return getJson(`${BASE}/runs/${id}/device/${deviceId}/trace`)
}

export function fetchDeviceStates(id: number): Promise<{ states: DeviceStates }> {
  return getJson(`${BASE}/runs/${id}/device-states`)
}

export function fetchRunAnalysis(id: number): Promise<RunAnalysis> {
  return getJson(`${BASE}/runs/${id}/analysis`)
}

export function fetchCompareRuns(sectionId: number, runIds: number[]): Promise<{ runs: RunAnalysis[] }> {
  return postJson(`${BASE}/sections/${sectionId}/runs/compare`, { run_ids: runIds })
}
