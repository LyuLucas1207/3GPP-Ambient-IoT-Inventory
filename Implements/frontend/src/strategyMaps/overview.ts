import {
  ArrowDownToLineIcon,
  CheckIcon,
  CircleHelpIcon,
  DicesIcon,
  HourglassIcon,
  RadioTowerIcon,
  SendIcon,
  XIcon,
} from 'lucide-react'
import { EdgeKind, NodeKind, e, n, type StrategyMapDef } from './types'

/** ASCII: YES/happy path is the right column; skip/collision sit left of it; wait is further left. */
const W = -480
const L = 48
const M = 560
const Y = 160

export const overviewMap: StrategyMapDef = {
  summaryKey: 'overview.lead',
  stepsKey: 'overview.steps',
  helpPrefix: 'overview',
  nodes: [
    n('reader', M, 0, 'overview.node.reader', NodeKind.Protocol, RadioTowerIcon),
    n('onq', M, Y, 'overview.node.onq', NodeKind.Decision, CircleHelpIcon),
    n('heard', M, Y * 2, 'overview.node.heard', NodeKind.Protocol, RadioTowerIcon),
    n('draw', M, Y * 3, 'overview.node.draw', NodeKind.Decision, CircleHelpIcon),
    n('ao', M, Y * 4, 'overview.node.ao', NodeKind.Protocol, DicesIcon),
    n('ok', M, Y * 5, 'overview.node.ok', NodeKind.Success, CheckIcon),
    n('m2', M, Y * 6, 'overview.node.m2', NodeKind.Protocol, ArrowDownToLineIcon),
    n('m3', M, Y * 7, 'overview.node.m3', NodeKind.Protocol, SendIcon),
    n('done', M, Y * 8, 'overview.node.done', NodeKind.Success, CheckIcon),
    n('skip', L, Y * 4, 'overview.node.skip', NodeKind.Failure, HourglassIcon),
    n('col', L, Y * 5, 'overview.node.col', NodeKind.Failure, XIcon),
    n('wait', W, Y * 8, 'overview.node.wait', NodeKind.Energy, HourglassIcon),
  ],
  edges: [
    e('pg', 'reader', 'onq', 'overview.edge.paging'),
    e('yes', 'onq', 'heard', 'overview.edge.yes'),
    e('no', 'onq', 'wait', 'overview.edge.no', EdgeKind.Retry, 'ls', 'tt'),
    e('hp', 'heard', 'draw', ''),
    e('join', 'draw', 'ao', 'overview.edge.join'),
    e('sk', 'draw', 'skip', 'overview.edge.skip', EdgeKind.Retry, 'ls', 'rt'),
    e('succ', 'ao', 'ok', 'overview.edge.success'),
    e('hit', 'ao', 'col', 'overview.edge.collision', EdgeKind.Retry, 'ls', 'rt'),
    e('m23', 'ok', 'm2', ''),
    e('m32', 'm2', 'm3', ''),
    e('fin', 'm3', 'done', ''),
    e('skw', 'skip', 'wait', '', EdgeKind.Retry, 'ls', 'rt'),
    e('clw', 'col', 'wait', '', EdgeKind.Retry, 'ls', 'rt'),
    e('nxt', 'wait', 'onq', 'overview.edge.next', EdgeKind.Retry, 'rs', 'lt'),
  ],
}
