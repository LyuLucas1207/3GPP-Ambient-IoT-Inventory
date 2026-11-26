import { Menu } from '@base-ui/react/menu'
import { CheckIcon, ChevronDownIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

export type DropdownOption<T extends string> = {
  value: T
  /** Row inside the open menu. */
  label: ReactNode
  /** Closed-state text. Falls back to `label`. */
  trigger?: ReactNode
  /** Question marker shown on the open row. Clicks do not select the row. */
  hint?: ReactNode
}

/** Button that opens a menu under itself. The list starts at the top of the menu. */
export function Dropdown<T extends string>({
  value,
  options,
  onChange,
  disabled,
  placeholder,
  align = 'start',
  className,
  menuClassName,
  size = 'default',
  id,
  'aria-label': ariaLabel,
}: {
  value: T | ''
  options: DropdownOption<T>[]
  onChange: (value: T) => void
  disabled?: boolean
  placeholder?: ReactNode
  align?: 'start' | 'center' | 'end'
  className?: string
  menuClassName?: string
  size?: 'sm' | 'default'
  id?: string
  'aria-label'?: string
}) {
  const current = options.find((option) => option.value === value)
  const shown = current ? (current.trigger ?? current.label) : placeholder
  return (
    <Menu.Root modal={false}>
      <Menu.Trigger
        type="button"
        id={id}
        disabled={disabled}
        aria-label={ariaLabel}
        data-size={size}
        className={cn(
          'flex w-full min-w-0 items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-2.5 text-left text-sm whitespace-nowrap outline-none select-none hover:bg-muted/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:h-8 data-[size=sm]:h-7 data-[size=sm]:rounded-[min(var(--radius-md),10px)] data-[size=sm]:text-xs dark:bg-input/30 dark:hover:bg-input/50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
          !current && 'text-muted-foreground',
          className,
        )}
      >
        <span className="min-w-0 flex-1 truncate">{shown}</span>
        <ChevronDownIcon className="size-4 text-muted-foreground" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner className="isolate z-[80]" side="bottom" sideOffset={4} align={align} collisionPadding={12}>
          <Menu.Popup
            className={cn(
              'max-h-72 min-w-(--anchor-width) origin-(--transform-origin) overflow-y-auto rounded-lg bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-none',
              menuClassName,
            )}
          >
            <Menu.RadioGroup value={value} onValueChange={(next) => onChange(next as T)}>
              {options.map((option) => (
                <Menu.RadioItem
                  key={option.value}
                  value={option.value}
                  closeOnClick
                  label={typeof option.trigger === 'string' ? option.trigger : typeof option.label === 'string' ? option.label : option.value}
                  className="relative flex w-full cursor-default items-center gap-1.5 rounded-md py-1.5 pr-8 pl-2 text-sm outline-hidden data-highlighted:bg-accent data-highlighted:text-accent-foreground"
                >
                  <span className="min-w-0 flex-1">{option.label}</span>
                  {option.hint ? (
                    <span
                      className="shrink-0"
                      onPointerDown={(event) => event.stopPropagation()}
                      onPointerUp={(event) => event.stopPropagation()}
                      onClick={(event) => event.stopPropagation()}
                    >
                      {option.hint}
                    </span>
                  ) : null}
                  <Menu.RadioItemIndicator className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
                    <CheckIcon className="size-4" />
                  </Menu.RadioItemIndicator>
                </Menu.RadioItem>
              ))}
            </Menu.RadioGroup>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  )
}
