import { useEffect, useState, useCallback } from 'react'
import { BarChart3, RefreshCw, Zap, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, Legend
} from 'recharts'
import { fetchEvaluation } from '../api/client'
import toast from 'react-hot-toast'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <b>{typeof p.value === 'number' ? p.value.toFixed(3) : p.value}</b>
        </p>
      ))}
    </div>
  )
}

const DeltaBadge = ({ v1, v2 }) => {
  if (v1 == null || v2 == null) return <span className="badge badge-info">N/A</span>
  const diff = v2 - v1
  if (Math.abs(diff) < 0.001) return <span className="badge badge-info"><Minus size={10} /> Equal</span>
  if (diff > 0) return <span className="badge badge-success"><TrendingUp size={10} /> V2 +{(diff * 100).toFixed(2)}%</span>
  return <span className="badge badge-danger"><TrendingDown size={10} /> V2 {(diff * 100).toFixed(2)}%</span>
}

export default function ModelComparison() {
  const [eval_, setEval] = useState(null)
  const [loading, setLoading] = useState(true)
  const [window_, setWindow] = useState(24)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const e = await fetchEvaluation(window_)
      setEval(e)
    } catch {
      toast.error('Failed to load comparison data')
    } finally {
      setLoading(false)
    }
  }, [window_])

  useEffect(() => { load() }, [load])

  const pct = v => v != null ? +(v * 100).toFixed(2) : null
  const ms  = v => v != null ? +v.toFixed(2) : null

  const radarData = eval_ ? [
    { metric: 'Accuracy', v1: pct(eval_.v1_accuracy) ?? 0, v2: pct(eval_.v2_accuracy) ?? 0 },
    { metric: 'Reliability', v1: (1 - eval_.v1_error_rate) * 100, v2: (1 - eval_.v2_error_rate) * 100 },
    { metric: 'Speed', v1: Math.max(0, 100 - eval_.v1_avg_latency_ms), v2: Math.max(0, 100 - eval_.v2_avg_latency_ms) },
    { metric: 'Agreement', v1: pct(eval_.agreement_rate) ?? 0, v2: pct(eval_.agreement_rate) ?? 0 },
  ] : []

  const barData = [
    { name: 'Accuracy (%)', v1: pct(eval_?.v1_accuracy), v2: pct(eval_?.v2_accuracy) },
    { name: 'Error Rate (%)', v1: pct(eval_?.v1_error_rate), v2: pct(eval_?.v2_error_rate) },
    { name: 'Latency (ms)', v1: ms(eval_?.v1_avg_latency_ms), v2: ms(eval_?.v2_avg_latency_ms) },
  ]

  return (
    <div className="fade-in">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Model Comparison</h1>
          <p>Side-by-side shadow mode performance analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={window_} onChange={e => setWindow(+e.target.value)} style={{ fontSize: '0.85rem' }}>
            {[1, 6, 12, 24, 48, 168].map(h => <option key={h} value={h}>{h}h window</option>)}
          </select>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Promotion Banner */}
      {eval_?.promotion_candidate && (
        <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid var(--accent-warning)', borderRadius: 'var(--radius-md)', padding: '14px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Zap size={18} color="var(--accent-warning)" />
          <div>
            <strong style={{ color: 'var(--accent-warning)' }}>Promotion Candidate Detected!</strong>
            <span style={{ color: 'var(--text-secondary)', marginLeft: 8, fontSize: '0.875rem' }}>
              Model V2 has consistently outperformed V1 by ≥2% accuracy over {eval_.sample_count} samples.
            </span>
          </div>
        </div>
      )}

      {/* Comparison Table */}
      <div className="card section" style={{ marginBottom: 24 }}>
        <div className="section-title"><BarChart3 size={16} /> Performance Summary</div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Model V1 (Production)</th>
                <th>Model V2 (Shadow)</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 24 }}>Loading...</td></tr>
              ) : eval_ ? (
                <>
                  <tr>
                    <td>Accuracy</td>
                    <td><span className="font-mono">{pct(eval_.v1_accuracy) ?? '—'}%</span></td>
                    <td><span className="font-mono">{pct(eval_.v2_accuracy) ?? '—'}%</span></td>
                    <td><DeltaBadge v1={eval_.v1_accuracy} v2={eval_.v2_accuracy} /></td>
                  </tr>
                  <tr>
                    <td>Avg Latency</td>
                    <td><span className="font-mono">{ms(eval_.v1_avg_latency_ms)} ms</span></td>
                    <td><span className="font-mono">{ms(eval_.v2_avg_latency_ms)} ms</span></td>
                    <td><DeltaBadge v1={-eval_.v1_avg_latency_ms} v2={-eval_.v2_avg_latency_ms} /></td>
                  </tr>
                  <tr>
                    <td>Error Rate</td>
                    <td><span className="font-mono">{pct(eval_.v1_error_rate)}%</span></td>
                    <td><span className="font-mono">{pct(eval_.v2_error_rate)}%</span></td>
                    <td><DeltaBadge v1={-eval_.v1_error_rate} v2={-eval_.v2_error_rate} /></td>
                  </tr>
                  <tr>
                    <td>Agreement Rate</td>
                    <td colSpan={2} style={{ textAlign: 'center' }}>
                      <span className="badge badge-info">{pct(eval_.agreement_rate)}%</span>
                    </td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>Drift Score (KS)</td>
                    <td colSpan={2} style={{ textAlign: 'center' }}>
                      <span className={`badge ${eval_.drift_score > 0.1 ? 'badge-danger' : 'badge-success'}`}>
                        {eval_.drift_score?.toFixed(4) ?? '—'}
                      </span>
                    </td>
                    <td>—</td>
                  </tr>
                  <tr>
                    <td>Sample Count</td>
                    <td colSpan={2} style={{ textAlign: 'center' }}>{eval_.sample_count}</td>
                    <td>—</td>
                  </tr>
                </>
              ) : (
                <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>No evaluation data yet. Send requests to /ingest first.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts */}
      <div className="grid-2">
        <div className="card">
          <div className="section-title">Grouped Bar Comparison</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={barData} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
              <Bar dataKey="v1" name="V1 (Prod)" fill="var(--accent-success)" radius={[4,4,0,0]} />
              <Bar dataKey="v2" name="V2 (Shadow)" fill="var(--accent-secondary)" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="section-title">Radar Performance Profile</div>
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Radar name="V1 (Prod)" dataKey="v1" stroke="var(--accent-success)" fill="var(--accent-success)" fillOpacity={0.15} />
              <Radar name="V2 (Shadow)" dataKey="v2" stroke="var(--accent-secondary)" fill="var(--accent-secondary)" fillOpacity={0.15} />
              <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
