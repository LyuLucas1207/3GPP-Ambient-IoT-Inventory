import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, ChevronUpIcon } from 'lucide-react'
import { useId, type CSSProperties, type PointerEvent, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { HudDock } from '@/types/hud'
import { useTranslation } from 'react-i18next'

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n))
}

interface Props {
  dock: HudDock
  open: boolean
  onOpenChange: (open: boolean) => void
  label: string
  size: number
  onSizeChange: (size: number) => void
  minSize: number
  maxSize: number
  defaultSize: number
  inset: CSSProperties
  children: ReactNode
}

export function HudPanel({
  dock,
  open,
  onOpenChange,
  label,
  size,
  onSizeChange,
  minSize,
  maxSize,
  defaultSize,
  inset,
  children,
}: Props) {
  const { t } = useTranslation()
  const panelId = useId()
  const closed = !open
  const resizeLabel =
    dock === HudDock.Left
      ? t('hud.resizeSetup')
      : dock === HudDock.Right
        ? t('hud.resizeInspect')
        : t('hud.resizePlots')

  const startResize = (ev: PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0) return
    ev.preventDefault()
    ev.stopPropagation()
    const origin = dock === HudDock.Bottom ? ev.clientY : ev.clientX
    const originSize = size
    const axisClass = dock === HudDock.Bottom ? 'hud-resizing-y' : 'hud-resizing-x'
    document.documentElement.classList.add('hud-resizing', axisClass)

    const move = (e: globalThis.PointerEvent) => {
      let next = originSize
      if (dock === HudDock.Bottom) next = originSize + (origin - e.clientY)
      else if (dock === HudDock.Left) next = originSize + (e.clientX - origin)
      else next = originSize + (origin - e.clientX)
      onSizeChange(clamp(next, minSize, maxSize))
    }
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      document.documentElement.classList.remove('hud-resizing', 'hud-resizing-x', 'hud-resizing-y')
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }

  const resetSize = () => onSizeChange(defaultSize)

  const transform = closed
    ? dock === HudDock.Left
      ? 'translateX(calc(-100% - 0.75rem))'
      : dock === HudDock.Right
        ? 'translateX(calc(100% + 0.75rem))'
        : 'translateY(calc(100% + 0.75rem))'
    : 'none'

  const Chevron =
    dock === HudDock.Bottom
      ? open
        ? ChevronDownIcon
        : ChevronUpIcon
      : dock === HudDock.Left
        ? open
          ? ChevronLeftIcon
          : ChevronRightIcon
        : open
          ? ChevronRightIcon
          : ChevronLeftIcon

  return (
    <div
      className="hud-dock-motion pointer-events-none absolute z-20"
      style={{
        ...inset,
        width: dock === HudDock.Bottom ? undefined : size,
        height: dock === HudDock.Bottom ? size : undefined,
        transform,
        transition: 'none',
      }}
    >
      <div
        id={panelId}
        className="pointer-events-auto relative h-full min-h-0 overflow-hidden rounded-xl border border-border bg-card/90 shadow-lg backdrop-blur-md"
      >
        <div
          role="separator"
          aria-orientation={dock === HudDock.Bottom ? 'horizontal' : 'vertical'}
          aria-label={resizeLabel}
          onPointerDown={startResize}
          onDoubleClick={resetSize}
          className={cn(
            'absolute z-10 touch-none',
            dock === HudDock.Bottom &&
              'inset-x-0 top-0 flex h-2 cursor-ns-resize items-start justify-center hover:bg-foreground/10',
            dock === HudDock.Left &&
              'inset-y-0 right-0 flex w-1.5 cursor-ew-resize items-center justify-end hover:bg-foreground/10',
            dock === HudDock.Right &&
              'inset-y-0 left-0 flex w-1.5 cursor-ew-resize items-center justify-start hover:bg-foreground/10',
          )}
        >
          <i
            className={cn(
              'rounded-full bg-foreground/35',
              dock === HudDock.Bottom ? 'mt-0.5 h-1 w-10' : 'h-10 w-1',
            )}
          />
        </div>
        <div className="h-full min-h-0">{children}</div>
      </div>

      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onOpenChange(!open)}
        className={cn(
          'pointer-events-auto absolute z-20 flex items-center gap-1 border border-border bg-card/90 px-1.5 py-2 text-[10px] tracking-[0.14em] uppercase shadow-md backdrop-blur-md hover:font-bold',
          dock === HudDock.Bottom &&
            'top-0 left-1/2 -translate-x-1/2 -translate-y-full rounded-t-md rounded-b-none',
          dock === HudDock.Left &&
            'top-1/2 right-0 translate-x-full -translate-y-1/2 flex-col rounded-l-none rounded-r-md py-3',
          dock === HudDock.Right &&
            'top-1/2 left-0 -translate-x-full -translate-y-1/2 flex-col rounded-l-md rounded-r-none py-3',
        )}
      >
        <Chevron className="size-3.5 shrink-0" />
        <span className={cn(dock !== HudDock.Bottom && '[writing-mode:vertical-lr]')}>{label}</span>
      </button>
    </div>
  )
}

interface SplitProps {
  ratio: number
  onRatioChange: (ratio: number) => void
}

export function HudSplit({ ratio, onRatioChange }: SplitProps) {
  const { t } = useTranslation()
  const startResize = (ev: PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0) return
    ev.preventDefault()
    const parent = ev.currentTarget.parentElement
    if (!parent) return
    document.documentElement.classList.add('hud-resizing', 'hud-resizing-x')
    const move = (e: globalThis.PointerEvent) => {
      const box = parent.getBoundingClientRect()
      onRatioChange(clamp((e.clientX - box.left) / box.width, 0.28, 0.72))
    }
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      document.documentElement.classList.remove('hud-resizing', 'hud-resizing-x', 'hud-resizing-y')
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t('hud.resizePlots')}
      aria-valuenow={Math.round(ratio * 100)}
      onPointerDown={startResize}
      onDoubleClick={() => onRatioChange(0.38)}
      className="w-1.5 shrink-0 cursor-col-resize self-stretch rounded-full hover:bg-foreground/20"
    />
  )
}
