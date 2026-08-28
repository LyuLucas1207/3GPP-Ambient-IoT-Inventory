import {
  ArrowDownToLineIcon,
  BatteryChargingIcon,
  BatteryLowIcon,
  CheckIcon,
  CircleHelpIcon,
  EyeIcon,
  RadioTowerIcon,
  SendIcon,
  TriangleIcon,
  XIcon,
} from 'lucide-react'
import { EdgeKind, NodeKind, e, fwd, leftLoop, n, type StrategyMapDef } from './types'

const M = 72
const S = 600
const Y = 180

/** Happy path drops top→bottom. Failures sit on a right-hand lane. */
export const emMap: StrategyMapDef = {
  summaryKey: 'maps.em.summary',
  stepsKey: 'maps.em.steps',
  helpPrefix: 'em',
  nodes: [
    n('off', M, 0, 'OFF / Harvest', NodeKind.Energy, BatteryChargingIcon),
    n('on', M, Y, 'ON / Monitor paging', NodeKind.Energy, EyeIcon),
    n('p', M, Y * 2, 'Aperiodic paging', NodeKind.Protocol, RadioTowerIcon),
    n('draw', M, Y * 3, 'Access probability', NodeKind.Decision, CircleHelpIcon),
    n('ao', M, Y * 4, 'Select Msg1 AO', NodeKind.Protocol, TriangleIcon),
    n('m2', M, Y * 5, 'Msg2 RX', NodeKind.Protocol, ArrowDownToLineIcon),
    n('m3', M, Y * 6, 'Msg3 TX', NodeKind.Protocol, SendIcon),
    n('done', M, Y * 7, 'DONE', NodeKind.Success, CheckIcon),
    n('elow', S, Y, 'E ≤ E_low → OFF', NodeKind.Failure, BatteryLowIcon),
    n('col', S, Y * 4, 'Collision', NodeKind.Failure, XIcon),
  ],
  edges: [
    e('a', 'off', 'on', 'E ≥ E_up', EdgeKind.Threshold),
    e('b', 'on', 'p', 'listening'),
    e('c', 'p', 'draw', 'heard'),
    e('d', 'draw', 'ao', 'accept'),
    e('e', 'ao', 'm2', 'Msg1 singleton'),
    e('f', 'm2', 'm3', 'decoded'),
    e('g', 'm3', 'done', 'energy > E_low'),
    e('h', 'on', 'elow', 'E ≤ E_low', EdgeKind.Threshold, ...fwd, 'straight'),
    e('i', 'elow', 'off', 'recharge', EdgeKind.Threshold, 'ts', 'rt'),
    e('j', 'draw', 'on', 'reject / keep ON', EdgeKind.Retry, ...leftLoop),
    e('k', 'ao', 'col', '≥2 on AO', EdgeKind.Retry, ...fwd, 'straight'),
    e('l', 'col', 'p', 'next paging', EdgeKind.Retry, 'ls', 'rt'),
    e('m', 'm3', 'elow', 'energy fail', EdgeKind.Threshold, 'rs', 'bt'),
  ],
}
