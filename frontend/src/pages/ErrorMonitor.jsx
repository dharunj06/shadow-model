import { useEffect, useState, useCallback } from 'react'
import { AlertTriangle, RefreshCw, XCircle, Info, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Cell
} from 'recharts'
import { fetchErrors } from '../api/client'
import toast from 'react-hot-toast'

const SEVERITY_CONFIG = {
  CRITICAL: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', Icon: XCircle     },
  ERROR:    { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', Icon: AlertTriangle },
  WARNING:  { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', Icon: AlertCircle  },
  INFO:     { color: '#6366f1', bg: 'rgba(99,102,241,0.12)', Icon: Info          },
}

export default function ErrorMonitor() {
  const [errors, setErrors]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [filter, setFilter]       = useState('ALL')
  const [selected, setSelected]   = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchErrors(100)
      setErrors(data)
    } catch {
      toast.error('Failed to load errors')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = filter === 'ALL' ? errors : errors.filter(e => e.severity === filter)

  // Summary counts
  const counts = Object.fromEntries(
    ['CRITICAL', 'ERROR', 'WARNING', 'INFO'].map(s => [s, errors.filter(e => e.severity === s).length])
  )

  // Error type breakdown for chart
  const typeBreakdown = Object.entries(
    errors.reduce((acc, e) => { acc[e.error_type] = (acc[e.error_type] || 0) + 1; return acc }, {})
  ).map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count).slice(0, 8)

  return (
    <div className="fade-in">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Error Monitoring</h1>
          <p>Centralized error tracking across all model services</p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Severity Summary */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        {Object.entries(SEVERITY_CONFIG).map(([sev, { color, bg, Icon }]) => (
          <div key={sev} onClick={() => setFilter(filter === sev ? 'ALL' : sev)}
            className="stat-card"
            style={{ cursor: 'pointer', borderColor: filter === sev ? color : 'var(--border)', background: filter === sev ? bg : '' }}>
            <div className="stat-icon"><Icon size={48} /></div>
            <span className="stat-label" style={{ color }}>{sev}</span>
            <span className="stat-value" style={{ color }}>{counts[sev] ?? 0}</span>
            <span className="stat-delta">Click to filter</span>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Error Type Chart */}
        <div className="card">
          <div className="section-title"><AlertTriangle size={16} /> Errors by Type</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={typeBreakdown} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
              <YAxis dataKey="type" type="category" width={110} tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: '0.8rem' }}
                labelStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="count" radius={[0,4,4,0]}>
                {typeBreakdown.map((_, i) => (
                  <Cell key={i} fill={['#6366f1','#8b5cf6','#3b82f6','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6'][i % 8]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Selected Error Detail */}
        {selected ? (
          <div className="card fade-in">
            <div className="section-title"><XCircle size={14} /> Error Detail</div>
            {(() => {
              const { color, bg } = SEVERITY_CONFIG[selected.severity] || SEVERITY_CONFIG.ERROR
              return (
                <div style={{ padding: 14, background: bg, border: `1px solid ${color}`, borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span className="badge" style={{ background: bg, color }}>{selected.severity}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {format(new Date(selected.created_at), 'yyyy-MM-dd HH:mm:ss')}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.82rem' }}>
                    <div><span style={{ color: 'var(--text-secondary)' }}>Type: </span><span className="font-mono">{selected.error_type}</span></div>
                    <div><span style={{ color: 'var(--text-secondary)' }}>Model: </span><span>{selected.model_version ?? '—'}</span></div>
                    <div><span style={{ color: 'var(--text-secondary)' }}>Message:</span>
                      <p style={{ marginTop: 4, color: 'var(--text-primary)', lineHeight: 1.5 }}>{selected.message}</p>
                    </div>
                    {selected.request_id && (
                      <div><span style={{ color: 'var(--text-secondary)' }}>Request: </span>
                        <span className="font-mono text-xs" style={{ color: 'var(--accent-primary)' }}>{selected.request_id}</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })()}
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            <div style={{ textAlign: 'center' }}>
              <Info size={32} style={{ marginBottom: 8, opacity: 0.4 }} />
              <p>Click an error row to see details</p>
            </div>
          </div>
        )}
      </div>

      {/* Errors Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="section-title" style={{ margin: 0 }}><AlertTriangle size={15} /> Error Log ({filtered.length})</span>
          <div className="flex gap-2">
            {['ALL', 'CRITICAL', 'ERROR', 'WARNING', 'INFO'].map(s => (
              <button key={s} onClick={() => setFilter(s)}
                className="btn btn-ghost" style={{ padding: '4px 12px', fontSize: '0.75rem',
                  background: filter === s ? 'rgba(99,102,241,0.15)' : '',
                  color: filter === s ? 'var(--accent-primary)' : '' }}>
                {s}
              </button>
            ))}
          </div>
        </div>
        <div className="table-wrap" style={{ border: 'none' }}>
          <table>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Type</th>
                <th>Model</th>
                <th>Message</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array(6).fill(0).map((_, i) => (
                  <tr key={i}>{Array(5).fill(0).map((_, j) => <td key={j}><div className="skeleton" style={{ height: 14, width: '80%' }} /></td>)}</tr>
                ))
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  {errors.length === 0 ? '🎉 No errors recorded' : 'No errors for this severity'}
                </td></tr>
              ) : filtered.map(err => {
                const { color, Icon } = SEVERITY_CONFIG[err.severity] || SEVERITY_CONFIG.ERROR
                return (
                  <tr key={err.id} onClick={() => setSelected(selected?.id === err.id ? null : err)} style={{ cursor: 'pointer' }}>
                    <td>
                      <span className="badge" style={{ background: `${color}20`, color }}>
                        <Icon size={10} /> {err.severity}
                      </span>
                    </td>
                    <td><span className="font-mono text-xs">{err.error_type}</span></td>
                    <td>{err.model_version ? <span className="badge badge-purple">{err.model_version}</span> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                    <td style={{ maxWidth: 320 }}><span className="truncate" style={{ display: 'block', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>{err.message}</span></td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{format(new Date(err.created_at), 'MM/dd HH:mm:ss')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
