import {
  BatteryChargingIcon,
  CheckIcon,
  CircleHelpIcon,
  EyeIcon,
  MoonIcon,
  RadioTowerIcon,
  SendIcon,
  TimerIcon,
  UnplugIcon,
  XIcon,
} from 'lucide-react'
import { EdgeKind, NodeKind, back, e, fwd, leftLoop, n, up, type StrategyMapDef } from './types'

const M = 72
const S = 600
const Y = 180

export const dcmOneGroupMap: StrategyMapDef = {
  summaryKey: 'maps.dcm1.summary',
  stepsKey: 'maps.dcm1.steps',
  helpPrefix: 'dcm1',
  nodes: [
    n('off', M, 0, 'OFF / Harvest', NodeKind.Energy, BatteryChargingIcon),
    n('pre', M, Y, 'Pre-inventory ON · 18 ms', NodeKind.Energy, TimerIcon),
    n('sync', M, Y * 2, 'First paging / sync', NodeKind.Protocol, RadioTowerIcon),
    n('on', M, Y * 3, 'DCM ON · 3 ms', NodeKind.Energy, EyeIcon),
    n('draw', M, Y * 4, 'Access probability', NodeKind.Decision, CircleHelpIcon),
    n('cbra', M, Y * 5, 'Msg2 → Msg3', NodeKind.Protocol, SendIcon),
    n('done', M, Y * 6, 'DONE', NodeKind.Success, CheckIcon),
    n('sleep', S, Y * 3, 'DCM SLEEP · 9 ms', NodeKind.Energy, MoonIcon),
    n('col', S, Y * 4, 'Collision → next 12 ms', NodeKind.Failure, XIcon),
    n('lose', S, Y, 'E_low / lose sync', NodeKind.Failure, UnplugIcon),
  ],
  edges: [
    e('a', 'off', 'pre', 'E ≥ E_up', EdgeKind.Threshold),
    e('b', 'pre', 'sync', 'paging heard'),
    e('c', 'pre', 'off', 'no paging', EdgeKind.Retry, ...leftLoop),
    e('d', 'sync', 'on', 'aligned to 12 ms'),
    e('e', 'on', 'draw', 'eligible'),
    e('f', 'draw', 'cbra', 'Msg1 singleton'),
    e('g', 'cbra', 'done', 'Msg3 ok'),
    e('h', 'on', 'sleep', 'window end', EdgeKind.Sleep, ...fwd, 'straight'),
    e('i', 'sleep', 'on', 'next paging', EdgeKind.Sleep, ...back, 'straight'),
    e('j', 'draw', 'on', 'no attempt (pays P_rx)', EdgeKind.Retry, ...leftLoop),
    e('k', 'draw', 'col', 'collision', EdgeKind.Retry, ...fwd, 'straight'),
    e('l', 'col', 'sleep', 'retry', EdgeKind.Retry, ...up),
    e('m', 'on', 'lose', 'E ≤ E_low', EdgeKind.Threshold, 'ts', 'lt'),
    e('n', 'lose', 'off', 'OFF', EdgeKind.Threshold, 'ts', 'rt'),
  ],
}
