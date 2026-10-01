import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Search, Eye, Trash2, FileText, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { StatusPill } from '../components/CostCard';
import { listEstimates, deleteEstimate, finalizeEstimate } from '../services/api';

const DEMO = [
  { id: 1, estimate_number: 'EST-00001', customer_name: 'Luxe Beauty Pvt Ltd', job_name: 'Premium Rigid Box', order_quantity: 1000, cost_per_box: 18.42, order_value: 22100, status: 'Finalized', created_at: '24 Sep 2026' },
  { id: 2, estimate_number: 'EST-00002', customer_name: 'Aura Skincare',        job_name: 'Gift Box',           order_quantity: 2000, cost_per_box: 21.36, order_value: 42700, status: 'Draft',     created_at: '23 Sep 2026' },
  { id: 3, estimate_number: 'EST-00003', customer_name: 'Veda Naturals',        job_name: 'Cosmetic Box',       order_quantity: 500,  cost_per_box: 16.80, order_value: 9800,  status: 'Quoted',    created_at: '22 Sep 2026' },
  { id: 4, estimate_number: 'EST-00004', customer_name: 'Elite Brands',         job_name: 'Luxury Box',         order_quantity: 1500, cost_per_box: 19.25, order_value: 28875, status: 'Finalized', created_at: '21 Sep 2026' },
];

export default function Estimates() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [rows,          setRows]          = useState([]);
  const [loading,       setLoading]       = useState(true);
  const [offline,       setOffline]       = useState(false);
  const [search,        setSearch]        = useState(() => searchParams.get('q') || '');
  const [statusFilter,  setStatusFilter]  = useState('All Status');
  const [customerFilter,setCustomerFilter]= useState('All Customers');
  const [toast,         setToast]         = useState(null);

  const showToast = (msg, isErr = false) => {
    setToast({ msg, isErr });
    setTimeout(() => setToast(null), 3500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listEstimates();
      setRows(data);
      setOffline(false);
    } catch {
      setRows(DEMO);
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setSearch(searchParams.get('q') || ''); }, [searchParams]);

  const handleDelete = async (e, row) => {
    e.stopPropagation();
    if (!window.confirm(`Delete ${row.estimate_number}? This cannot be undone.`)) return;
    if (offline) { showToast('Backend offline — cannot delete', true); return; }
    try {
      await deleteEstimate(row.id);
      showToast(`${row.estimate_number} deleted`);
      load();
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleFinalize = async (e, row) => {
    e.stopPropagation();
    if (offline) { showToast('Backend offline', true); return; }
    try {
      await finalizeEstimate(row.id);
      showToast(`${row.estimate_number} finalized`);
      load();
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const customers = [...new Set(rows.map(r => r.customer_name).filter(Boolean))];

  const filtered = rows.filter(r => {
    const q = search.toLowerCase();
    const matchSearch   = !q || r.customer_name?.toLowerCase().includes(q) ||
      r.job_name?.toLowerCase().includes(q) || r.estimate_number?.toLowerCase().includes(q);
    const matchStatus   = statusFilter   === 'All Status'    || r.status        === statusFilter;
    const matchCustomer = customerFilter === 'All Customers' || r.customer_name === customerFilter;
    return matchSearch && matchStatus && matchCustomer;
  });

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Estimates</span>
          <h1 style={{ marginTop: 4 }}>Estimates</h1>
          <p>View and manage all cost estimates</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={load} disabled={loading} title="Refresh">
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/estimator/new')}>
            <Plus size={15} /> New Estimate
          </button>
        </div>
      </div>

      {offline && (
        <div className="warn-banner" style={{ marginBottom: 16 }}>
          <AlertCircle size={15} />
          <span>Backend offline — showing demo data. Start the FastAPI server on port 8000 to use live data.</span>
        </div>
      )}

      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Filter row */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 200, maxWidth: 300 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }}
              placeholder="Search estimates..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <select className="form-select" style={{ height: 36, width: 170, fontSize: 12 }}
            value={customerFilter} onChange={e => setCustomerFilter(e.target.value)}>
            <option>All Customers</option>
            {customers.map(c => <option key={c}>{c}</option>)}
          </select>
          <select className="form-select" style={{ height: 36, width: 130, fontSize: 12 }}
            value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option>All Status</option>
            <option>Draft</option>
            <option>Quoted</option>
            <option>Finalized</option>
          </select>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>
            {loading ? 'Loading…' : `Showing ${filtered.length} of ${rows.length}`}
          </div>
        </div>

        {/* Table */}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Customer</th>
                <th>Product / Job</th>
                <th style={{ textAlign: 'right' }}>Order Qty</th>
                <th style={{ textAlign: 'right' }}>Cost/Box</th>
                <th style={{ textAlign: 'right' }}>Total Value</th>
                <th>Status</th>
                <th>Date</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id} style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/estimates/${r.id}`)}>
                  <td style={{ fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)', fontSize: 11 }}>
                    {r.estimate_number}
                  </td>
                  <td><strong style={{ fontSize: 12 }}>{r.customer_name}</strong></td>
                  <td style={{ fontSize: 12 }}>{r.job_name}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>
                    {Number(r.order_quantity || 0).toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700, color: 'var(--ink-2)' }}>
                    ₹ {Number(r.cost_per_box || 0).toFixed(2)}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700 }}>
                    ₹ {Number(r.order_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td><StatusPill status={r.status} /></td>
                  <td style={{ fontSize: 11, color: 'var(--muted-2)' }}>{r.created_at}</td>
                  <td onClick={ev => ev.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                      <button className="btn btn-ghost btn-sm btn-icon" title="View detail"
                        onClick={e => { e.stopPropagation(); navigate(`/estimates/${r.id}`); }}>
                        <Eye size={13} />
                      </button>
                      {r.status !== 'Finalized' && (
                        <button className="btn btn-ghost btn-sm btn-icon" title="Finalize"
                          style={{ color: 'var(--orange)' }}
                          onClick={e => handleFinalize(e, r)}>
                          <CheckCircle2 size={13} />
                        </button>
                      )}
                      {r.status !== 'Finalized' && (
                        <button className="btn btn-ghost btn-sm btn-icon" title="Delete"
                          style={{ color: '#E53E3E' }}
                          onClick={e => handleDelete(e, r)}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)', fontSize: 13 }}>
                    No estimates found.{' '}
                    <button className="btn btn-ghost btn-sm"
                      onClick={() => navigate('/estimator/new')}
                      style={{ color: 'var(--orange)' }}>
                      Create the first estimate →
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)', fontSize: 12, color: 'var(--muted-2)', display: 'flex', justifyContent: 'space-between' }}>
          <span>{filtered.length} estimate{filtered.length !== 1 ? 's' : ''}</span>
          {offline && <span style={{ color: '#D97706' }}>⚠ Demo mode</span>}
        </div>
      </div>

      {toast && (
        <div className="toast" style={{ background: toast.isErr ? '#C53030' : 'var(--ink-2)' }}>
          {toast.isErr
            ? <AlertCircle size={14} style={{ color: '#FCA5A5' }} />
            : <CheckCircle2 size={14} style={{ color: '#72D38D' }} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
}
