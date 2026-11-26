import { BrowserRouter, Route, Routes } from 'react-router-dom'
import {
  APERIODIC_PAGING_PATH,
  GLOSSARY_PATH,
  PERIODIC_PAGING_PATH,
  THESIS_ANALYSIS_PATH,
  THESIS_RL_PATH,
  THESIS_SIMULATION_PATH,
  THESIS_TRAINING_PATH,
} from '@/navigations/paths'
import AperiodicPagingPage from '@/pages/Aperiodic'
import GlossaryPage from '@/pages/Glossary'
import HomePage from '@/pages/Home'
import PeriodicPagingPage from '@/pages/Periodic'
import ThesisAnalysisPage from '@/pages/Thesis/Analysis'
import ThesisRlPage from '@/pages/Thesis/Rl'
import ThesisSimulationPage from '@/pages/Thesis/Simulation'
import ThesisTrainingPage from '@/pages/Thesis/Training'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path={PERIODIC_PAGING_PATH} element={<PeriodicPagingPage />} />
        <Route path={APERIODIC_PAGING_PATH} element={<AperiodicPagingPage />} />
        <Route path={THESIS_SIMULATION_PATH} element={<ThesisSimulationPage />} />
        <Route path={THESIS_ANALYSIS_PATH} element={<ThesisAnalysisPage />} />
        <Route path={THESIS_TRAINING_PATH} element={<ThesisTrainingPage />} />
        <Route path={THESIS_RL_PATH} element={<ThesisRlPage />} />
        <Route path={GLOSSARY_PATH} element={<GlossaryPage />} />
      </Routes>
    </BrowserRouter>
  )
}
