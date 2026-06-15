import { useMemo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  FEATURE_GLOSSARY,
  FEATURE_LABELS,
  SAFE_FEATURE_ORDER,
  shapBreakdownLines,
  shapFeatureLabel,
} from '@/lib/artifactHelpers'

const SHAP_READING_GUIDE =
  'How to read this: Our model does not just output GREEN, YELLOW, or RED — it shows why. ' +
  'For each decision, we calculate how much each factor pushed the result toward the final ' +
  'classification versus away from it. A long bar means that factor had a strong influence; ' +
  'the direction shows whether it supported or worked against this specific outcome.'

export interface ShapExplainabilityPanelProps {
  shapScores?: Record<string, number> | null
  routerFeatures?: Record<string, number> | null
  riskLevel?: string | null
  title?: string
}

export default function ShapExplainabilityPanel({
  shapScores,
  routerFeatures,
  riskLevel,
  title = 'Model Explainability (SHAP)',
}: ShapExplainabilityPanelProps) {
  const level = (riskLevel ?? 'UNKNOWN').toUpperCase()

  const chartData = useMemo(() => {
    const entries = Object.entries(shapScores ?? {})
      .map(([feature, value]) => ({
        feature,
        label: shapFeatureLabel(feature),
        impact: Number(value),
      }))
      .filter((row) => Number.isFinite(row.impact))
      .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    return entries
  }, [shapScores])

  const breakdown = useMemo(
    () => shapBreakdownLines(shapScores, routerFeatures, level),
    [shapScores, routerFeatures, level]
  )

  if (!chartData.length) {
    return (
      <div>
        <h4 className="font-sans font-medium text-[13px] mb-2" style={{ color: '#0D0D0D' }}>
          {title}
        </h4>
        <p className="font-sans text-xs" style={{ color: '#6B6B6B' }}>
          SHAP values not available for this classification.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h4 className="font-sans font-medium text-[13px] mb-2" style={{ color: '#0D0D0D' }}>
        {title}
      </h4>

      <details
        className="mb-2 rounded-md border px-3 py-2"
        style={{ borderColor: '#E4E2DC', backgroundColor: '#FAFAF8' }}
      >
        <summary
          className="cursor-pointer font-sans text-xs font-medium select-none"
          style={{ color: '#374151' }}
        >
          What do these factors mean?
        </summary>
        <ul className="mt-2 space-y-2 list-none pl-0">
          {SAFE_FEATURE_ORDER.map((key) => (
            <li key={key} className="font-sans text-xs leading-relaxed" style={{ color: '#4B5563' }}>
              <strong style={{ color: '#0D0D0D' }}>{FEATURE_LABELS[key]}</strong>
              <span style={{ color: '#9B9B9B' }}> — </span>
              {FEATURE_GLOSSARY[key]}
            </li>
          ))}
        </ul>
      </details>

      <details
        className="mb-3 rounded-md border px-3 py-2"
        style={{ borderColor: '#D6E4FF', backgroundColor: '#F0F6FF' }}
      >
        <summary
          className="cursor-pointer font-sans text-xs font-medium select-none"
          style={{ color: '#1D4ED8' }}
        >
          How to read this chart
        </summary>
        <p className="font-sans text-xs mt-2 leading-relaxed" style={{ color: '#374151' }}>
          {SHAP_READING_GUIDE}
        </p>
      </details>

      <p className="font-sans text-xs mb-3 leading-relaxed" style={{ color: '#6B6B6B' }}>
        These are the factors that most influenced this <strong>{level}</strong> classification.
        Bars pointing right pushed toward <strong>{level}</strong>; bars pointing left pushed
        toward a different classification.
      </p>

      <p className="font-sans text-[11px] mb-2" style={{ color: '#9B9B9B' }}>
        Orange = toward {level} · Blue = away from {level} (bar length shows strength; numbers
        hidden — see breakdown below)
      </p>

      <div style={{ width: '100%', height: Math.max(200, chartData.length * 36) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E4E2DC" />
            <XAxis type="number" tick={false} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              width={160}
              tick={{ fontSize: 11, fill: '#0D0D0D' }}
            />
            <Tooltip
              formatter={(value: number) => [value.toFixed(4), 'Influence']}
              labelFormatter={(label) => String(label)}
            />
            <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
              {chartData.map((entry) => (
                <Cell
                  key={entry.feature}
                  fill={entry.impact >= 0 ? '#e67e22' : '#2980b9'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {breakdown.length > 0 ? (
        <div className="mt-3">
          <p
            className="font-sans text-xs font-medium mb-2"
            style={{ color: '#0D0D0D' }}
          >
            Factor-by-factor explanation
          </p>
          <ul className="space-y-1.5 list-disc pl-4">
            {breakdown.map((line) => (
              <li
                key={line}
                className="font-sans text-xs leading-relaxed"
                style={{ color: '#374151' }}
              >
                {line}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
