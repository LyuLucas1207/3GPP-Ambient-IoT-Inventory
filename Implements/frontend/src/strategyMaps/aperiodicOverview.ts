import {
  ArrowDownToLineIcon,
  BatteryChargingIcon,
  BatteryWarningIcon,
  CheckIcon,
  CircleHelpIcon,
  DicesIcon,
  EarIcon,
  FlagIcon,
  MoonIcon,
  RadioTowerIcon,
  SendIcon,
  XIcon,
} from 'lucide-react'
import { EdgeKind, NodeKind, e, n, type StrategyMapDef } from './types'

// Device state machine of the aperiodic-paging paper (Sec. III, Fig. 2/3),
// with the periodic baseline's synchronized sleep (Fig. 1) as a side branch.
const L = -40
const W = -560
const M = 480
const R = 1000
const Y = 150

export const aperiodicOverviewMap: StrategyMapDef = {
  summaryKey: 'ap.overview.lead',
  stepsKey: 'ap.overview.steps',
  helpPrefix: 'apOverview',
  helpBase: 'ap.overview.nodeHelp',
  nodes: [
    n('charge', M, 0, 'ap.overview.node.charge', NodeKind.Energy, BatteryChargingIcon),
    n('monitor', M, Y, 'ap.overview.node.monitor', NodeKind.Energy, EarIcon),
    n('page', R, Y, 'ap.overview.node.page', NodeKind.Protocol, RadioTowerIcon),
    n('caught', M, Y * 2, 'ap.overview.node.caught', NodeKind.Decision, CircleHelpIcon),
    n('access', M, Y * 3, 'ap.overview.node.access', NodeKind.Decision, DicesIcon),
    n('msg1', M, Y * 4, 'ap.overview.node.msg1', NodeKind.Protocol, SendIcon),
    n('ei', M, Y * 5, 'ap.overview.node.ei', NodeKind.Protocol, FlagIcon),
    n('msg2', M, Y * 6, 'ap.overview.node.msg2', NodeKind.Protocol, ArrowDownToLineIcon),
    n('msg3', M, Y * 7, 'ap.overview.node.msg3', NodeKind.Protocol, SendIcon),
    n('done', M, Y * 8, 'ap.overview.node.done', NodeKind.Success, CheckIcon),
    n('fail', L, Y * 5.5, 'ap.overview.node.fail', NodeKind.Failure, XIcon),
    n('rejected', L, Y * 3, 'ap.overview.node.rejected', NodeKind.Failure, XIcon),
    n('sync', W, Y * 4.25, 'ap.overview.node.sync', NodeKind.Energy, MoonIcon),
    n('depleted', R, Y * 5.5, 'ap.overview.node.depleted', NodeKind.Failure, BatteryWarningIcon),
  ],
  edges: [
    e('charge_monitor', 'charge', 'monitor', 'ap.overview.edge.full'),
    e('monitor_off', 'monitor', 'charge', 'ap.overview.edge.noPage', EdgeKind.Retry, 'rs', 'rt'),
    e('page_caught', 'page', 'caught', 'ap.overview.edge.page', EdgeKind.Normal, 'bs', 'rt'),
    e('monitor_caught', 'monitor', 'caught', ''),
    e('caught_access', 'caught', 'access', 'ap.overview.edge.rx'),
    e('access_msg1', 'access', 'msg1', 'ap.overview.edge.transmit'),
    e('access_rej', 'access', 'rejected', 'ap.overview.edge.reject', EdgeKind.Retry, 'ls', 'rt'),
    e('msg1_ei', 'msg1', 'ei', ''),
    e('ei_msg2', 'ei', 'msg2', 'ap.overview.edge.flag'),
    e('ei_fail', 'ei', 'fail', 'ap.overview.edge.noFlag', EdgeKind.Retry, 'ls', 'rt'),
    e('msg2_msg3', 'msg2', 'msg3', 'ap.overview.edge.echo'),
    e('msg2_fail', 'msg2', 'fail', 'ap.overview.edge.captureLoss', EdgeKind.Retry, 'ls', 'rt'),
    e('msg3_done', 'msg3', 'done', 'ap.overview.edge.identified'),
    e('round_dep', 'msg2', 'depleted', 'ap.overview.edge.depleted', EdgeKind.Threshold, 'rs', 'lt'),
    e('dep_off', 'depleted', 'charge', 'ap.overview.edge.toOff', EdgeKind.Retry, 'rs', 'rt'),
    e('fail_off', 'fail', 'charge', 'ap.overview.edge.aperiodicOff', EdgeKind.Retry, 'ts', 'lt'),
    e('rej_off', 'rejected', 'charge', '', EdgeKind.Retry, 'ts', 'lt'),
    e('fail_sync', 'fail', 'sync', 'ap.overview.edge.periodicSleep', EdgeKind.Sleep, 'ls', 'rt'),
    e('rej_sync', 'rejected', 'sync', '', EdgeKind.Sleep, 'ls', 'rt'),
    e('sync_access', 'sync', 'access', 'ap.overview.edge.wake', EdgeKind.Sleep, 'ts', 'lt'),
    e('sync_off', 'sync', 'charge', 'ap.overview.edge.syncLow', EdgeKind.Retry, 'ts', 'lt'),
  ],
}
