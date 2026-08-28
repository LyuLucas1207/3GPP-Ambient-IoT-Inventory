import { MarkerType, type BuiltInEdge, type Node } from '@xyflow/react'
import type { LucideIcon } from 'lucide-react'

export enum NodeKind {
  Energy = 'energy',
  Protocol = 'protocol',
  Decision = 'decision',
  Failure = 'failure',
  Success = 'success',
}

export enum EdgeKind {
  Normal = 'normal',
  Threshold = 'threshold',
  Retry = 'retry',
  Sleep = 'sleep',
}

export type StrategyHelpPrefix = 'em' | 'dcm1' | 'dcm4' | 'overview'

export interface StrategyNodeData extends Record<string, unknown> {
  label: string
  kind: NodeKind
  icon: LucideIcon
  dropDelayMs?: number
  dropGen?: number
  helpPrefix?: StrategyHelpPrefix
  nodeId?: string
}

export interface StrategyMapDef {
  nodes: Node<StrategyNodeData>[]
  edges: BuiltInEdge[]
  summaryKey: string
  stepsKey: string
  helpPrefix: StrategyHelpPrefix
}

export const NODE_WIDTH = 320

export function n(
  id: string,
  x: number,
  y: number,
  label: string,
  kind: NodeKind,
  icon: LucideIcon,
): Node<StrategyNodeData> {
  return {
    id,
    position: { x, y },
    data: { label, kind, icon },
    type: 'strategy',
    draggable: true,
    style: { width: NODE_WIDTH },
  }
}

const EDGE_STROKE: Record<EdgeKind, string> = {
  [EdgeKind.Normal]: 'var(--foreground)',
  [EdgeKind.Threshold]: 'oklch(0.65 0.15 250)',
  [EdgeKind.Retry]: 'oklch(0.63 0.2 25)',
  [EdgeKind.Sleep]: 'oklch(0.62 0.18 300)',
}

function isAround(sourceHandle: string, targetHandle: string) {
  return (
    (sourceHandle === 'ls' && targetHandle === 'lt') ||
    (sourceHandle === 'rs' && targetHandle === 'rt')
  )
}

/** Default: top-to-bottom (bottom source → top target). */
export function e(
  id: string,
  source: string,
  target: string,
  label: string,
  kind: EdgeKind = EdgeKind.Normal,
  sourceHandle = 'bs',
  targetHandle = 'tt',
  path: 'step' | 'straight' = 'step',
): BuiltInEdge {
  const around = isAround(sourceHandle, targetHandle)
  return {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    label,
    data: { kind },
    type: path === 'straight' ? 'straight' : 'smoothstep',
    animated: kind === EdgeKind.Sleep || kind === EdgeKind.Retry,
    pathOptions: path === 'straight' ? undefined : { borderRadius: 14, offset: around ? 56 : 28 },
    style: {
      stroke: EDGE_STROKE[kind],
      strokeWidth: kind === EdgeKind.Normal ? 2.25 : 2.5,
      strokeDasharray: kind === EdgeKind.Retry ? '7 5' : undefined,
    },
    labelStyle: { fontSize: 13, fontWeight: 500, fill: 'var(--foreground)' },
    labelBgStyle: { fill: 'var(--popover)', fillOpacity: 0.94 },
    labelBgPadding: [6, 8],
    labelBgBorderRadius: 6,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: EDGE_STROKE[kind],
    },
  }
}

export const down = ['bs', 'tt'] as const
export const up = ['ts', 'bt'] as const
export const back = ['ls', 'rt'] as const
export const fwd = ['rs', 'lt'] as const
/** Skip along the main column: arc on the left, do not pierce nodes in between. */
export const leftLoop = ['ls', 'lt'] as const
/** Skip along the side column: arc on the right, do not pierce nodes in between. */
export const rightLoop = ['rs', 'rt'] as const
export const over = ['ts', 'tt'] as const
export const under = ['bs', 'bt'] as const
