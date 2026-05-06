import { Routes, Route } from 'react-router'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import ReviewQueuePage from './pages/ReviewQueuePage'
import TechReviewPage from './pages/TechReviewPage'
import ShortlistPage from './pages/ShortlistPage'
import RunDecisionPage from './pages/RunDecisionPage'
import BulkRankPage from './pages/BulkRankPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/run" element={<RunDecisionPage />} />
      <Route path="/bulk-rank" element={<BulkRankPage />} />
      <Route path="/review" element={<ReviewQueuePage />} />
      <Route path="/tech-review" element={<TechReviewPage />} />
      <Route path="/shortlist" element={<ShortlistPage />} />
    </Routes>
  )
}
