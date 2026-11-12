import { getJson, postJson } from '@/api/http'
import type { PolicyInfo, TrainingExperiment, TrainingExperimentDetail } from '@/types/thesis'

const BASE = '/api/thesis-simulator'

/** Policies in the registry (``app/thesis_simulator/rl/policies``), selectable by ``policy_id``. */
export function fetchPolicies(): Promise<PolicyInfo[]> {
  return getJson(`${BASE}/policies`)
}

/** Training configs and their runs in ``training/outputs`` (training itself runs from the CLI). */
export function fetchTrainingExperiments(): Promise<TrainingExperiment[]> {
  return getJson(`${BASE}/training/experiments`)
}

export function fetchTrainingExperiment(name: string): Promise<TrainingExperimentDetail> {
  return getJson(`${BASE}/training/experiments/${encodeURIComponent(name)}`)
}

export function trainingPlotUrl(experiment: string, run: string, plot: string): string {
  return `${BASE}/training/experiments/${encodeURIComponent(experiment)}/runs/${encodeURIComponent(run)}/plots/${encodeURIComponent(plot)}`
}

export function promoteTrainingRun(experiment: string, run: string, body: { policy_id?: string | null; force?: boolean }): Promise<{ policy_id: string }> {
  return postJson(`${BASE}/training/experiments/${encodeURIComponent(experiment)}/runs/${encodeURIComponent(run)}/promote`, body)
}
