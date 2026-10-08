import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Option<T extends string | number> {
  value: T
  label: string
  disabled?: boolean
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
      {options.map((o) => (
        <Button
          key={String(o.value)}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          size="sm"
          variant={o.value === value ? 'default' : 'outline'}
          disabled={disabled || o.disabled}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </Button>
      ))}
    </div>
  )
}
