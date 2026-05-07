import { Routes, Route, Navigate } from 'react-router'
import LandingPage from './pages/LandingPage'
import MissionControlPage from './pages/MissionControlPage'
import DecisionStreamPage from './pages/DecisionStreamPage'
import InvestigationPage from './pages/InvestigationPage'
import IncidentQueuePage from './pages/IncidentQueuePage'
import PoliciesPage from './pages/PoliciesPage'
import AgentsPage from './pages/AgentsPage'
import ArtifactsPage from './pages/ArtifactsPage'
import RunDecisionPage from './pages/RunDecisionPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      {/* Primary governance IA */}
      <Route path="/mission-control" element={<MissionControlPage />} />
      <Route path="/dashboard" element={<Navigate to="/mission-control" replace />} />
      <Route path="/decisions" element={<DecisionStreamPage />} />
      <Route path="/investigate/:decisionId" element={<InvestigationPage />} />
      <Route path="/incidents" element={<IncidentQueuePage />} />
      <Route path="/policies" element={<PoliciesPage />} />
      <Route path="/artifacts" element={<ArtifactsPage />} />
      <Route path="/agents" element={<AgentsPage />} />
      <Route path="/scenario-lab" element={<RunDecisionPage />} />
      <Route path="/run" element={<Navigate to="/scenario-lab" replace />} />

      {/* Legacy HR routes redirect into governance surfaces */}
      <Route path="/review" element={<Navigate to="/incidents" replace />} />
      <Route path="/tech-review" element={<Navigate to="/incidents" replace />} />
      <Route path="/shortlist" element={<Navigate to="/scenario-lab" replace />} />
    </Routes>
  )
}
