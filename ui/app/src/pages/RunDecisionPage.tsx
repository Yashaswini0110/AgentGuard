import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import AppShell from '@/components/AppShell'
import { postDecision, postResumeParse } from '@/lib/api'

export default function RunDecisionPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)

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

  // Streamlit parity: JD-aware resume ingestion
  const PREDEFINED_JDS: Record<string, string> = {
    'Software Engineer': 'Role: Software Engineer. Requirements: Python, APIs, Data Structures, System Design.',
    'Data Scientist': 'Role: Data Scientist. Requirements: Python, ML, Pandas, Statistics.',
    'Frontend Developer': 'Role: Frontend Developer. Requirements: React, JS, UI/UX.',
  }
  const [inputMode, setInputMode] = useState<'manual' | 'resume'>('manual')
  const [jdOption, setJdOption] = useState<'Custom' | keyof typeof PREDEFINED_JDS>('Software Engineer')
  const [jdText, setJdText] = useState(PREDEFINED_JDS['Software Engineer'])
  const [resumeFile, setResumeFile] = useState<File | null>(null)

  // Optional proxy fields (Streamlit's simulate_bias / metadata)
  const [showProxyFields, setShowProxyFields] = useState(false)
  const [applicant_surname, setSurname] = useState('')
  const [home_district, setHomeDistrict] = useState('')
  const [village_code, setVillageCode] = useState('')
  const [emotion_score, setEmotionScore] = useState(0.45)

  const handleParseResume = async () => {
    setParseError(null)
    if (!resumeFile) {
      setParseError('Please select a PDF resume first.')
      return
    }
    if (!jdText.trim()) {
      setParseError('Please provide a Job Description first.')
      return
    }
    setParsing(true)
    try {
      const parsed = await postResumeParse(resumeFile, jdText.trim())

      const pick = <T,>(k: string): T | undefined => parsed[k] as T | undefined

      const newName = pick<string>('name')
      const newId = pick<string>('candidate_id')
      const yoe = pick<number>('years_of_experience')
      const sms = pick<number>('skill_match_score')
      const gap = pick<number>('career_gap_months')
      const gen = pick<string>('gender')
      const tier = pick<number>('institution_tier')
      const sur = pick<string>('applicant_surname')
      const dist = pick<string>('home_district')

      if (newName) setName(newName)
      if (newId) setCandidateId(newId)
      if (typeof yoe === 'number') setYears(yoe)
      if (typeof sms === 'number') setSkill(Math.max(0, Math.min(1, sms)))
      if (typeof gap === 'number') setGap(Math.max(0, Math.round(gap)))
      if (typeof gen === 'string') setGender(gen)
      if (typeof tier === 'number') setTier(tier)

      // If resume parser detects proxies, surface them without forcing major UI changes
      if (sur || dist || typeof tier === 'number') setShowProxyFields(true)
      if (typeof sur === 'string') setSurname(sur)
      if (typeof dist === 'string') setHomeDistrict(dist)
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Resume parsing failed')
    } finally {
      setParsing(false)
    }
  }

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
        ...(showProxyFields
          ? {
              applicant_surname: applicant_surname.trim() || null,
              home_district: home_district.trim() || null,
              village_code: village_code.trim() || null,
              emotion_score: emotion_score,
            }
          : {}),
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
        <div
          className="mb-5"
          style={{
            border: '1px solid #E4E2DC',
            borderRadius: '8px',
            padding: '14px 16px',
            backgroundColor: '#F7F6F3',
          }}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="font-sans font-semibold text-sm" style={{ color: '#0D0D0D' }}>
                Candidate ingestion
              </div>
              <div className="font-sans text-xs mt-0.5" style={{ color: '#6B6B6B' }}>
                Streamlit feature parity: manual input or resume upload (JD-aware)
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setInputMode('manual')}
                className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                style={{
                  border: '1px solid #E4E2DC',
                  backgroundColor: inputMode === 'manual' ? '#FFFFFF' : 'transparent',
                  color: '#0D0D0D',
                  cursor: 'pointer',
                }}
              >
                Manual
              </button>
              <button
                type="button"
                onClick={() => setInputMode('resume')}
                className="font-sans text-xs font-medium px-3 py-1.5 rounded-md"
                style={{
                  border: '1px solid #E4E2DC',
                  backgroundColor: inputMode === 'resume' ? '#FFFFFF' : 'transparent',
                  color: '#0D0D0D',
                  cursor: 'pointer',
                }}
              >
                Resume upload (PDF)
              </button>
            </div>
          </div>

          {inputMode === 'resume' && (
            <div className="mt-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-sans text-xs block mb-1" style={{ color: '#6B6B6B' }}>
                    Target role (JD preset)
                  </label>
                  <select
                    value={jdOption}
                    onChange={(e) => {
                      const next = e.target.value as 'Custom' | keyof typeof PREDEFINED_JDS
                      setJdOption(next)
                      if (next !== 'Custom') setJdText(PREDEFINED_JDS[next])
                    }}
                    style={{ ...inputStyle }}
                  >
                    {(['Custom', ...Object.keys(PREDEFINED_JDS)] as Array<'Custom' | keyof typeof PREDEFINED_JDS>).map(
                      (opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      )
                    )}
                  </select>
                </div>
                <div>
                  <label className="font-sans text-xs block mb-1" style={{ color: '#6B6B6B' }}>
                    Resume PDF
                  </label>
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
                    style={{ ...inputStyle, paddingTop: 8 }}
                  />
                </div>
                <div className="col-span-2">
                  <label className="font-sans text-xs block mb-1" style={{ color: '#6B6B6B' }}>
                    Job description
                  </label>
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    rows={4}
                    className="w-full font-sans text-sm p-3 rounded-md"
                    style={{
                      border: '1px solid #E4E2DC',
                      backgroundColor: '#FFFFFF',
                      color: '#0D0D0D',
                      outline: 'none',
                      resize: 'vertical',
                    }}
                  />
                </div>
              </div>

              {parseError && (
                <p className="font-sans text-xs mt-3" style={{ color: '#B91C1C' }}>
                  {parseError}
                </p>
              )}

              <div className="flex items-center gap-3 mt-3">
                <button
                  type="button"
                  onClick={() => void handleParseResume()}
                  disabled={parsing}
                  className="font-sans text-xs font-medium px-3 py-2 rounded-md"
                  style={{
                    backgroundColor: parsing ? '#9CA3AF' : '#0D6EFD',
                    color: '#FFFFFF',
                    border: 'none',
                    cursor: parsing ? 'wait' : 'pointer',
                  }}
                >
                  {parsing ? 'Parsing…' : 'Evaluate resume with Gemini'}
                </button>
                <span className="font-sans text-xs" style={{ color: '#9B9B9B' }}>
                  Populates the form below with extracted fields (name, experience, skill score, proxies if detected).
                </span>
              </div>
            </div>
          )}
        </div>

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

        <label className="flex items-center gap-2 mt-4 cursor-pointer">
          <input
            type="checkbox"
            checked={showProxyFields}
            onChange={(e) => setShowProxyFields(e.target.checked)}
            style={{ width: '16px', height: '16px', accentColor: '#0D6EFD' }}
          />
          <span className="font-sans text-sm" style={{ color: '#0D0D0D' }}>
            Include proxy / prohibited fields (for governance demo)
          </span>
        </label>

        {showProxyFields && (
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls} style={labelStyle}>
                Applicant surname
              </label>
              <input value={applicant_surname} onChange={(e) => setSurname(e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label className={labelCls} style={labelStyle}>
                Home district
              </label>
              <input value={home_district} onChange={(e) => setHomeDistrict(e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label className={labelCls} style={labelStyle}>
                Village code
              </label>
              <input value={village_code} onChange={(e) => setVillageCode(e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label className={labelCls} style={labelStyle}>
                Emotion score (0–1)
              </label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={emotion_score}
                onChange={(e) => setEmotionScore(Number(e.target.value))}
                style={inputStyle}
              />
            </div>
          </div>
        )}

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
