import { Routes, Route } from 'react-router'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ReviewQueuePage from './pages/ReviewQueuePage'
import TechReviewPage from './pages/TechReviewPage'
import ShortlistPage from './pages/ShortlistPage'
import RunDecisionPage from './pages/RunDecisionPage'
import BulkRankPage from './pages/BulkRankPage'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute roles={['hr']}>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/run"
        element={
          <ProtectedRoute roles={['hr']}>
            <RunDecisionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/bulk-rank"
        element={
          <ProtectedRoute roles={['hr']}>
            <BulkRankPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/review"
        element={
          <ProtectedRoute roles={['hr']}>
            <ReviewQueuePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tech-review"
        element={
          <ProtectedRoute roles={['tech']}>
            <TechReviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/shortlist"
        element={
          <ProtectedRoute roles={['hr']}>
            <ShortlistPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
