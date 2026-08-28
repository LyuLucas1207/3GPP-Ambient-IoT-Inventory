import type { DeviceScientificTrace, PaperConfig, SimulateRequest, SimulationResult } from '../types/simulation'

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    return JSON.stringify(body.detail ?? body)
  } catch {
    return res.statusText
  }
}

export async function fetchHealth(): Promise<boolean> {
  try {
    const res = await fetch('/api/health')
    return res.ok
  } catch {
    return false
  }
}

export async function fetchPaperConfig(): Promise<PaperConfig> {
  const res = await fetch('/api/config/paper')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function runSimulation(req: SimulateRequest): Promise<SimulationResult> {
  const res = await fetch('/api/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function fetchFig5bReference(): Promise<NonNullable<SimulationResult['paper_fig5b']>> {
  const res = await fetch('/api/config/fig5b-reference')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function fetchDeviceTrace(
  runId: string,
  strategy: string,
  deviceId: number,
): Promise<DeviceScientificTrace> {
  const res = await fetch(
    `/api/simulation/${runId}/strategies/${strategy}/devices/${deviceId}/trace`,
  )
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
