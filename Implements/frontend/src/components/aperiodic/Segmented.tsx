import { MathText } from '@/components/MathText'
import { ParamHint } from '@/components/ParamHint'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Option<T extends string | number> {
  value: T
  label: string
  disabled?: boolean
  /** Optional explanation shown behind a "?" inside the option. */
  hint?: string
}

interface Props<T extends string | number> {
  value: T
  options: Option<T>[]
  onChange: (v: T) => void
  disabled?: boolean
  className?: string
  ariaLabel?: string
}

export function Segmented<T extends string | number>({ value, options, onChange, disabled, className, ariaLabel }: Props<T>) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cn('flex flex-wrap gap-1', className)}>
      {options.map((o) => {
        const checked = o.value === value
        const off = disabled || o.disabled
        const variant = checked ? 'default' : 'outline'
        if (!o.hint) {
          return (
            <Button
              key={String(o.value)}
              type="button"
              role="radio"
              aria-checked={checked}
              size="sm"
              variant={variant}
              disabled={off}
              onClick={() => onChange(o.value)}
            >
              <MathText text={o.label} />
            </Button>
          )
        }
        // The "?" is itself a button (popover trigger), so the chip cannot be a <button>.
        return (
          <div
            key={String(o.value)}
            role="radio"
            aria-checked={checked}
            aria-disabled={off || undefined}
            tabIndex={off ? -1 : 0}
            className={cn(buttonVariants({ size: 'sm', variant }), 'cursor-pointer gap-1 pr-1.5', off && 'pointer-events-none opacity-50')}
            onClick={() => !off && onChange(o.value)}
            onKeyDown={(e) => {
              if (!off && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault()
                onChange(o.value)
              }
            }}
          >
            <MathText text={o.label} />
            <span className="pointer-events-auto inline-flex" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
              <ParamHint text={o.hint} title={o.label} iconClassName="text-current opacity-60 hover:opacity-100" />
            </span>
          </div>
        )
      })}
    </div>
  )
}
