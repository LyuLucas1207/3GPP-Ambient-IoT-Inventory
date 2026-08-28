import { TermId } from '@/explain/ids'

/** Address bar: `/glossary`. */
export const GLOSSARY_PATH = '/glossary'

export type GlossaryKind = 'abbr' | 'symbol'

export const GLOSSARY_KINDS: GlossaryKind[] = ['abbr', 'symbol']

export interface GlossaryDef {
  id: string
  kind: GlossaryKind
  /** Reuse `terms.<id>` copy when set. */
  termId?: TermId
  /** KaTeX body for symbol titles, without dollar signs. */
  tex?: string
  aliases: string[]
}

function abbr(id: string, aliases: string[], termId?: TermId): GlossaryDef {
  return { id, kind: 'abbr', termId, aliases }
}

function symbol(id: string, aliases: string[], tex: string, termId?: TermId): GlossaryDef {
  return { id, kind: 'symbol', termId, tex, aliases }
}

export const GLOSSARY: GlossaryDef[] = [
  abbr('g3gpp', ['3GPP', '3gpp']),
  abbr('aiot', ['A-IoT', 'AIoT', 'Ambient IoT']),
  abbr('bs', ['BS', 'base station', 'gNB', 'Reader']),
  abbr('cw', ['CW', 'continuous wave']),
  abbr('wur', ['WUR', 'wake-up receiver']),
  abbr('ic', ['IC']),
  abbr('rf', ['RF']),
  abbr('cbra', ['CBRA', 'cbra'], TermId.Cbra),
  abbr('ao', ['AO', 'ao'], TermId.Ao),
  abbr('prach', ['PRACH']),
  abbr('msg1', ['Msg1', 'Msg 1'], TermId.Msg1),
  abbr('msg2', ['Msg2', 'Msg 2'], TermId.Msg2),
  abbr('msg3', ['Msg3', 'Msg 3'], TermId.Msg3),
  abbr('em', ['EM'], TermId.Em),
  abbr('dcm', ['DCM'], TermId.Dcm),
  abbr('cdf', ['CDF']),
  abbr('rx', ['RX']),
  abbr('tx', ['TX']),
  abbr('off', ['OFF']),
  abbr('on', ['ON']),
  abbr('sleep', ['SLEEP']),
  abbr('done', ['DONE']),
  abbr('t50', ['T50', 'T_50'], TermId.T50),
  abbr('t90', ['T90', 'T_90'], TermId.T90),
  abbr('t99', ['T99', 'T_99'], TermId.T99),
  abbr('nj', ['nJ']),
  abbr('uw', ['μW', 'uW']),
  abbr('nw', ['nW']),
  abbr('dbm', ['dBm']),
  abbr('ms', ['ms']),

  symbol('pin', ['p_in', 'P_in', 'pin', 'p_{in}'], 'p_{\\mathrm{in}}', TermId.Pin),
  symbol('peh', ['P_eh', 'Peh', 'P_{eh}'], 'P_{\\mathrm{eh}}', TermId.Peh),
  symbol('xi', ['ξ', 'xi', 'eta'], '\\xi', TermId.Xi),
  symbol('ees', ['e_ES', 'eES', 'e_{ES}'], 'e_{\\mathrm{ES}}', TermId.Ees),
  symbol('emax', ['E_max', 'Emax', 'E_{max}'], 'E_{\\max}', TermId.Emax),
  symbol('eup', ['E_up', 'Eup', 'E_{up}'], 'E_{\\mathrm{up}}', TermId.Eup),
  symbol('elow', ['E_low', 'Elow', 'E_{low}'], 'E_{\\mathrm{low}}', TermId.Elow),
  symbol('prx', ['P_rx', 'Prx', 'P_{rx}'], 'P_{\\mathrm{rx}}', TermId.Prx),
  symbol('ptx', ['P_tx', 'Ptx', 'P_{tx}'], 'P_{\\mathrm{tx}}', TermId.Ptx),
  symbol('psl', ['P_sl', 'Psl', 'P_{sl}'], 'P_{\\mathrm{sl}}', TermId.Psl),
  symbol('paccess', ['p_access', 'paccess', 'p_{access}'], 'p_{\\mathrm{access}}', TermId.Paccess),
  symbol('tpg', ['T_pg', 'Tpg', 'T_{pg}'], 'T_{\\mathrm{pg}}', TermId.Tpg),
  symbol('tpag', ['T_pag', 'Tpag', 'T_{pag}'], 'T_{\\mathrm{pag}}'),
  symbol('tonTimer', ['T_on_timer', 'T_{on,timer}'], 'T_{\\mathrm{on}}^{\\mathrm{timer}}', TermId.TonTimer),
  symbol('tonDcm', ['T_on_DCM', 'T_{on}^{DCM}'], 'T_{\\mathrm{on}}^{\\mathrm{DCM}}', TermId.TonDcm),
  symbol('nDevices', ['N'], 'N'),
  symbol('ng', ['N_g', 'Ng', 'N_{g}'], 'N_{g}'),
  symbol('nt', ['N_t', 'Nt', 'N_{t}'], 'N_{t}'),
  symbol('nf', ['N_f', 'Nf', 'N_{f}'], 'N_{f}'),
  symbol('nao', ['N_AO', 'N_{AO}'], 'N_{\\mathrm{AO}}'),
  symbol('dt', ['dt', 'Δt'], '\\mathrm{d}t'),
]
