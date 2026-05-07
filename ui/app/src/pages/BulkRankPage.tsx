import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { ArrowLeft, ClipboardList, Download, Layers, ShieldAlert } from 'lucide-react'
import AppShell from '@/components/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { apiBase, joinUrl, postBatchRankStream } from '@/lib/api'
import type { BatchRankCandidateRow, BatchRankResponse } from '@/types/agentguard'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

function exportUrl(decisionId: string) {
  return joinUrl(apiBase(), `/decisions/${encodeURIComponent(decisionId)}/export`)
}

export default function BulkRankPage() {
  const [jobDescription, setJobDescription] = useState('')
  const [openings, setOpenings] = useState(5)
  const [zipFile, setZipFile] = useState<File | null>(null)

  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progressLabel, setProgressLabel] = useState('')
  const [processedCount, setProcessedCount] = useState(0)

  const [result, setResult] = useState<BatchRankResponse | null>(null)
  const [detail, setDetail] = useState<BatchRankCandidateRow | null>(null)

  const chartRows = useMemo(() => {
    if (!result?.ranked_candidates?.length) return []
    const m: Record<string, number> = {}
    for (const r of result.ranked_candidates) {
      const k = (r.governance_status ?? 'UNKNOWN').toUpperCase()
      m[k] = (m[k] ?? 0) + 1
    }
    return Object.entries(m).map(([name, count]) => ({ name, count }))
  }, [result])

  const blocked = useMemo(
    () => (result?.ranked_candidates ?? []).filter((r) => (r.governance_status ?? '').includes('BLOCK')),
    [result]
  )

  const reviewQueueEligible = useMemo(() => {
    if (!result?.ranked_candidates?.length) return 0
    return result.ranked_candidates.filter((r) => Boolean(r.artifact_reference?.decision_id)).length
  }, [result])

  const tentativeTop = useMemo(() => {
    const hold = Boolean(result?.pool_quota_policy?.tentative_hold)
    const n = Number(result?.open_positions ?? openings)
    if (!hold || !result?.ranked_candidates) return []
    return result.ranked_candidates.filter(
      (r) => (r.rank ?? 0) <= n && (r.governance_status ?? '') === 'TENTATIVE_HOLD'
    )
  }, [result, openings])

  const handleRun = async () => {
    setError(null)
    setResult(null)
    setProgressLabel('')
    setProcessedCount(0)
    if (!zipFile) {
      setError('Please choose a ZIP that contains PDF and/or DOCX resumes.')
      return
    }
    if (!jobDescription.trim()) {
      setError('Job description is required for merit scoring.')
      return
    }
    setRunning(true)
    try {
      const data = await postBatchRankStream(
        zipFile,
        jobDescription.trim(),
        Math.max(1, Number(openings) || 1),
        (evt) => {
          const ph = evt.phase as string | undefined
          if (evt.type === 'progress' && ph === 'start') {
            setProgressLabel(`Processing: ${String(evt.file ?? '').split('/').pop() ?? evt.candidate_id}`)
          }
          if (
            evt.type === 'progress' &&
            (ph === 'done' || ph === 'error' || ph === 'pipeline_error')
          ) {
            setProcessedCount((c) => c + 1)
            setProgressLabel(`Finished leg: ${String(evt.file ?? '').split('/').pop() ?? evt.candidate_id}`)
          }
        }
      )
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Bulk ranking failed')
    } finally {
      setRunning(false)
      setProgressLabel('')
    }
  }

  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[#6B6B6B]">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1 text-xs font-medium"
                style={{ color: '#0D6EFD', textDecoration: 'none' }}
              >
                <ArrowLeft size={14} /> Back to dashboard
              </Link>
            </div>
            <div className="flex items-center gap-2">
              <Layers size={20} style={{ color: '#0D6EFD' }} />
              <h1 className="font-sans text-xl font-semibold" style={{ color: '#0D0D0D' }}>
                Bulk resume intelligence
              </h1>
            </div>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed" style={{ color: '#6B6B6B' }}>
              Upload the full applicant ZIP, run governance on every resume in parallel, and receive a merit-ranked
              shortlist. Rankings deliberately ignore intra-archive ordering.
            </p>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <Card className="border-[#E4E2DC]" style={{ backgroundColor: '#FFFFFF' }}>
            <CardHeader className="pb-3">
              <CardTitle className="font-sans text-base">Pool-first intake</CardTitle>
              <CardDescription>ZIP ingestion, JD context, concurrency-safe governance hooks.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="jd">Job description</Label>
                <Textarea
                  id="jd"
                  rows={8}
                  className="font-mono text-xs"
                  style={{ borderColor: '#E4E2DC' }}
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the live job description from your ATS or internal requisition — nothing is hard-coded here."
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="opens">Open positions</Label>
                  <Input
                    id="opens"
                    type="number"
                    min={1}
                    max={5000}
                    value={openings}
                    onChange={(e) => setOpenings(Number(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="zip">Resume archive (.zip)</Label>
                  <Input
                    id="zip"
                    type="file"
                    accept=".zip,application/zip"
                    onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
                  />
                </div>
              </div>

              {error ? (
                <Alert variant="destructive">
                  <ShieldAlert />
                  <AlertTitle>Run blocked</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              <Button
                type="button"
                disabled={running}
                onClick={() => void handleRun()}
                className="w-full sm:w-auto"
                style={{ backgroundColor: '#0D6EFD' }}
              >
                {running ? 'Running governance mesh…' : 'Start parallel pool review'}
              </Button>

              {running ? (
                <div className="space-y-2 rounded-md border border-dashed border-[#E4E2DC] p-3">
                  <div className="flex justify-between text-xs" style={{ color: '#6B6B6B' }}>
                    <span>Streams candidate-level progress via SSE.</span>
                    <span>{processedCount} finalized</span>
                  </div>
                  <Progress
                    value={processedCount === 0 ? 12 : Math.min(100, 10 + processedCount * 4)}
                    className="h-2"
                  />
                  <p className="text-xs font-mono" style={{ color: '#9B9B9B' }}>
                    {progressLabel || 'Fan-out workers running policy → router → supervisor path…'}
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card className="border-[#E4E2DC]">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 font-sans text-sm">
                  <ShieldAlert size={14} />
                  Governance commitments
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs leading-relaxed" style={{ color: '#6B6B6B' }}>
                <p>ZIP order is hashed into a RNG seed — ranking never mirrors queue sequence.</p>
                <p>Each candidate routes through the same worker, policy, router, supervisor, ServiceNow, and artifact stack as /decision.</p>
                <p className="pt-2 border-t border-[#E4E2DC]">
                  <strong>HR review:</strong> one artifact is saved per résumé. Every bulk candidate is tagged for intake
                  acknowledgement and appears in{' '}
                  <Link to="/review" style={{ color: '#0D6EFD', fontWeight: 600 }}>
                    Review Queue
                  </Link>{' '}
                  until HR approves / rejects, escalates, or tech review clears the row (including GREEN merit matches).
                </p>
                <p>Quota latch monitors pool coverage before final approval waves.</p>
              </CardContent>
            </Card>
          </div>
        </div>

        {result?.pool_quota_policy?.tentative_hold ? (
          <Alert className="border-amber-200 bg-amber-50">
            <AlertTitle className="text-amber-900">Quota exhaustion guard</AlertTitle>
            <AlertDescription className="text-amber-950">
              Final approvals may be frozen: reviewed pool{' '}
              <strong>{((result.pool_quota_policy.reviewed_pool_percentage ?? 0) * 100).toFixed(1)}%</strong> versus
              minimum <strong>{((result.pool_quota_policy.min_pool_review_threshold ?? 0.8) * 100).toFixed(0)}%</strong>.
              Top {result.open_positions} slots are flagged as tentative hold until HR clears the backlog.
              {tentativeTop.length ? (
                <span className="mt-2 block font-mono text-[11px]">
                  Held IDs:{' '}
                  {tentativeTop
                    .map((r) => r.candidate_id)
                    .filter(Boolean)
                    .slice(0, 8)
                    .join(', ')}
                </span>
              ) : null}
            </AlertDescription>
          </Alert>
        ) : null}

        {result ? (
          <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
            <Card className="border-[#E4E2DC]" style={{ gridColumn: '1 / -1' }}>
              <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex gap-3">
                  <ClipboardList className="mt-0.5 shrink-0" size={18} style={{ color: '#0D6EFD' }} />
                  <div className="text-sm" style={{ color: '#3B3B3B' }}>
                    <p className="font-medium" style={{ color: '#0D0D0D' }}>
                      Next step: compliance review
                    </p>
                    <p className="mt-1 leading-relaxed" style={{ color: '#6B6B6B' }}>
                      This run persisted artifacts for each file (including ingestion or pipeline failures, which save a
                      RED/BLOCK audit row with the captured error reason).{' '}
                      <strong>{reviewQueueEligible}</strong> candidate
                      {reviewQueueEligible === 1 ? '' : 's'} {reviewQueueEligible === 1 ? 'is' : 'are'} in the HR review
                      scope for this bulk session. Use <span className="font-mono text-xs">Review queue</span> per row or
                      open the filtered session view.
                    </p>
                  </div>
                </div>
                <Button asChild className="shrink-0" style={{ backgroundColor: '#0D0D0D' }}>
                  <Link
                    to={
                      result?.bulk_session_id
                        ? `/review?session=${encodeURIComponent(String(result.bulk_session_id))}`
                        : '/review'
                    }
                  >
                    Open Review Queue
                  </Link>
                </Button>
              </CardContent>
            </Card>

            <Card className="border-[#E4E2DC]">
              <CardHeader>
                <CardTitle className="font-sans text-base">{result.job_role}</CardTitle>
                <CardDescription>
                  {result.successful_ingestion ?? '—'} / {result.total_candidates ?? '—'} ingested •{' '}
                  {Math.round(Number(result.processing_time_ms ?? 0))} ms • digest{' '}
                  <span className="font-mono">{String(result.job_description_digest ?? '')}</span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-4 h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartRows} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E4E2DC" />
                      <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#0D6EFD" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">#</TableHead>
                      <TableHead>Candidate</TableHead>
                      <TableHead className="text-right">Merit</TableHead>
                      <TableHead>Governance</TableHead>
                      <TableHead className="w-[7.5rem]">Review</TableHead>
                      <TableHead className="w-28">Artifacts</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.ranked_candidates?.map((row) => (
                      <TableRow key={`${row.rank}-${row.candidate_id}`}>
                        <TableCell className="font-mono text-xs">{row.rank}</TableCell>
                        <TableCell>
                          <button
                            type="button"
                            className="text-left text-sm font-medium hover:underline"
                            style={{ color: '#0D6EFD' }}
                            onClick={() => setDetail(row)}
                          >
                            {row.candidate_name}
                          </button>
                          <div className="truncate font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
                            {(row.top_skills ?? []).slice(0, 6).join(' · ') || '—'}
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {(Number(row.composite_score ?? 0) * 100).toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-xs">{row.governance_status ?? '—'}</TableCell>
                        <TableCell>
                          {row.artifact_reference?.decision_id ? (
                            <Link
                              to={`/review?decision=${encodeURIComponent(String(row.artifact_reference.decision_id))}`}
                              className="font-sans text-xs font-medium hover:underline"
                              style={{ color: '#0D6EFD' }}
                            >
                              Review queue
                            </Link>
                          ) : (
                            <span className="text-xs" style={{ color: '#9B9B9B' }}>
                              —
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="gap-1"
                            disabled={!row.artifact_reference?.decision_id}
                            onClick={() => {
                              const id = row.artifact_reference?.decision_id
                              if (id) window.open(exportUrl(String(id)), '_blank')
                            }}
                          >
                            <Download size={12} /> Export
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card className="border-[#E4E2DC]">
              <CardHeader>
                <CardTitle className="font-sans text-sm">Governance violations</CardTitle>
                <CardDescription>Blocked profiles remain auditable yet excluded from merit leadership.</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[420px] pr-4">
                  {blocked.length === 0 ? (
                    <p className="text-sm" style={{ color: '#6B6B6B' }}>
                      No blocked governance states in this run.
                    </p>
                  ) : (
                    <ul className="space-y-3 text-xs">
                      {blocked.map((b) => (
                        <li
                          key={b.candidate_id ?? b.rank}
                          className="rounded border border-[#F3DADA] bg-[#FFF7F7] px-3 py-2"
                        >
                          <div className="font-semibold">{b.candidate_name}</div>
                          <div className="font-mono text-[11px]" style={{ color: '#9B3B3B' }}>
                            {b.policy_rule ?? 'POLICY_OR_ROUTING'}
                          </div>
                          <div className="mt-1" style={{ color: '#7A4A4A' }}>
                            {b.reasoning}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </ScrollArea>

                {(result.skipped_files?.length ?? 0) > 0 ? (
                  <div className="mt-4 border-t pt-4">
                    <p className="mb-2 text-xs font-semibold" style={{ color: '#6B6B6B' }}>
                      Skipped files ({result.skipped_files?.length})
                    </p>
                    <ul className="space-y-1 font-mono text-[11px]" style={{ color: '#9B9B9B' }}>
                      {result.skipped_files?.slice(0, 8).map((s) => (
                        <li key={s.file}>
                          {s.file} — {s.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>

      <Dialog open={detail != null} onOpenChange={() => setDetail(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{detail?.candidate_name}</DialogTitle>
            <DialogDescription>{detail?.experience_summary}</DialogDescription>
          </DialogHeader>
          {detail?.artifact_reference?.decision_id ? (
            <Button asChild variant="outline" size="sm" className="mb-3 w-fit">
              <Link
                to={
                  detail?.artifact_reference?.bulk_session_id
                    ? `/review?session=${encodeURIComponent(String(detail.artifact_reference.bulk_session_id))}&decision=${encodeURIComponent(String(detail.artifact_reference.decision_id))}`
                    : `/review?decision=${encodeURIComponent(String(detail.artifact_reference.decision_id))}`
                }
              >
                Open in Review Queue
              </Link>
            </Button>
          ) : null}
          {detail?.score_breakdown ? (
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              {Object.entries(detail.score_breakdown).map(([k, v]) => (
                <div key={k} className="rounded border px-2 py-1">
                  <div style={{ color: '#9B9B9B' }}>{k}</div>
                  <div>{typeof v === 'number' ? (v <= 1 ? `${(v * 100).toFixed(1)}%` : v.toFixed(2)) : String(v)}</div>
                </div>
              ))}
            </div>
          ) : null}
          <div className="text-sm leading-relaxed" style={{ color: '#3B3B3B' }}>
            {detail?.reasoning}
          </div>
          <Button
            type="button"
            disabled={!detail?.artifact_reference?.decision_id}
            onClick={() => {
              const id = detail?.artifact_reference?.decision_id
              if (id) window.open(exportUrl(String(id)), '_blank')
            }}
          >
            <Download size={14} /> Download regulator export
          </Button>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
