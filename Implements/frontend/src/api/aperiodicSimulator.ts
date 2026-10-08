import type {
  AperiodicDeviceTrace,
  AperiodicPaperConfig,
  AperiodicSimulateRequest,
  AperiodicSimulationResult,
  JobStatus,
  PpoStatus,
  ReproduceRequest,
  ReproTarget,
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
