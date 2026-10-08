import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { APERIODIC_PAGING_PATH, PERIODIC_PAGING_PATH } from '@/components/PaperNav'
import { GLOSSARY_PATH } from '@/explain/glossary'
import AperiodicPagingPage from '@/pages/AperiodicPagingPage'
import GlossaryPage from '@/pages/GlossaryPage'
import PeriodicPagingPage from '@/pages/PeriodicPagingPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to={PERIODIC_PAGING_PATH} replace />} />
        <Route path={PERIODIC_PAGING_PATH} element={<PeriodicPagingPage />} />
        <Route path={APERIODIC_PAGING_PATH} element={<AperiodicPagingPage />} />
        <Route path={GLOSSARY_PATH} element={<GlossaryPage />} />
      </Routes>
    </BrowserRouter>
  )
}
