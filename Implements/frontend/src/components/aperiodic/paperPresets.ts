import type { AperiodicSimulateRequest } from '@/types/aperiodicSimulation'

// Interactive runs of the paper's Section V scenarios: N_tot = 15000 devices of
// all three types, F = 8, FA 0.1 %, MD 1 %, capture 6 dB (Table II).

export type PaperFigure = 'fig5a' | 'fig5b' | 'fig6a' | 'fig6b' | 'fig7'
export type PaperCurve = 'aperiodic' | 'periodic_Ng1' | 'periodic_Ng4' | 'recurrent_ppo' | 'dfsa_schoute' | 'cmebe'

export const PAPER_FIGURES: PaperFigure[] = ['fig5a', 'fig5b', 'fig6a', 'fig6b', 'fig7']

export function curvesFor(fig: PaperFigure): PaperCurve[] {
  return fig === 'fig7' ? ['recurrent_ppo', 'dfsa_schoute', 'cmebe'] : ['aperiodic', 'periodic_Ng1', 'periodic_Ng4']
}

const COMMON: Partial<AperiodicSimulateRequest> = {
  num_devices: 15000,
  type_mix: 'mixed',
  F: 8,
  impairments_enabled: true,
  capture_ratio_db: 6,
  missed_detection_rate: 0.01,
  false_alarm_rate: 0.001,
  runtime_mode: 'interactive',
  num_episodes: 1,
  enforce_midround_depletion: true,
  p_initial: 1,
  alpha: 0.5,
}

const FIGURE: Record<PaperFigure, Partial<AperiodicSimulateRequest>> = {
  fig5a: { harvesting_scenario: 'single_source', L_fixed: 16, max_time_s: 1200 },
  fig5b: { harvesting_scenario: 'single_source', L_fixed: 1, max_time_s: 1200 },
  fig6a: { harvesting_scenario: 'multi_source', L_fixed: 16, max_time_s: 800 },
  fig6b: { harvesting_scenario: 'multi_source', L_fixed: 1, max_time_s: 800 },
  fig7: { harvesting_scenario: 'multi_source', L_initial: 1, max_time_s: 400 },
}

const CURVE: Record<PaperCurve, Partial<AperiodicSimulateRequest>> = {
  aperiodic: { paging_mode: 'aperiodic', N_g: 1, controller: 'pfsa_pze', ppo_enabled: false, L_mode: 'fixed' },
  periodic_Ng1: { paging_mode: 'periodic', N_g: 1, controller: 'pfsa_pze', ppo_enabled: false, L_mode: 'fixed' },
  periodic_Ng4: { paging_mode: 'periodic', N_g: 4, controller: 'pfsa_pze', ppo_enabled: false, L_mode: 'fixed' },
  recurrent_ppo: { paging_mode: 'aperiodic', N_g: 1, controller: 'recurrent_ppo', ppo_enabled: true, L_mode: 'adaptive' },
  dfsa_schoute: { paging_mode: 'aperiodic', N_g: 1, controller: 'dfsa_schoute', ppo_enabled: false, L_mode: 'adaptive' },
  cmebe: { paging_mode: 'aperiodic', N_g: 1, controller: 'cmebe', ppo_enabled: false, L_mode: 'adaptive' },
}

export function paperRequest(base: AperiodicSimulateRequest, fig: PaperFigure, curve: PaperCurve): AperiodicSimulateRequest {
  return { ...base, ...COMMON, ...FIGURE[fig], ...CURVE[curve] }
}
