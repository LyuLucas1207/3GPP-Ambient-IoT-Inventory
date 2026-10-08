const MACROS: Array<[RegExp, string]> = [
  [/\\mathrm\{([^}]*)\}/g, '$1'],
  [/\\(max|min|clip)\b/g, '$1'],
  [/\\alpha/g, 'α'],
  [/\\cdot/g, '·'],
  [/\\times/g, '×'],
  [/\\approx/g, '≈'],
  [/\\le\b/g, '≤'],
  [/\\lceil/g, '⌈'],
  [/\\rceil/g, '⌉'],
  [/\\big/g, ''],
  [/\\[,;]/g, ' '],
  [/\\ /g, ' '],
]

function expandMacros(tex: string): string {
  return MACROS.reduce((s, [re, to]) => s.replace(re, to), tex)
}

/** `$...$` TeX islands as plain text, for places that cannot render KaTeX (title attributes, aria labels). */
export function texToPlain(text: string): string {
  return text.replace(/\$([^$]+)\$/g, (_, tex: string) => expandMacros(tex).replace(/_\{([^}]*)\}/g, '_$1'))
}

/** `$...$` TeX islands as Plotly rich text (subscripts via <sub>). */
export function texToPlotly(text: string): string {
  return text.replace(/\$([^$]+)\$/g, (_, tex: string) =>
    expandMacros(tex)
      .replace(/_\{([^}]*)\}/g, '<sub>$1</sub>')
      .replace(/_(\w)/g, '<sub>$1</sub>'),
  )
}
