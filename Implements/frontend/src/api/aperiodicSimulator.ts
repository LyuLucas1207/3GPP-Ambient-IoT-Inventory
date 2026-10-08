import type {
  AperiodicDeviceTrace,
  AperiodicPaperConfig,
  AperiodicSimulateRequest,
  AperiodicSimulationResult,
  JobStatus,
  PpoStatus,
  ReproduceRequest,
  ReproTarget,
  StepNextResult,
  StepSessionInfo,
} from '../types/aperiodicSimulation'
import { getJson, postJson } from './http'

const BASE = '/api/aperiodic-simulator'

export function fetchAperiodicPaperConfig(): Promise<AperiodicPaperConfig> {
  return getJson(`${BASE}/config/paper`)
}

export function runAperiodicSimulation(req: AperiodicSimulateRequest): Promise<AperiodicSimulationResult> {
  return postJson(`${BASE}/simulate`, req)
}

export function fetchAperiodicDeviceTrace(
  runId: string,
  controller: string,
  deviceId: number,
): Promise<AperiodicDeviceTrace> {
  return getJson(`${BASE}/runs/${runId}/controllers/${controller}/devices/${deviceId}/trace`)
}

export function fetchPpoStatus(): Promise<PpoStatus> {
  return getJson(`${BASE}/ppo/status`)
}

export function startReproduction(target: ReproTarget, req: ReproduceRequest): Promise<JobStatus> {
  return postJson(`${BASE}/reproduce/${target}`, req)
}

export function fetchJob(jobId: string): Promise<JobStatus> {
  return getJson(`${BASE}/jobs/${jobId}`)
}

export interface PaperReference {
  panel: string
  figure: string
  curves: Record<string, { x: number[]; y: number[] }>
}

export function fetchPaperReference(panelId: string): Promise<PaperReference> {
  return getJson(`${BASE}/paper-reference/${panelId}`)
}

export function createStepSession(config: AperiodicSimulateRequest, nDevices: number): Promise<StepSessionInfo> {
  return postJson(`${BASE}/step-sessions`, { config, n_devices: nDevices })
}

export function nextStepRound(sessionId: string, skipEmpty: boolean): Promise<StepNextResult> {
  return postJson(`${BASE}/step-sessions/${sessionId}/next`, { skip_empty: skipEmpty })
}

export function deleteStepSession(sessionId: string): void {
  void fetch(`${BASE}/step-sessions/${sessionId}`, { method: 'DELETE' }).catch(() => undefined)
}
