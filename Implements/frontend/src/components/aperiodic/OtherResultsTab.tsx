import { ParamHint } from '@/components/ParamHint'
import { PaperCaption } from '@/components/aperiodic/PaperRef'
import {
  CheckpointNotes,
  Figure4View,
  Figure8View,
  GenericObject,
  ReproRunControls,
  RowsTable,
  jobResult,
  type Reproduce,
} from '@/components/aperiodic/ReproViews'
import { Segmented } from '@/components/aperiodic/Segmented'
import type { JobStatus, ReproResult, ReproTarget } from '@/types/aperiodicSimulation'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

type OtherId = 'fig4' | 'fig8' | 'tab4' | 'tab5' | 'tab6'

const ITEMS: Array<{ id: OtherId; target: ReproTarget }> = [
  { id: 'fig4', target: 'figure4' },
  { id: 'fig8', target: 'figure8' },
  { id: 'tab4', target: 'figure5' },
  { id: 'tab5', target: 'tables' },
  { id: 'tab6', target: 'tables' },
]

function Body({ id, result }: { id: OtherId; result: ReproResult }) {
  if (id === 'fig4') return <Figure4View result={result} />
  if (id === 'fig8' && result.series) return <Figure8View result={result} />
  const key = id === 'tab4' ? 'table_iv' : id === 'tab5' ? 'table_v' : 'table_vi'
  if (Array.isArray(result[key])) return <RowsTable rows={result[key] as Array<Record<string, unknown>>} />
  return <GenericObject value={result} />
}

/** Paper results that are not inventory-vs-time curves of one run: Fig. 4, Fig. 8, Tables IV–VI. */
export function OtherResultsTab({ job, reproduce, baseSeed }: { job: JobStatus | null; reproduce: Reproduce; baseSeed: number }) {
  const { t } = useTranslation()
  const [id, setId] = useState<OtherId>('fig4')
  const item = ITEMS.find((i) => i.id === id)!
  const res = jobResult(job, item.target)
  return (
    <div className="grid gap-3 pr-2">
      <p className="text-[11px] text-muted-foreground">{t('ap.otherTab.lead')}</p>
      <div className="flex flex-wrap items-center gap-2">
        <Segmented
          value={id}
          onChange={setId}
          options={ITEMS.map((i) => ({ value: i.id, label: t(`ap.paperRef.${i.id}.label`), hint: t(`ap.help.fig.${i.id}`) }))}
        />
      </div>
      <PaperCaption id={id} />
      <ReproRunControls key={item.target} job={job} target={item.target} reproduce={reproduce} baseSeed={baseSeed} />
      {res && <CheckpointNotes result={res} />}
      {res && <Body id={id} result={res} />}
      {!res && (
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          {t('ap.otherTab.empty')} <ParamHint text={t(`ap.help.fig.${id}`)} title={t(`ap.paperRef.${id}.label`)} />
        </p>
      )}
    </div>
  )
}
