import { ChartLegend } from '@/components/ChartLegend'
import { scientificStateLegendItems } from '@/explain/chartVisuals'
import { useTranslation } from 'react-i18next'

export function ScientificStateKey() {
  const { t } = useTranslation()
  return <ChartLegend title={t('energy.stateKey')} items={scientificStateLegendItems(t)} />
}
