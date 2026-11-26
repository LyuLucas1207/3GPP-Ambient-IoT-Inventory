import { ChartLegend } from '@/components/ChartLegend'
import { protocolEventLegendItems } from '@/features/periodic/chartVisuals'
import { useTranslation } from 'react-i18next'

export function ProtocolEventKey({ present }: { present: Set<string> }) {
  const { t } = useTranslation()
  return <ChartLegend title={t('energy.eventKey')} items={protocolEventLegendItems(t, present)} />
}
