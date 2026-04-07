import { useState } from 'react'
import { Zap, CheckCircle, AlertCircle, TrendingUp, Loader, ChevronDown } from 'lucide-react'
import toast from 'react-hot-toast'
import '../styles/ModelEvaluation.css'

export default function ModelEvaluation({ onEvaluationComplete }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [expanded, setExpanded] = useState(false)

  const triggerEvaluation = async () => {
    setLoading(true)
    console.log('[EVAL_START] Beginning model evaluation request')
    
    try {
      console.log('[EVAL_REQUEST] Sending POST to /api/v1/evaluate-models')
      const response = await fetch('/api/v1/evaluate-models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      
      console.log(`[EVAL_RESPONSE] Status: ${response.status}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`[EVAL_ERROR] HTTP ${response.status} response:`, errorText)
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
      
      const data = await response.json()
      console.log('[EVAL_SUCCESS] Evaluation completed:', data)
      setResult(data)
      setExpanded(true)
      
      if (data.decision === 'PROMOTE_MODEL_V2') {
        toast.success('M2 is better! Ready for promotion 🚀', {
          duration: 4000,
          icon: '✅',
        })
      } else {
        toast.info('M1 still performing better', {
          duration: 4000,
          icon: 'ℹ️',
        })
      }
      
      onEvaluationComplete?.(data)
    } catch (error) {
      const errorMsg = error.message || 'Unknown error occurred'
      console.error('[EVAL_FAILED] Evaluation error:', error)
      console.error('[EVAL_FAILED_MESSAGE]', errorMsg)
      toast.error(`Evaluation failed: ${errorMsg}`)
    } finally {
      setLoading(false)
      console.log('[EVAL_END] Evaluation request completed')
    }
  }

  return (
    <div className="model-evaluation-card">
      <div className="eval-header">
        <div>
          <h3>Model Evaluation</h3>
          <p>Compare M1 (Production) vs M2 (Shadow)</p>
        </div>
        <button
          className="btn btn-primary eval-button"
          onClick={triggerEvaluation}
          disabled={loading}
        >
          {loading ? (
            <>
              <Loader size={14} className="spin-anim" />
              Evaluating...
            </>
          ) : (
            <>
              <Zap size={14} />
              Evaluate
            </>
          )}
        </button>
      </div>

      {result && (
        <div className="eval-result-container">
          {/* Decision Badge */}
          <div className={`decision-badge ${result.decision === 'PROMOTE_MODEL_V2' ? 'promote' : 'keep'}`}>
            {result.decision === 'PROMOTE_MODEL_V2' ? (
              <>
                <CheckCircle size={20} />
                <div>
                  <strong>🟢 Shadow Model is Better</strong>
                  <p>Ready for Promotion</p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle size={20} />
                <div>
                  <strong>🔴 Production Model Still Better</strong>
                  <p>Keep Current Model</p>
                </div>
              </>
            )}
            <div className="confidence-score">
              Confidence: <strong>{(result.confidence_score * 100).toFixed(0)}%</strong>
            </div>
          </div>

          {/* Metrics Comparison Table */}
          <div className="metrics-comparison">
            <h4>Metrics Comparison</h4>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Production (V1)</th>
                  <th>Shadow (V2)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {result.metrics.v1_accuracy !== null && (
                  <tr>
                    <td>Accuracy</td>
                    <td>{(result.metrics.v1_accuracy * 100).toFixed(2)}%</td>
                    <td>{(result.metrics.v2_accuracy * 100).toFixed(2)}%</td>
                    <td>
                      {result.metrics.v2_accuracy > result.metrics.v1_accuracy ? (
                        <span className="badge badge-success">✓ V2 Better</span>
                      ) : (
                        <span className="badge badge-neutral">- V1 Same</span>
                      )}
                    </td>
                  </tr>
                )}
                <tr>
                  <td>Avg Latency</td>
                  <td>{result.metrics.latency_v1.toFixed(2)} ms</td>
                  <td>{result.metrics.latency_v2.toFixed(2)} ms</td>
                  <td>
                    {result.metrics.latency_v2 <= result.metrics.latency_v1 * 1.2 ? (
                      <span className="badge badge-success">✓ Within Threshold</span>
                    ) : (
                      <span className="badge badge-danger">✗ Too Slow</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td>Error Rate</td>
                  <td>{(result.metrics.error_rate * 100).toFixed(2)}%</td>
                  <td>—</td>
                  <td>
                    {result.metrics.error_rate < 0.05 ? (
                      <span className="badge badge-success">✓ Acceptable</span>
                    ) : (
                      <span className="badge badge-danger">✗ High</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td>Model Agreement</td>
                  <td colSpan="2" className="text-center">
                    <strong>{(result.metrics.agreement_rate * 100).toFixed(1)}%</strong>
                  </td>
                  <td>—</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Reasoning */}
          <div className="reasoning-section" style={{ cursor: 'pointer' }} onClick={() => setExpanded(!expanded)}>
            <div className="reasoning-header">
              <h4>Decision Reasoning</h4>
              <ChevronDown
                size={18}
                style={{
                  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                }}
              />
            </div>
            {expanded && (
              <ul className="reasoning-list">
                {result.reasoning.map((reason, idx) => (
                  <li key={idx} className="reasoning-item">
                    {reason.includes('[PASS]') && <span className="reason-icon success">✓</span>}
                    {reason.includes('[FAIL]') && <span className="reason-icon error">✗</span>}
                    {reason.includes('[WARN]') && <span className="reason-icon warning">⚠</span>}
                    {reason.includes('[INFO]') && <span className="reason-icon info">ℹ</span>}
                    {reason}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Recommended Action */}
          <div className="recommended-action">
            <TrendingUp size={16} />
            <span>{result.recommended_action}</span>
          </div>

          {/* Sample Count */}
          <div className="eval-metadata">
            <small>Evaluated {result.sample_count} samples at {new Date(result.evaluation_timestamp).toLocaleTimeString()}</small>
          </div>

          {/* Promotion Button (if recommended) */}
          {result.decision === 'PROMOTE_MODEL_V2' && (
            <div className="promotion-action">
              <button className="btn btn-success">
                <Zap size={14} />
                Promote Shadow Model to Production
              </button>
              <p className="promotion-note">
                ⚠️ This action will promote V2 to production. Ensure team approval before proceeding.
              </p>
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="placeholder">
          <Zap size={32} opacity={0.5} />
          <p>Click &quot;Evaluate Models&quot; to compare production and shadow models</p>
        </div>
      )}
    </div>
  )
}
