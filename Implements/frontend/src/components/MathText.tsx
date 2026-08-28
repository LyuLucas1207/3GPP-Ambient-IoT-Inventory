import katex from 'katex'
import { useMemo, type ReactNode } from 'react'

function renderTex(tex: string, display = false) {
  return katex.renderToString(tex, {
    throwOnError: false,
    displayMode: display,
    output: 'html',
  })
}

/** Inline TeX, e.g. P_{\\mathrm{rx}}. */
export function MathInline({ tex, className }: { tex: string; className?: string }) {
  const html = useMemo(() => renderTex(tex), [tex])
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
}

/** Mixed copy with $...$ TeX islands. */
export function MathText({ text, className }: { text: string; className?: string }) {
  const nodes = useMemo(() => splitMath(text), [text])
  return <span className={className}>{nodes}</span>
}

function splitMath(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /\$([^$]+)\$/g
  let last = 0
  let i = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const html = renderTex(m[1])
    out.push(<span key={`m${i}`} dangerouslySetInnerHTML={{ __html: html }} />)
    i += 1
    last = m.index + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}
