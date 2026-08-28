import { ClickHelp } from '@/components/ClickHelp'
import { cn } from '@/lib/utils'

export interface LegendItem {
  id: string
  label: string
  swatch?: string
  symbol?: string
  dashed?: boolean
  helpTitle?: string
  helpBody?: string
}

interface Props {
  title: string
  items: LegendItem[]
}

function Mark({ item }: { item: LegendItem }) {
  if (item.symbol === 'line-ns') {
    return <span className="inline-block h-3 w-0.5 bg-current" style={{ color: item.swatch }} />
  }
  if (item.symbol === 'triangle-up') {
    return (
      <span
        className="inline-block size-0 border-x-[5px] border-b-[8px] border-x-transparent"
        style={{ borderBottomColor: item.swatch }}
      />
    )
  }
  if (item.symbol === 'triangle-down') {
    return (
      <span
        className="inline-block size-0 border-x-[5px] border-t-[8px] border-x-transparent"
        style={{ borderTopColor: item.swatch }}
      />
    )
  }
  if (item.symbol === 'square') {
    return <span className="inline-block size-2.5" style={{ background: item.swatch }} />
  }
  if (item.symbol === 'diamond') {
    return (
      <span
        className="inline-block size-2.5 rotate-45"
        style={{ background: item.swatch }}
      />
    )
  }
  if (item.symbol === 'x') {
    return (
      <span className="text-xs font-bold leading-none" style={{ color: item.swatch }}>
        ×
      </span>
    )
  }
  return (
    <span
      className={cn('inline-block h-0.5 w-4', item.dashed && 'border-t border-dashed bg-transparent')}
      style={
        item.dashed
          ? { borderColor: item.swatch }
          : { background: item.swatch ?? 'currentColor' }
      }
    />
  )
}

function ItemLabel({ item }: { item: LegendItem }) {
  const inner = (
    <>
      <Mark item={item} />
      <span>{item.label}</span>
    </>
  )
  if (!item.helpBody) {
    return <span className="inline-flex items-center gap-1.5 text-xs">{inner}</span>
  }
  return (
    <ClickHelp title={item.helpTitle ?? item.label} body={item.helpBody} className="text-xs">
      {inner}
    </ClickHelp>
  )
}

export function ChartLegend({ title, items }: Props) {
  if (!items.length) return null
  return (
    <div className="rounded-md border bg-muted/30 p-2">
      <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{title}</p>
      <ul className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <ItemLabel item={item} />
          </li>
        ))}
      </ul>
    </div>
  )
}
