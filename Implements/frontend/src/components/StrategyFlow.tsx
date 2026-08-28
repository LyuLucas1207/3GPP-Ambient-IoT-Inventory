import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import { MathText } from '@/components/MathText'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverClose,
  PopoverDescription,
  PopoverPopup,
  PopoverPortal,
  PopoverPositioner,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { NODE_WIDTH, NodeKind, type StrategyMapDef, type StrategyNodeData } from '@/strategyMaps/types'
import { XIcon } from 'lucide-react'
import { memo, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import '@xyflow/react/dist/style.css'

const KIND_CLASS: Record<NodeKind, string> = {
  [NodeKind.Energy]: 'border-sky-600 bg-sky-50 text-sky-950 dark:bg-sky-950/80 dark:text-sky-50',
  [NodeKind.Protocol]: 'border-amber-600 bg-amber-50 text-amber-950 dark:bg-amber-950/70 dark:text-amber-50',
  [NodeKind.Decision]: 'border-violet-600 bg-violet-50 text-violet-950 dark:bg-violet-950/70 dark:text-violet-50',
  [NodeKind.Failure]: 'border-red-600 bg-red-50 text-red-950 dark:bg-red-950/70 dark:text-red-50',
  [NodeKind.Success]: 'border-emerald-600 bg-emerald-50 text-emerald-950 dark:bg-emerald-950/70 dark:text-emerald-50',
}

const KIND_SHAPE: Record<NodeKind, string> = {
  [NodeKind.Energy]: 'rounded-md',
  [NodeKind.Protocol]: 'rounded-sm',
  [NodeKind.Decision]: 'rounded-full',
  [NodeKind.Failure]: 'rounded-none',
  [NodeKind.Success]: 'rounded-md',
}

const handleCls = '!size-2.5 !border-0 !bg-transparent !opacity-0 pointer-events-none'

const FIT = { padding: 0.1, minZoom: 0.28, maxZoom: 1.2 } as const

function StrategyNode({ data, selected, dragging }: NodeProps<Node<StrategyNodeData>>) {
  const { t } = useTranslation()
  const Icon = data.icon
  const [open, setOpen] = useState(false)
  if (dragging && open) setOpen(false)
  const helpKey =
    data.helpPrefix && data.nodeId ? `maps.nodeHelp.${data.helpPrefix}.${data.nodeId}` : null
  const helpTitle = helpKey ? t(`${helpKey}.title`, { defaultValue: data.label }) : data.label
  const helpBody = helpKey ? t(`${helpKey}.body`) : ''
  const popoverOpen = open && !dragging

  return (
    <div className="relative w-full">
      <Handle type="target" position={Position.Top} id="tt" className={handleCls} />
      <Handle type="source" position={Position.Top} id="ts" className={handleCls} />
      <Handle type="target" position={Position.Left} id="lt" className={handleCls} style={{ top: '38%' }} />
      <Handle type="source" position={Position.Left} id="ls" className={handleCls} style={{ top: '62%' }} />
      <Handle type="source" position={Position.Right} id="rs" className={handleCls} style={{ top: '38%' }} />
      <Handle type="target" position={Position.Right} id="rt" className={handleCls} style={{ top: '62%' }} />
      <Handle type="source" position={Position.Bottom} id="bs" className={handleCls} />
      <Handle type="target" position={Position.Bottom} id="bt" className={handleCls} />
      <Handle type="source" position={Position.Bottom} id="bs2" className={handleCls} style={{ left: '78%' }} />
      <Popover open={popoverOpen} onOpenChange={setOpen}>
        <PopoverTrigger
          nativeButton={false}
          render={
            <div
              key={String(data.dropGen ?? 0)}
              role="button"
              tabIndex={0}
              aria-haspopup="dialog"
              aria-expanded={popoverOpen}
              aria-label={`${t(data.label, { defaultValue: data.label })}. ${t('maps.clickNode')}`}
              className={cn(
                'strategy-drop-inner flex w-full cursor-grab items-start gap-2.5 border-2 px-4 py-3.5 text-left text-base leading-snug shadow-sm outline-none active:cursor-grabbing focus-visible:ring-3 focus-visible:ring-ring/50',
                KIND_CLASS[data.kind],
                KIND_SHAPE[data.kind],
                selected && 'ring-3 ring-ring/50',
              )}
              style={{ ['--drop-delay' as string]: `${data.dropDelayMs ?? 0}ms` }}
            />
          }
        >
          <Icon className="mt-0.5 size-5 shrink-0" aria-hidden strokeWidth={2} />
          <span>
            <MathText text={t(data.label, { defaultValue: data.label })} />
          </span>
        </PopoverTrigger>
        <PopoverPortal>
          <PopoverPositioner side="right" align="start">
            <PopoverPopup>
              <div className="flex items-start justify-between gap-2">
                <PopoverTitle>
                  <MathText text={helpTitle} />
                </PopoverTitle>
                <PopoverClose
                  className="rounded-md p-1 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                  aria-label={t('explain.close')}
                >
                  <XIcon className="size-3.5" />
                </PopoverClose>
              </div>
              <PopoverDescription className="mt-2">
                <MathText text={helpBody || t('maps.clickNode')} />
              </PopoverDescription>
            </PopoverPopup>
          </PopoverPositioner>
        </PopoverPortal>
      </Popover>
    </div>
  )
}

const nodeTypes = { strategy: memo(StrategyNode) }

function cloneNodes(def: StrategyMapDef, dropGen: number): Node<StrategyNodeData>[] {
  return def.nodes.map((node) => ({
    ...node,
    position: { ...node.position },
    style: { width: NODE_WIDTH, ...node.style },
    data: {
      ...node.data,
      helpPrefix: def.helpPrefix,
      nodeId: node.id,
      dropDelayMs: Math.round(node.position.y / 2.1 + node.position.x / 20),
      dropGen,
    },
  }))
}

function FlowInner({ def }: { def: StrategyMapDef }) {
  const { fitView } = useReactFlow()
  const { t } = useTranslation()
  const [dropGen, setDropGen] = useState(0)
  const origin = useMemo(() => cloneNodes(def, dropGen), [def, dropGen])
  const [nodes, setNodes, onNodesChange] = useNodesState(origin)
  const reduceMotion =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const originEdges = useMemo(() => {
    const labeled = def.edges.map((edge) => ({
      ...edge,
      label: edge.label ? t(String(edge.label), { defaultValue: String(edge.label) }) : edge.label,
    }))
    return reduceMotion ? labeled.map((edge) => ({ ...edge, animated: false })) : labeled
  }, [def.edges, reduceMotion, t])
  const [edges, setEdges, onEdgesChange] = useEdgesState(originEdges)

  const centerMap = (duration = 0) => {
    void fitView({ ...FIT, duration })
  }

  useEffect(() => {
    setNodes(cloneNodes(def, dropGen))
    setEdges(originEdges)
  }, [def, dropGen, originEdges, setNodes, setEdges])

  useEffect(() => {
    let inner = 0
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => centerMap(0))
    })
    return () => {
      cancelAnimationFrame(outer)
      cancelAnimationFrame(inner)
    }
  }, [def, dropGen, fitView])

  const resetLayout = () => {
    setDropGen((n) => n + 1)
    setNodes(cloneNodes(def, dropGen + 1))
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 gap-2 p-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => centerMap(reduceMotion ? 0 : 280)}
        >
          {t('maps.fit')}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={resetLayout}>
          {t('maps.reset')}
        </Button>
        <p className="self-center text-xs text-muted-foreground">{t('maps.clickNode')}</p>
      </div>
      <div className="min-h-0 flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          nodesDraggable
          nodesConnectable={false}
          edgesReconnectable={false}
          elementsSelectable
          fitView
          fitViewOptions={FIT}
          onInit={(instance) => {
            requestAnimationFrame(() => instance.fitView({ ...FIT, duration: 0 }))
          }}
          panOnScroll
          zoomOnScroll
          panOnDrag={[1, 2]}
          selectionOnDrag={false}
          minZoom={0.28}
          maxZoom={1.45}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
            animated: false,
            markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color: 'var(--foreground)' },
            style: { strokeWidth: 2.25, stroke: 'var(--foreground)' },
          }}
          style={{ width: '100%', height: '100%' }}
        >
          <Background gap={20} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  )
}

export function StrategyFlow({ def }: { def: StrategyMapDef }) {
  return (
    <ReactFlowProvider>
      <FlowInner def={def} />
    </ReactFlowProvider>
  )
}
