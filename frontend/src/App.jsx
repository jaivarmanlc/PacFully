import React, { useCallback, useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import { StatusPill, money } from './components/CostCard.jsx';
import { getEstimate } from './services/api.js';

// Auth
import { AuthProvider, useAuth } from './context/AuthContext.jsx';

// Layout
import Sidebar from './components/Sidebar.jsx';
import Navbar  from './components/Navbar.jsx';

// Public pages
import Home  from './pages/Home.jsx';
import Login from './pages/Login.jsx';

// App pages
import Dashboard     from './pages/Dashboard.jsx';
import CostEstimator from './pages/CostEstimator.jsx';
import Estimates     from './pages/Estimates.jsx';
import Customers     from './pages/Customers.jsx';
import Reports       from './pages/Reports.jsx';
import MasterConfig  from './pages/MasterConfig.jsx';
import Quotations    from './pages/Quotations.jsx';
import Proforma      from './pages/Proforma.jsx';
import Settings      from './pages/Settings.jsx';
import Users         from './pages/Users.jsx';
import AuditLog      from './pages/AuditLog.jsx';

// ── Protected route wrapper ──────────────────────────────────
// Redirects to /login if user is not authenticated.
function RequireAuth({ children }) {
  const { isLoggedIn } = useAuth();
  const location       = useLocation();

  if (!isLoggedIn) {
    // Preserve the URL they tried to visit so we can redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

// ── Public layout (no sidebar) ───────────────────────────────
function PublicLayout({ children }) {
  return <>{children}</>;
}

// ── App layout (sidebar + topbar) — only for authenticated users
function AppLayout({ children }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      {mobileNavOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      <div className="main-content">
        <Navbar onMenuClick={() => setMobileNavOpen(value => !value)} />
        {children}
      </div>
    </div>
  );
}

// ── Convenience wrapper: protected + app layout ──────────────
function AppPage({ children }) {
  return (
    <RequireAuth>
      <AppLayout>{children}</AppLayout>
    </RequireAuth>
  );
}

const SNAPSHOT_GROUPS = [
  { title: 'Order', keys: ['quantity', 'margin_percent'] },
  { title: 'Kappa Board', keys: ['kappa_material', 'kappa_thickness_mm', 'kappa_gsm_at_1mm', 'kappa_sheet_length_mm', 'kappa_sheet_width_mm', 'kappa_ups', 'kappa_wastage_percent', 'kappa_master_rate', 'kappa_override_rate'] },
  { title: 'Wrapper', keys: ['wrapper_gsm', 'wrapper_ups', 'wrapper_sheet_length_mm', 'wrapper_sheet_width_mm', 'wrapper_wastage_percent', 'wrapper_make_ready_sheets', 'wrapper_master_rate', 'wrapper_override_rate'] },
  { title: 'Printing', keys: ['print_sheet_size', 'print_master_rate', 'print_additional_rate', 'print_override_rate'] },
  { title: 'Lamination', keys: ['lamination_type', 'lamination_sheet_length_in', 'lamination_sheet_width_in', 'lam_master_rate', 'lam_override_rate'] },
  { title: 'Glue', keys: ['glue_lines'] },
  { title: 'Punching', keys: ['punching_material', 'punching_machine_rate_per_hour', 'punching_speed', 'punching_setup_hours'] },
  { title: 'Embellishments', keys: ['embellishment_type', 'embellishment_area_sq_in', 'embellishment_rate_per_sq_in', 'embellishment_setup', 'embellishment_minimum'] },
  { title: 'Accessories', keys: ['accessories'] },
  { title: 'Conversion and EB', keys: ['conversion_machine_rate', 'conversion_machine_hours', 'conversion_labour_rate', 'conversion_labour_hours', 'conversion_setup', 'eb_method', 'eb_value'] },
];

function snapshotLabel(key) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

function snapshotValue(key, value) {
  if (value === null || value === undefined || value === '') return 'Not set';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    if (key.includes('percent')) return `${value}%`;
    if (key.includes('rate') || key.includes('cost') || key.includes('setup') || key === 'eb_value') return money(value);
    return value.toLocaleString();
  }
  return String(value);
}

function SnapshotGroup({ title, keys, snapshot }) {
  const fields = keys.filter(key => Object.hasOwn(snapshot, key));
  if (!fields.length) return null;
  return (
    <section className="panel" style={{ marginBottom: 0 }}>
      <h3 className="panel-title" style={{ marginBottom: 12 }}>{title}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px 20px' }}>
        {fields.map(key => (
          <div key={key} style={{ minWidth: 0 }}>
            <div className="form-label">{snapshotLabel(key)}</div>
            {Array.isArray(snapshot[key]) ? (
              <div style={{ display: 'grid', gap: 6, marginTop: 5 }}>
                {snapshot[key].map((item, index) => (
                  <div key={`${key}-${index}`} style={{ borderTop: '1px solid var(--line-2)', paddingTop: 6, fontSize: 12 }}>
                    {Object.entries(item).map(([itemKey, itemValue]) => (
                      <div key={itemKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <span style={{ color: 'var(--muted)' }}>{snapshotLabel(itemKey)}</span>
                        <strong style={{ textAlign: 'right' }}>{snapshotValue(itemKey, itemValue)}</strong>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : <strong style={{ display: 'block', marginTop: 4, fontSize: 13, overflowWrap: 'anywhere' }}>{snapshotValue(key, snapshot[key])}</strong>}
          </div>
        ))}
      </div>
    </section>
  );
}

function EstimateDetail() {
  const { id } = useParams();
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setEstimate(await getEstimate(id));
    } catch (err) {
      setEstimate(null);
      setError(err.message || 'Unable to load this estimate');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load, reloadKey]);

  if (loading) return <div className="page-content"><div className="panel">Loading estimate details...</div></div>;
  if (error) return (
    <div className="page-content">
      <div className="warn-banner"><AlertCircle size={15} /><span>{error}</span></div>
      <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setReloadKey(key => key + 1)}><RefreshCw size={14} /> Retry</button>
    </div>
  );

  const snapshot = estimate.input_snapshot || {};
  const formatTimestamp = value => value ? new Date(value).toLocaleString() : '—';

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Estimates › Detail</span>
          <h1 style={{ marginTop: 4 }}>{estimate.estimate_number}</h1>
          <p>{estimate.customer_name} · {estimate.job_name}</p>
        </div>
        <div className="page-header-right" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusPill status={estimate.status} />
          <button className="btn btn-secondary btn-sm" onClick={() => setReloadKey(key => key + 1)} title="Refresh estimate"><RefreshCw size={14} /></button>
          <button className="btn btn-secondary btn-sm" onClick={() => window.history.back()}><ArrowLeft size={14} /> Back</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12, marginBottom: 16 }}>
        {[
          ['Order Quantity', Number(estimate.order_quantity || 0).toLocaleString()],
          ['Manufacturing Cost', money(estimate.total_manufacturing_cost)],
          ['Cost per Box', money(estimate.cost_per_box)],
          ['Margin', `${Number(estimate.margin_percent || 0).toFixed(2)}%`],
          ['Selling Price / Box', money(estimate.selling_price_per_box)],
          ['Order Value', money(estimate.order_value)],
        ].map(([label, value]) => (
          <div className="panel" key={label} style={{ padding: 16 }}>
            <div className="form-label">{label}</div>
            <strong style={{ display: 'block', marginTop: 6, fontFamily: 'Manrope', fontSize: 17 }}>{value}</strong>
          </div>
        ))}
      </div>

      <section className="panel" style={{ padding: 0, overflow: 'hidden', marginBottom: 16 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)' }}>
          <h2 className="panel-title">Module Cost Breakdown</h2>
          <p className="panel-sub">Saved calculation lines and their calculation traces</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Module</th><th style={{ textAlign: 'right' }}>Total Cost</th><th style={{ textAlign: 'right' }}>Cost / Box</th><th style={{ textAlign: 'right' }}>Weightage</th><th>Status</th><th>Calculation Trace</th></tr></thead>
            <tbody>
              {(estimate.cost_lines || []).map(line => (
                <tr key={line.module}>
                  <td><strong>{line.module}</strong></td>
                  <td style={{ textAlign: 'right' }}>{money(line.total_cost)}</td>
                  <td style={{ textAlign: 'right' }}>{money(line.cost_per_box)}</td>
                  <td style={{ textAlign: 'right' }}>{Number(line.weightage_percent || 0).toFixed(1)}%</td>
                  <td><StatusPill status={line.status || 'OK'} /></td>
                  <td>
                    {line.trace?.length ? <details>
                      <summary style={{ cursor: 'pointer', color: 'var(--orange)', fontSize: 12 }}>View trace</summary>
                      <div style={{ minWidth: 230, paddingTop: 8 }}>
                        {line.trace.map((item, index) => (
                          <div key={`${line.module}-${index}`} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 11, padding: '3px 0' }}>
                            <span style={{ color: 'var(--muted)' }}>{item.label}</span><strong style={{ textAlign: 'right' }}>{item.value}</strong>
                          </div>
                        ))}
                      </div>
                    </details> : '—'}
                  </td>
                </tr>
              ))}
              {!estimate.cost_lines?.length && <tr><td colSpan={6} style={{ textAlign: 'center', padding: 24, color: 'var(--muted)' }}>No module cost lines were saved with this estimate.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, marginBottom: 10 }}>Input Snapshot</h2>
        <div style={{ display: 'grid', gap: 12 }}>
          {SNAPSHOT_GROUPS.map(group => <SnapshotGroup key={group.title} {...group} snapshot={snapshot} />)}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title" style={{ marginBottom: 12 }}>Document History</h2>
        {(estimate.quotations || []).length ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {estimate.quotations.map(quotation => (
              <div key={quotation.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderTop: '1px solid var(--line-2)', paddingTop: 8, fontSize: 12 }}>
                <div><strong>{quotation.quotation_number}</strong><span style={{ marginLeft: 8, color: 'var(--muted)' }}>{quotation.doc_type}</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><StatusPill status={quotation.status} /><strong>{money(quotation.grand_total)}</strong><span style={{ color: 'var(--muted-2)' }}>{formatTimestamp(quotation.created_at)}</span></div>
              </div>
            ))}
          </div>
        ) : <p style={{ fontSize: 12, color: 'var(--muted)' }}>No quotations or proforma invoices are linked to this estimate yet.</p>}
        <div style={{ marginTop: 12, fontSize: 11, color: 'var(--muted-2)' }}>
          Created {formatTimestamp(estimate.created_at)}{estimate.finalized_at ? ` · Finalized ${formatTimestamp(estimate.finalized_at)}` : ''}
        </div>
      </section>
    </div>
  );
}

function CustomerDetail() {
  const id = useLocation().pathname.split('/').pop();
  return (
    <div className="page-content">
      <span className="eyebrow">Customers › Profile</span>
      <h1 style={{ marginTop: 4 }}>Customer Profile</h1>
      <div className="panel" style={{ marginTop: 16 }}>
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--muted-2)', fontSize: 13 }}>
          Customer {id} — history, contacts and estimate list.
        </div>
      </div>
    </div>
  );
}

// ── Root App ─────────────────────────────────────────────────
// AuthProvider wraps everything so Login can call login() and
// protected routes can call isLoggedIn — both need BrowserRouter
// context from main.jsx.
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* ── Public ── */}
        <Route path="/"      element={<PublicLayout><Home /></PublicLayout>} />
        <Route path="/login" element={<PublicLayout><Login /></PublicLayout>} />

        {/* ── Protected app pages ── */}
        <Route path="/dashboard"     element={<AppPage><Dashboard /></AppPage>} />
        <Route path="/estimator/*"   element={<AppPage><CostEstimator /></AppPage>} />
        <Route path="/estimates"     element={<AppPage><Estimates /></AppPage>} />
        <Route path="/estimates/:id" element={<AppPage><EstimateDetail /></AppPage>} />
        <Route path="/customers"     element={<AppPage><Customers /></AppPage>} />
        <Route path="/customers/:id" element={<AppPage><CustomerDetail /></AppPage>} />
        <Route path="/reports"       element={<AppPage><Reports /></AppPage>} />
        <Route path="/master-config" element={<AppPage><MasterConfig /></AppPage>} />
        <Route path="/quotations"    element={<AppPage><Quotations /></AppPage>} />
        <Route path="/proforma"      element={<AppPage><Proforma /></AppPage>} />
        <Route path="/settings"      element={<AppPage><Settings /></AppPage>} />
        <Route path="/users"         element={<AppPage><Users /></AppPage>} />
        <Route path="/audit-log"     element={<AppPage><AuditLog /></AppPage>} />

        {/* ── Catch-all ── */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
