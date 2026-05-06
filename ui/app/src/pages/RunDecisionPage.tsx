import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import AppShell from '@/components/AppShell'
import { postDecision } from '@/lib/api'

export default function RunDecisionPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [candidate_id, setCandidateId] = useState(() => {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return `CAND-${crypto.randomUUID().slice(0, 8)}`
    }
    return `CAND-${String(Date.now()).slice(-8)}`
  })
  const [name, setName] = useState('Rahul Sharma')
  const [years_of_experience, setYears] = useState(5)
  const [skill_match_score, setSkill] = useState(0.87)
  const [interview_score, setInterview] = useState(7.8)
  const [assessment_score, setAssessment] = useState(82)
  const [career_gap_months, setGap] = useState(0)
  const [gender, setGender] = useState('M')
  const [institution_tier, setTier] = useState(2)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const payload = {
        candidate_id,
        name,
        years_of_experience,
        skill_match_score,
        interview_score,
        assessment_score,
        career_gap_months: career_gap_months,
        gender: gender.trim() || null,
        institution_tier: institution_tier,
      }

      await postDecision(payload)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline failed')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    border: '1px solid #E4E2DC',
    backgroundColor: '#FFFFFF',
    color: '#0D0D0D',
    borderRadius: '6px',
    height: '38px',
    padding: '0 12px',
    width: '100%',
    outline: 'none' as const,
  }

  const labelCls = 'font-sans text-xs block mb-1'
  const labelStyle = { color: '#6B6B6B' }

  return (
    <AppShell>
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1 font-sans text-sm mb-4"
          style={{ color: '#0D6EFD', textDecoration: 'none' }}
        >
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
        <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
          Run governance pipeline
        </h1>
        <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
          Submits one candidate to{' '}
          <span className="font-mono text-xs">POST /decision</span> — worker agent, policy engine,
          risk router, supervisor (YELLOW), ServiceNow (RED), and signed artifact.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E4E2DC',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '720px',
        }}
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className={labelCls} style={labelStyle}>
              Candidate ID
            </label>
            <input
              value={candidate_id}
              onChange={(e) => setCandidateId(e.target.value)}
              required
              style={inputStyle}
            />
          </div>
          <div className="col-span-2">
            <label className={labelCls} style={labelStyle}>
              Name
            </label>
            <input value={name} onChange={(e) => setName(e.target.value)} required style={inputStyle} />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Years of experience
            </label>
            <input
              type="number"
              min={0}
              step={0.5}
              value={years_of_experience}
              onChange={(e) => setYears(Number(e.target.value))}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Skill match (0–1)
            </label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={skill_match_score}
              onChange={(e) => setSkill(Number(e.target.value))}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Interview score
            </label>
            <input
              type="number"
              min={0}
              step={0.1}
              value={interview_score}
              onChange={(e) => setInterview(Number(e.target.value))}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Assessment score
            </label>
            <input
              type="number"
              min={0}
              step={1}
              value={assessment_score}
              onChange={(e) => setAssessment(Number(e.target.value))}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Career gap (months)
            </label>
            <input
              type="number"
              min={0}
              value={career_gap_months}
              onChange={(e) => setGap(Number(e.target.value))}
              style={inputStyle}
            />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Gender
            </label>
            <input value={gender} onChange={(e) => setGender(e.target.value)} style={inputStyle} />
          </div>
          <div>
            <label className={labelCls} style={labelStyle}>
              Institution tier (1–5)
            </label>
            <input
              type="number"
              min={1}
              max={5}
              value={institution_tier}
              onChange={(e) => setTier(Number(e.target.value))}
              style={inputStyle}
            />
          </div>
        </div>

        <p className="font-sans text-xs mt-4" style={{ color: '#9B9B9B' }}>
          The worker agent may inject prohibited features in about 30% of runs (simulated biased model). Run again
          if you need a RED / policy-block demo.
        </p>

        {error && (
          <p className="font-sans text-sm mt-4" style={{ color: '#B91C1C' }}>
            {error}
          </p>
        )}

        <div className="flex gap-3 mt-6">
          <button
            type="submit"
            disabled={loading}
            className="font-sans text-sm font-medium px-5 py-2.5 rounded-lg"
            style={{
              backgroundColor: loading ? '#9CA3AF' : '#0D6EFD',
              color: '#FFFFFF',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Running pipeline…' : 'Run AgentGuard pipeline'}
          </button>
        </div>
      </form>
    </AppShell>
  )
}
