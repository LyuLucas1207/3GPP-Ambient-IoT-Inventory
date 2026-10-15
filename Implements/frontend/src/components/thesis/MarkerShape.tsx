import type { Shape } from '@/types/thesis'

export function MarkerShape({
  shape,
  r,
  className,
  strokeWidth = 1.5,
}: {
  shape: Shape
  r: number
  className?: string
  strokeWidth?: number
}) {
  if (shape === 'circle') {
    return <circle r={r} className={className} strokeWidth={strokeWidth} vectorEffect="non-scaling-stroke" />
  }
  if (shape === 'square') {
    return (
      <rect
        x={-r}
        y={-r}
        width={r * 2}
        height={r * 2}
        className={className}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />
    )
  }
  return (
    <polygon
      points={polygon(shape === 'triangle' ? 3 : shape === 'diamond' ? 4 : 6, r)}
      className={className}
      strokeWidth={strokeWidth}
      vectorEffect="non-scaling-stroke"
    />
  )
}

export function ShapeGlyph({ shape, className }: { shape: Shape; className?: string }) {
  return (
    <svg viewBox="-12 -12 24 24" className={className} aria-hidden>
      <g transform="scale(1,-1)">
        <MarkerShape shape={shape} r={8} className="fill-current stroke-background" />
      </g>
    </svg>
  )
}

function polygon(sides: number, radius: number) {
  return Array.from({ length: sides }, (_, index) => {
    const angle = Math.PI / 2 + (index * 2 * Math.PI) / sides
    return `${(Math.cos(angle) * radius).toFixed(3)},${(Math.sin(angle) * radius).toFixed(3)}`
  }).join(' ')
}
