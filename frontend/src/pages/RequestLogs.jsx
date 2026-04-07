import { useEffect, useState, useCallback } from 'react'
import { FileText, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import { fetchRequests } from '../api/client'
import toast from 'react-hot-toast'

const PAGE_SIZE = 20

export default function RequestLogs() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading]   = useState(true)
  const [page, setPage]         = useState(0)
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchRequests(PAGE_SIZE, page * PAGE_SIZE)
      setRequests(data)
    } catch {
      toast.error('Failed to load request logs')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { load() }, [load])

  const getV1 = req => req.predictions?.find(p => p.model_version === 'v1')
  const getV2 = req => req.predictions?.find(p => p.model_version === 'v2')

  return (
    <div className="fade-in">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1>Request Logs</h1>
          <p>All ingested shadow mode requests and internal model outputs</p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={loading}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 360px' : '1fr', gap: 20 }}>
        {/* Table */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrap" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Timestamp</th>
                  <th>Status</th>
                  <th>V1 Pred</th>
                  <th>V2 Pred</th>
                  <th>V1 Latency</th>
                  <th>V2 Latency</th>
                  <th>True Label</th>
                  <th>Agreement</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array(8).fill(0).map((_, i) => (
                    <tr key={i}>
                      {Array(9).fill(0).map((_, j) => (
                        <td key={j}><div className="skeleton" style={{ height: 16, width: '80%' }} /></td>
                      ))}
                    </tr>
                  ))
                ) : requests.length === 0 ? (
                  <tr><td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No requests yet. Send data to POST /api/v1/ingest</td></tr>
                ) : requests.map(req => {
                  const v1 = getV1(req)
                  const v2 = getV2(req)
                  const agree = v1?.prediction != null && v2?.prediction != null
                    ? v1.prediction === v2.prediction : null
                  return (
                    <tr key={req.id} onClick={() => setSelected(selected?.id === req.id ? null : req)}
                      style={{ cursor: 'pointer', background: selected?.id === req.id ? 'var(--bg-elevated)' : '' }}>
                      <td><span className="font-mono text-xs" style={{ color: 'var(--accent-primary)' }}>{req.id.slice(0,8)}…</span></td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{format(new Date(req.created_at), 'MM/dd HH:mm:ss')}</td>
                      <td>
                        <span className={`badge ${req.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                          {req.status}
                        </span>
                      </td>
                      <td>
                        {v1?.is_error
                          ? <span className="badge badge-danger">ERR</span>
                          : <span className="font-mono">{v1?.prediction ?? '—'}</span>}
                      </td>
                      <td>
                        {v2?.is_error
                          ? <span className="badge badge-danger">ERR</span>
                          : <span className="font-mono">{v2?.prediction ?? '—'}</span>}
                      </td>
                      <td className="font-mono text-xs">{v1?.latency_ms?.toFixed(1) ?? '—'} ms</td>
                      <td className="font-mono text-xs">{v2?.latency_ms?.toFixed(1) ?? '—'} ms</td>
                      <td>{req.true_label != null ? <span className="badge badge-info">{req.true_label}</span> : <span style={{ color: 'var(--text-muted)' }}>—</span>}</td>
                      <td>
                        {agree === null ? <span style={{ color: 'var(--text-muted)' }}>—</span>
                          : agree
                            ? <span className="badge badge-success">✓ Yes</span>
                            : <span className="badge badge-danger">✗ No</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between" style={{ padding: '12px 20px', borderTop: '1px solid var(--border)' }}>
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Page {page + 1}</span>
            <div className="flex gap-2">
              <button className="btn btn-ghost" style={{ padding: '6px 12px' }} disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={14} />
              </button>
              <button className="btn btn-ghost" style={{ padding: '6px 12px' }} disabled={requests.length < PAGE_SIZE} onClick={() => setPage(p => p + 1)}>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="card fade-in" style={{ height: 'fit-content', position: 'sticky', top: 20 }}>
            <div className="section-title"><FileText size={14} /> Request Detail</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              <span className="font-mono" style={{ color: 'var(--accent-primary)' }}>{selected.id}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                ['Status', selected.status],
                ['Timestamp', format(new Date(selected.created_at), 'yyyy-MM-dd HH:mm:ss')],
                ['True Label', selected.true_label ?? 'Not provided'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 6 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{k}</span>
                  <span className="font-mono">{String(v)}</span>
                </div>
              ))}
            </div>
            {selected.predictions?.map(p => (
              <div key={p.id} style={{ marginTop: 16, padding: 12, background: 'var(--bg-elevated)', borderRadius: 8, border: `1px solid ${p.is_error ? 'var(--accent-danger)' : 'var(--border)'}` }}>
                <div style={{ fontWeight: 700, marginBottom: 8, color: p.model_version === 'v1' ? 'var(--accent-success)' : 'var(--accent-secondary)' }}>
                  Model {p.model_version.toUpperCase()}
                </div>
                <div style={{ fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span>Prediction: <b className="font-mono">{p.is_error ? 'ERROR' : p.prediction}</b></span>
                  <span>Probability: <b className="font-mono">{p.probability?.toFixed(4) ?? '—'}</b></span>
                  <span>Latency: <b className="font-mono">{p.latency_ms?.toFixed(2)} ms</b></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
