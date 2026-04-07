import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Activity, BarChart3, FileText, AlertTriangle, Zap } from 'lucide-react'
import Overview from './pages/Overview.jsx'
import ModelComparison from './pages/ModelComparison.jsx'
import RequestLogs from './pages/RequestLogs.jsx'
import ErrorMonitor from './pages/ErrorMonitor.jsx'
import './App.css'

const NAV = [
  { to: '/',           label: 'Overview',    Icon: Activity    },
  { to: '/compare',   label: 'Model Compare', Icon: BarChart3  },
  { to: '/logs',      label: 'Request Logs', Icon: FileText    },
  { to: '/errors',    label: 'Errors',       Icon: AlertTriangle },
]

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ style: { background: '#1e2a3d', color: '#f1f5f9', border: '1px solid #2a3a55' } }} />
      <div className="app-layout">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-logo">
            <Zap size={22} className="logo-icon" />
            <span>Shadow<b>ML</b></span>
          </div>
          <nav className="sidebar-nav">
            {NAV.map(({ to, label, Icon }) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-footer">
            <div className="live-dot" />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Live Shadow Mode</span>
          </div>
        </aside>

        {/* ── Main ── */}
        <main className="main-content">
          <Routes>
            <Route path="/"        element={<Overview />} />
            <Route path="/compare" element={<ModelComparison />} />
            <Route path="/logs"    element={<RequestLogs />} />
            <Route path="/errors"  element={<ErrorMonitor />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
