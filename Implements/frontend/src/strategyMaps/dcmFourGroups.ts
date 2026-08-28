import {
  BatteryLowIcon,
  CheckIcon,
  EyeIcon,
  Grid2x2Icon,
  MoonIcon,
  PercentIcon,
  RadioTowerIcon,
  TriangleIcon,
  XIcon,
} from 'lucide-react'
import { EdgeKind, NodeKind, back, e, fwd, n, rightLoop, up, type StrategyMapDef } from './types'

const M = 72
const S = 600
const Y = 180

export const dcmFourGroupsMap: StrategyMapDef = {
  summaryKey: 'maps.dcm4.summary',
  stepsKey: 'maps.dcm4.steps',
  helpPrefix: 'dcm4',
  nodes: [
    n('sync', M, 0, 'First paging / sync', NodeKind.Protocol, RadioTowerIcon),
    n('grp', M, Y, 'g = device_id mod 4', NodeKind.Decision, Grid2x2Icon),
    n('route', M, Y * 2, 'Wake iff paging ≡ g (mod 4)', NodeKind.Decision, PercentIcon),
    n('on', M, Y * 3, 'DCM ON · 3 ms · ~150', NodeKind.Energy, EyeIcon),
    n('cbra', M, Y * 4, 'CBRA', NodeKind.Protocol, TriangleIcon),
    n('done', M, Y * 5, 'DONE', NodeKind.Success, CheckIcon),
    n('sleep', S, Y * 3, 'SLEEP · 45 ms', NodeKind.Energy, MoonIcon),
    n('col', S, Y * 4, 'Collision / retry', NodeKind.Failure, XIcon),
    n('fail', S, Y * 5, 'Energy failure', NodeKind.Failure, BatteryLowIcon),
  ],
  edges: [
    e('a', 'sync', 'grp', 'even split assumption'),
    e('b', 'grp', 'route', 'g ∈ {0,1,2,3}'),
    e('c', 'route', 'on', 'this group'),
    e('d', 'on', 'cbra', 'eligible'),
    e('e', 'cbra', 'done', 'Msg3 ok'),
    e('f', 'on', 'sleep', 'T_on over', EdgeKind.Sleep, ...fwd, 'straight'),
    e('g', 'sleep', 'on', '48 ms period', EdgeKind.Sleep, ...back, 'straight'),
    e('h', 'cbra', 'col', 'AO collision', EdgeKind.Retry, ...fwd, 'straight'),
    e('i', 'col', 'sleep', 'next group occasion', EdgeKind.Retry, ...up),
    e('j', 'cbra', 'fail', 'E_low on Msg1–3', EdgeKind.Threshold, 'bs2', 'lt'),
    e('k', 'fail', 'sleep', 'rejoin after recharge', EdgeKind.Threshold, ...rightLoop),
  ],
}
