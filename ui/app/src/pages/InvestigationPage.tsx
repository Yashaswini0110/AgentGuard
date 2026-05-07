import { Link, useParams } from 'react-router'
import { useCallback, useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import { ArrowLeft } from 'lucide-react'
import { ChartContainer } from '@/components/ui/chart'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import type { GovernanceTrace } from '@/lib/api'
import { fetchGovernanceTrace, postArtifactVerify } from '@/lib/api'
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts'

export default function InvestigationPage() {
  const { decisionId } = useParams<{ decisionId: string }>()
  const [trace, setTrace] = useState<GovernanceTrace | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [verify, setVerify] = useState<boolean | null>(null)

  const load = useCallback(async () => {
    if (!decisionId) return
    setErr(null)
    try {
      const t = await fetchGovernanceTrace(decisionId)
      setTrace(t)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Load failed')
    }
  }, [decisionId])

  useEffect(() => {
    void load()
  }, [load])

  const runVerify = async () => {
    if (!decisionId) return
    try {
      const res = await postArtifactVerify(decisionId)
      setVerify(res.integrity_verified ?? false)
    } catch {
      setVerify(null)
    }
  }

  if (!decisionId) {
    return (
      <AppShell>
        <p className="font-sans text-sm">Missing decision id.</p>
      </AppShell>
    )
  }

  const router = trace?.router as Record<string, unknown> | undefined
  const policy = trace?.policy as Record<string, unknown> | undefined
  const ingress = trace?.ingress_snapshot as Record<string, unknown> | undefined
  const canon = trace?.canonical_artifact_view as Record<string, unknown> | undefined
  const violations = (policy?.violations as unknown[]) ?? []
  const shap = ((router?.shap_scores as Record<string, number>) ?? {})
  const routerFeatures = ((router?.router_features as Record<string, unknown>) ?? {})
  const routerProbs = ((router?.router_probabilities as Record<string, number>) ?? {})
  const explainedClass = String(router?.shap_explained_class ?? '')
  const routerSkippedReason = String(router?.router_skipped_reason ?? '')

  const shapBars = Object.entries(shap)
    .map(([name, value]) => ({ name, value: Number(value) }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 6)

  const topDrivers = shapBars.slice(0, 3).map((x) => x.name).join(', ')
  const timeline = (trace?.timeline as { phase?: string; at?: string; detail?: unknown }[]) ?? []

  const policyBlocked = String(canon?.policy_result ?? '') === 'BLOCK'
  const explainabilityLabel = policyBlocked
    ? 'RED — Policy hard block (router skipped; no SHAP)'
    : explainedClass
      ? `Explaining probability of ${explainedClass}`
      : 'Explainability'

  return (
    <AppShell>
      <div className="mb-6">
        <Link
          to="/decisions"
          className="inline-flex items-center gap-1 font-sans text-sm mb-4"
          style={{ color: '#0D6EFD', textDecoration: 'none' }}
        >
          <ArrowLeft size={14} /> Decision stream
        </Link>
        <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
          Decision investigation
        </h1>
        <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
          Trace hash <span className="font-mono text-xs">{String(trace?.trace_id ?? decisionId)}</span> ·{' '}
          <span className="font-mono text-xs">GET /v2/traces/{'{id}'}</span>
        </p>
        {err && (
          <p className="font-sans text-xs mt-3" style={{ color: '#B91C1C' }}>
            {err}
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-4">
        <Card className="flex-1 min-w-[260px]">
          <CardHeader>
            <CardTitle className="text-base">Ingress</CardTitle>
            <CardDescription>Adapter and subject identifiers</CardDescription>
          </CardHeader>
          <CardContent className="font-mono text-xs space-y-1">
            <div>adapter: {String(ingress?.adapter ?? '')}</div>
            <div>received: {String(canon?.timestamp ?? '')}</div>
          </CardContent>
        </Card>

        <Card className="flex-1 min-w-[260px]">
          <CardHeader>
            <CardTitle className="text-base">Policy</CardTitle>
            <CardDescription>Violations cite published rules</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="font-sans text-sm mb-2">Summary: {String(policy?.summary ?? '')}</p>
            <ul className="list-disc ml-5 font-sans text-xs space-y-1">
              {(violations as { rule_name?: string; regulation?: string }[]).slice(0, 6).map((v, i) => (
                <li key={i}>
                  {v.rule_name} · {v.regulation}
                </li>
              ))}
              {violations.length === 0 && <li className="text-muted-foreground">No violations recorded.</li>}
            </ul>
          </CardContent>
        </Card>

        <Card className="flex-1 min-w-[260px]">
          <CardHeader>
            <CardTitle className="text-base">ITSM bridge</CardTitle>
            <CardDescription>ServiceNow linkage when RED</CardDescription>
          </CardHeader>
          <CardContent className="font-mono text-xs">
            {(canon?.servicenow_ticket_id ? String(canon.servicenow_ticket_id) : 'No incident id on artifact')}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Router explainability</CardTitle>
          <CardDescription>
            {explainabilityLabel}
            {!policyBlocked && topDrivers ? ` · Top drivers: ${topDrivers}` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!policyBlocked && Object.keys(routerProbs).length > 0 && (
            <p className="font-mono text-[11px] mb-3" style={{ color: '#6B6B6B' }}>
              class_probs: {Object.entries(routerProbs).map(([k, v]) => `${k}=${Number(v).toFixed(2)}`).join(' · ')}
            </p>
          )}
          {policyBlocked && (
            <p className="font-sans text-sm" style={{ color: '#6B6B6B' }}>
              Router was skipped because policy recommended BLOCK ({routerSkippedReason || 'POLICY_BLOCK'}).
            </p>
          )}
          <ChartContainer
            config={{ shap: { label: 'Contribution', color: 'hsl(var(--chart-1))' } }}
            className="h-[280px] w-full"
          >
            <BarChart data={shapBars} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(val: unknown, nm: unknown) => {
                  const feature = String(nm)
                  const v = Number(val)
                  const fv = routerFeatures[feature]
                  const dir = v >= 0 ? 'increases' : 'decreases'
                  const cls = explainedClass || 'explained class'
                  return [`${v.toFixed(3)} (${dir} ${cls}) · value=${String(fv ?? '—')}`, feature]
                }}
              />
              <Bar dataKey="value" fill="#2563eb" radius={4} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Governance timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2 font-sans text-xs">
            {timeline.map((e, idx) => (
              <li key={idx}>
                <span className="font-mono" style={{ color: '#9B9B9B' }}>{String(e.phase)}</span> ·{' '}
                <span style={{ color: '#6B6B6B' }}>{String(e.at)}</span>
              </li>
            ))}
          </ol>
          {timeline.length === 0 && (
            <p className="text-sm text-muted-foreground">Older artifacts may omit embedded events.</p>
          )}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Artifact</CardTitle>
          <CardDescription>Signed envelope + integrity check</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="font-mono text-xs break-all">hash: {String(canon?.artifact_hash ?? '')}</p>
          <Separator />
          <div className="flex gap-2 items-center flex-wrap">
            <button
              type="button"
              className="font-sans text-sm px-3 py-2 rounded-md"
              style={{ border: '1px solid #E4E2DC', background: '#fff', cursor: 'pointer' }}
              onClick={() => void runVerify()}
            >
              Verify integrity
            </button>
            {verify !== null && (
              <span className="font-sans text-sm" style={{ color: verify ? '#15803D' : '#B91C1C' }}>
                {verify ? 'Verified' : 'Integrity failure'}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </AppShell>
  )
}
