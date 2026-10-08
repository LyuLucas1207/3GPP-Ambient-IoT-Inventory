import type { DeviceScientificTrace, PaperConfig, SimulateRequest, SimulationResult } from '../types/simulation'
import { getJson, postJson } from './http'

const BASE = '/api/simulator'

export { fetchHealth } from './http'

export function fetchPaperConfig(): Promise<PaperConfig> {
  return getJson(`${BASE}/config/paper`)
}

export function runSimulation(req: SimulateRequest): Promise<SimulationResult> {
  return postJson(`${BASE}/simulate`, req)
}

export function fetchFig5bReference(): Promise<NonNullable<SimulationResult['paper_fig5b']>> {
  return getJson(`${BASE}/config/fig5b-reference`)
}

export function fetchDeviceTrace(
  runId: string,
  strategy: string,
  deviceId: number,
): Promise<DeviceScientificTrace> {
  return getJson(`${BASE}/runs/${runId}/strategies/${strategy}/devices/${deviceId}/trace`)
}
