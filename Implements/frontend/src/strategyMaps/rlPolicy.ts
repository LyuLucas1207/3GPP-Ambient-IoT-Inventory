import {
  BookOpenIcon,
  CircleHelpIcon,
  CpuIcon,
  EyeIcon,
  FastForwardIcon,
  FlagIcon,
  PlayIcon,
  RadioTowerIcon,
  RepeatIcon,
  ScaleIcon,
  ShuffleIcon,
  SigmaIcon,
  SlidersHorizontalIcon,
} from 'lucide-react'
import type { Node } from '@xyflow/react'
import { EdgeKind, NodeKind, e, fwd, leftLoop, n, type StrategyMapDef, type StrategyNodeData, type StrategySheetGroup } from './types'

const S = 'thesis.rl.map.sheet'
const F = 'thesis.rl.map.full'

/** Glossary on the left of the formulas. The loop returns further left of that box. */
const LEGEND_X = 16
const LEGEND_W = 440
const X = 620
const COLD_X = 1480
const WIDE = 760

const Y = {
  sample: 0,
  who: 320,
  decision: 460,
  input: 600,
  actor: 1120,
  action: 1600,
  frame: 1940,
  reward: 2080,
  done: 2380,
  update: 2720,
  eval: 3160,
} as const

function withSheet(node: Node<StrategyNodeData>, width: number, leadKey: string, sheet: StrategySheetGroup[]): Node<StrategyNodeData> {
  return { ...node, style: { width }, data: { ...node.data, sheetLeadKey: leadKey, sheet } }
}

function lines(keys: string[]): StrategySheetGroup {
  return { rows: keys.map((textKey) => ({ symbol: '', textKey })) }
}

const frameRows: StrategySheetGroup = {
  headingKey: `${S}.frames`,
  columns: 2,
  rows: [
    { symbol: 'S/K', textKey: `${S}.s` },
    { symbol: 'C/K', textKey: `${S}.c` },
    { symbol: 'E/K', textKey: `${S}.e` },
    { symbol: 'IDs/K', textKey: `${S}.ids` },
    { symbol: 'join/K', textKey: `${S}.join` },
    { symbol: 'log₂(K)', textKey: `${S}.k` },
    { symbol: 'p*', textKey: `${S}.p` },
    { symbol: 't', textKey: `${S}.t` },
  ],
}

const placeRows: StrategySheetGroup = {
  headingKey: `${S}.place`,
  columns: 2,
  rows: [
    { symbol: 'N/18', textKey: `${S}.readers` },
    { symbol: 'nb/17', textKey: `${S}.neighbors` },
    { symbol: 'c/n', textKey: `${S}.color` },
    { symbol: 'Fᵣ/F', textKey: `${S}.fr` },
    { symbol: 'delay', textKey: `${S}.offset` },
    { symbol: 'x', textKey: `${S}.x` },
    { symbol: 'y', textKey: `${S}.y` },
    { symbol: 'quiet', textKey: `${S}.quiet` },
    { symbol: 'frames', textKey: `${S}.framesRun` },
  ],
}

const absentRows: StrategySheetGroup = {
  headingKey: `${S}.absent`,
  rows: [
    { symbol: 'left', textKey: `${S}.left` },
    { symbol: 'energy', textKey: `${S}.energy` },
    { symbol: 'awake', textKey: `${S}.awake` },
  ],
}

const criticRows: StrategySheetGroup = {
  headingKey: `${F}.criticTitle`,
  columns: 2,
  rows: [
    { symbol: 'id', textKey: `${F}.gId` },
    { symbol: 't', textKey: `${F}.gTime` },
    { symbol: 'N/18', textKey: `${F}.gReaders` },
    { symbol: 'stop', textKey: `${F}.gStop` },
    { symbol: 'awake', textKey: `${F}.gAwake` },
    { symbol: 'E', textKey: `${F}.gEnergy` },
    { symbol: 'frame', textKey: `${F}.gFrame` },
  ],
}

const L = 'thesis.rl.map.legend'

function named(headingKey: string, rows: { symbol: string; textKey: string }[]): StrategySheetGroup {
  return { headingKey, symbolWidth: '6.4rem', rows }
}

const legendSheet: StrategySheetGroup[] = [
  named(`${L}.frame`, [
    { symbol: '$K$', textKey: `${L}.K` },
    { symbol: '$p^*$', textKey: `${L}.p` },
    { symbol: '$L$', textKey: `${L}.L` },
    { symbol: '$F$', textKey: `${L}.F` },
    { symbol: '$F_r$', textKey: `${L}.Fr` },
    { symbol: '$(\\cdot)_{\\mathrm{prev}}$', textKey: `${L}.prev` },
    { symbol: '$K_{\\mathrm{cold}}$', textKey: `${L}.Kcold` },
    { symbol: '$K_{\\mathrm{init}}$', textKey: `${L}.Kinit` },
    { symbol: '$K_{\\max}$', textKey: `${L}.Kmax` },
  ]),
  named(`${L}.net`, [
    { symbol: '$o$', textKey: `${L}.o` },
    { symbol: '$\\mu$', textKey: `${L}.mu` },
    { symbol: '$\\sigma$', textKey: `${L}.sigma` },
    { symbol: '$a_0,a_1$', textKey: `${L}.a` },
    { symbol: '$m$', textKey: `${L}.m` },
    { symbol: '$q$', textKey: `${L}.q` },
  ]),
  named(`${L}.reward`, [
    { symbol: '$\\mathrm{ids}$', textKey: `${L}.ids` },
    { symbol: '$\\mathrm{coll}$', textKey: `${L}.coll` },
    { symbol: '$t$', textKey: `${L}.t` },
    { symbol: '$\\alpha$', textKey: `${L}.alpha` },
    { symbol: '$\\beta$', textKey: `${L}.beta` },
    { symbol: '$\\mathrm{local}$', textKey: `${L}.local` },
    { symbol: '$\\mathrm{team}$', textKey: `${L}.team` },
    { symbol: '$\\mathrm{reward}$', textKey: `${L}.rew` },
  ]),
  named(`${L}.update`, [
    { symbol: '$V$', textKey: `${L}.V` },
    { symbol: '$r$', textKey: `${L}.r` },
    { symbol: '$\\delta$', textKey: `${L}.delta` },
    { symbol: '$\\mathrm{boot}$', textKey: `${L}.boot` },
    { symbol: '$A$', textKey: `${L}.A` },
    { symbol: '$\\gamma$', textKey: `${L}.gamma` },
    { symbol: '$\\lambda$', textKey: `${L}.lambda` },
    { symbol: '$d$', textKey: `${L}.d` },
    { symbol: '$\\pi$', textKey: `${L}.pi` },
    { symbol: '$\\rho$', textKey: `${L}.rho` },
    { symbol: '$\\epsilon$', textKey: `${L}.eps` },
    { symbol: '$R$', textKey: `${L}.R` },
    { symbol: '$H$', textKey: `${L}.H` },
    { symbol: '$c_V,c_H$', textKey: `${L}.c` },
    { symbol: '$g$', textKey: `${L}.g` },
    { symbol: '$n_{\\mathrm{steps}}$', textKey: `${L}.n` },
  ]),
]

const again = e('again', 'update', 'sample', 'thesis.rl.map.edge.again', EdgeKind.Normal, 'rs', 'rt', 'step', 120)

export const rlPolicyMap: StrategyMapDef = {
  summaryKey: 'thesis.rl.subtitle',
  stepsKey: 'thesis.rl.subtitle',
  helpPrefix: 'rl',
  helpBase: 'thesis.rl.map.help',
  nodes: [
    withSheet(n('letters', LEGEND_X, Y.action, 'thesis.rl.map.letters', NodeKind.Energy, BookOpenIcon), LEGEND_W, `${L}.lead`, legendSheet),
    withSheet(n('sample', X, Y.sample, 'thesis.rl.map.sample', NodeKind.Protocol, ShuffleIcon), WIDE, `${F}.sampleLead`, [
      lines([`${F}.readers`, `${F}.devices`, `${F}.offsets`, `${F}.resource`, `${F}.mix`]),
    ]),
    n('who', X, Y.who, 'thesis.rl.map.who', NodeKind.Protocol, RadioTowerIcon),
    n('decision', X, Y.decision, 'thesis.rl.map.decision', NodeKind.Decision, CircleHelpIcon),
    withSheet(n('cold', COLD_X, Y.decision, 'thesis.rl.map.cold', NodeKind.Protocol, FastForwardIcon), 460, `${F}.coldLead`, [
      lines([`${F}.coldK`, `${F}.coldP`]),
    ]),
    withSheet(n('input', X, Y.input, 'thesis.rl.map.input', NodeKind.Energy, EyeIcon), WIDE, `${S}.inputLead`, [frameRows, placeRows, absentRows]),
    withSheet(n('actor', X, Y.actor, 'thesis.rl.map.actor', NodeKind.Protocol, CpuIcon), WIDE, `${F}.actorLead`, [
      lines([`${F}.net`, `${F}.draw`, `${F}.mean`]),
      criticRows,
      lines([`${F}.criticNote`, `${F}.zero`]),
    ]),
    withSheet(n('action', X, Y.action, 'thesis.rl.map.action', NodeKind.Success, SlidersHorizontalIcon), WIDE, `${F}.actionLead`, [
      lines([`${F}.m`, `${F}.q`, `${F}.L`, `${F}.p`, `${F}.example`]),
    ]),
    n('frame', X, Y.frame, 'thesis.rl.map.frame', NodeKind.Protocol, PlayIcon),
    withSheet(n('reward', X, Y.reward, 'thesis.rl.map.reward', NodeKind.Energy, SigmaIcon), WIDE, `${F}.rewardLead`, [
      lines([`${F}.local`, `${F}.team`, `${F}.reward`, `${F}.ab`]),
    ]),
    withSheet(n('done', X, Y.done, 'thesis.rl.map.done', NodeKind.Protocol, FlagIcon), WIDE, `${F}.doneLead`, [
      lines([`${F}.stay`, `${F}.stop`, `${F}.boot`, `${F}.count`]),
    ]),
    withSheet(n('update', X, Y.update, 'thesis.rl.map.update', NodeKind.Protocol, RepeatIcon), WIDE, `${F}.updateLead`, [
      lines([`${F}.gae`, `${F}.loss`, `${F}.hp`, `${F}.sb3`, `${F}.scale`, `${F}.save`]),
    ]),
    withSheet(n('eval', X, Y.eval, 'thesis.rl.map.eval', NodeKind.Success, ScaleIcon), WIDE, `${F}.evalLead`, []),
  ],
  edges: [
    e('go', 'sample', 'who', ''),
    e('due', 'who', 'decision', ''),
    e('yes', 'decision', 'cold', 'thesis.rl.map.edge.yes', EdgeKind.Normal, ...fwd),
    e('no', 'decision', 'input', 'thesis.rl.map.edge.no'),
    e('join', 'cold', 'frame', '', EdgeKind.Normal, 'bs', 'rt'),
    e('obs', 'input', 'actor', ''),
    e('act', 'actor', 'action', 'thesis.rl.map.edge.act'),
    e('apply', 'action', 'frame', 'thesis.rl.map.edge.apply'),
    e('score', 'frame', 'reward', 'thesis.rl.map.edge.score'),
    e('next', 'reward', 'done', ''),
    e('stay', 'done', 'who', 'thesis.rl.map.edge.loop', EdgeKind.Normal, ...leftLoop),
    e('fresh', 'done', 'sample', 'thesis.rl.map.edge.fresh', EdgeKind.Normal, 'rs', 'rt'),
    e('batch', 'done', 'update', 'thesis.rl.map.edge.batch'),
    again,
    e('scored', 'update', 'eval', 'thesis.rl.map.edge.eval'),
  ],
}
