import { TermId } from '@/explain/ids'

/** KaTeX bodies for paper Table 1 keys shown in the Setup panel. */
export const PAPER_TEX: Record<string, string> = {
  N: 'N',
  E_max_nJ: 'E_{\\max}',
  E_up_nJ: 'E_{\\mathrm{up}}',
  E_low_nJ: 'E_{\\mathrm{low}}',
  P_rx_uW: 'P_{\\mathrm{rx}}',
  P_tx_uW: 'P_{\\mathrm{tx}}',
  P_sl_uW: 'P_{\\mathrm{sl}}',
  paging_ms: 'T_{\\mathrm{pag}}',
  T_pg_ms: 'T_{\\mathrm{pg}}',
  Msg1_ms: '\\mathrm{Msg}_{1}',
  Msg2_ms: '\\mathrm{Msg}_{2}',
  Msg3_ms: '\\mathrm{Msg}_{3}',
  T_on_DCM_ms: 'T_{\\mathrm{on}}^{\\mathrm{DCM}}',
  T_on_timer_ms: 'T_{\\mathrm{on}}^{\\mathrm{timer}}',
  n_time_ao: 'N_{t}',
  n_freq_ao: 'N_{f}',
  n_ao: 'N_{\\mathrm{AO}}',
}

export const PAPER_TERM: Partial<Record<string, TermId>> = {
  E_max_nJ: TermId.Emax,
  E_up_nJ: TermId.Eup,
  E_low_nJ: TermId.Elow,
  P_rx_uW: TermId.Prx,
  P_tx_uW: TermId.Ptx,
  P_sl_uW: TermId.Psl,
  paging_ms: TermId.Paging,
  T_pg_ms: TermId.Tpg,
  Msg1_ms: TermId.Msg1,
  Msg2_ms: TermId.Msg2,
  Msg3_ms: TermId.Msg3,
  T_on_DCM_ms: TermId.TonDcm,
  T_on_timer_ms: TermId.TonTimer,
  n_time_ao: TermId.Ao,
  n_freq_ao: TermId.Ao,
  n_ao: TermId.Ao,
}

export const PAPER_UNIT: Record<string, string> = {
  E_max_nJ: 'nJ',
  E_up_nJ: 'nJ',
  E_low_nJ: 'nJ',
  P_rx_uW: 'μW',
  P_tx_uW: 'μW',
  P_sl_uW: 'μW',
  paging_ms: 'ms',
  T_pg_ms: 'ms',
  Msg1_ms: 'ms',
  Msg2_ms: 'ms',
  Msg3_ms: 'ms',
  T_on_DCM_ms: 'ms',
  T_on_timer_ms: 'ms',
}
