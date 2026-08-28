import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { GLOSSARY_PATH } from '@/explain/glossary'
import GlossaryPage from '@/pages/GlossaryPage'
import SimulatorPage from '@/pages/SimulatorPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SimulatorPage />} />
        <Route path={GLOSSARY_PATH} element={<GlossaryPage />} />
      </Routes>
    </BrowserRouter>
  )
}
