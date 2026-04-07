import { useEffect, useState, useCallback } from 'react'
import { Activity, TrendingUp, AlertCircle, Clock, RefreshCw, CheckCircle, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { format } from 'date-fns'
import { fetchEvaluation, fetchMetricsHistory, fetchHealth } from '../api/client'
import ModelEvaluation from '../components/ModelEvaluation'
import toast from 'react-hot-toast'

const StatCard = ({ label, value, delta, icon: Icon, color = 'var(--accent-primary)' }) => (
  <div className="stat-card fade-in">
    <div className="stat-icon"><Icon size={48} /></div>
    <span className="stat-label">{label}</span>
    <span className="stat-value" style={{ color }}>{value ?? '—'}</span>
    {delta && <span className="stat-delta">{delta}</span>}
  </div>
)

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <b>{typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</b>
        </p>
      ))}
    </div>
  )
}

export default function Overview() {
  const [eval_, setEval] = useState(null)
  const [history, setHistory] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [e, h, he] = await Promise.all([fetchEvaluation(24), fetchMetricsHistory(50), fetchHealth()])
      setEval(e)
      setHistory(h.reverse().map(m => ({
        time: format(new Date(m.recorded_at), 'HH:mm'),
        agreement: m.agreement_rate != null ? +(m.agreement_rate * 100).toFixed(1) : null,
        latency_v1: m.avg_latency_ms != null ? +m.avg_latency_ms.toFixed(1) : null,
        drift: m.drift_score != null ? +m.drift_score.toFixed(4) : null,
      })))
      setHealth(he)
      setLastRefresh(new Date())
    } catch {
      toast.error('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [load])

  const pct = v => v != null ? `${(v * 100).toFixed(1)}%` : '—'
  const ms  = v => v != null ? `${v.toFixed(1)} ms` : '—'

  return (
    <div className="fade-in">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Overview Dashboard</h1>
          <p>Real-time shadow mode evaluation · Last updated {format(lastRefresh, 'HH:mm:ss')}</p>
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <span className="badge badge-success">
              <CheckCircle size={12} /> API Healthy
            </span>
          )}
          {eval_?.promotion_candidate && (
            <span className="badge badge-warning">
              <Zap size={12} /> Promotion Candidate
            </span>
          )}
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin-anim' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      {loading && !eval_ ? (
        <div className="grid-4" style={{ marginBottom: 24 }}>
          {[0,1,2,3].map(i => <div key={i} className="stat-card skeleton" style={{ height: 110 }} />)}
        </div>
      ) : (
        <div className="grid-4" style={{ marginBottom: 28 }}>
          <StatCard label="Agreement Rate" value={pct(eval_?.agreement_rate)} icon={Activity} color="var(--accent-primary)" delta={`${eval_?.sample_count ?? 0} samples`} />
          <StatCard label="V1 Accuracy" value={pct(eval_?.v1_accuracy)} icon={TrendingUp} color="var(--accent-success)" delta="Production model" />
          <StatCard label="V2 Accuracy" value={pct(eval_?.v2_accuracy)} icon={TrendingUp} color="var(--accent-secondary)" delta="Shadow model" />
          <StatCard label="Drift Score" value={eval_?.drift_score?.toFixed(4) ?? '—'} icon={AlertCircle} color={eval_?.drift_score > 0.1 ? 'var(--accent-danger)' : 'var(--accent-success)'} delta="KS statistic" />
        </div>
      )}

      {/* Latency cards */}
      {eval_ && (
        <div className="grid-4" style={{ marginBottom: 28 }}>
          <StatCard label="V1 Avg Latency" value={ms(eval_?.v1_avg_latency_ms)} icon={Clock} delta="Production" />
          <StatCard label="V2 Avg Latency" value={ms(eval_?.v2_avg_latency_ms)} icon={Clock} color="var(--accent-secondary)" delta="Shadow" />
          <StatCard label="V1 Error Rate" value={pct(eval_?.v1_error_rate)} icon={AlertCircle} color={eval_?.v1_error_rate > 0.05 ? 'var(--accent-danger)' : 'var(--accent-success)'} delta="Production" />
          <StatCard label="V2 Error Rate" value={pct(eval_?.v2_error_rate)} icon={AlertCircle} color={eval_?.v2_error_rate > 0.05 ? 'var(--accent-danger)' : 'var(--accent-success)'} delta="Shadow" />
        </div>
      )}

      {/* Charts */}
      <div className="grid-2">
        <div className="card section">
          <div className="section-title"><Activity size={16} /> Agreement Rate (%) over Time</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="agreement" stroke="var(--accent-primary)" strokeWidth={2} dot={false} name="Agreement %" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card section">
          <div className="section-title"><Clock size={16} /> Model Latency (ms) Trend</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="latency_v1" stroke="var(--accent-success)" strokeWidth={2} dot={false} name="V2 Latency ms" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Drift */}
      {history.length > 0 && (
        <div className="card section" style={{ marginTop: 20 }}>
          <div className="section-title"><AlertCircle size={16} /> Distribution Drift (KS Score)</div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="time" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis domain={[0, 0.3]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="drift" stroke="var(--accent-warning)" strokeWidth={2} dot={false} name="KS Drift" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Interactive Model Evaluation */}
      <div style={{ marginTop: 28 }}>
        <ModelEvaluation onEvaluationComplete={() => load()} />
      </div>
    </div>
  )
}
