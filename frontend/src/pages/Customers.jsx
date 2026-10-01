import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Search, MapPin, ChevronRight, RefreshCw, AlertCircle, CheckCircle2, X, Trash2 } from 'lucide-react';
import { listCustomers, createCustomer, deleteCustomer } from '../services/api';

const DEMO = [
  { id: 1, name: 'Luxe Beauty Pvt Ltd', contact: 'Priya Menon',  email: 'priya@luxebeauty.in',   phone: '+91 98400 12345', city: 'Chennai',   estimate_count: 4 },
  { id: 2, name: 'Aura Skincare',       contact: 'Rahul Sharma', email: 'rahul@auraskincare.com', phone: '+91 99876 54321', city: 'Mumbai',    estimate_count: 3 },
  { id: 3, name: 'Veda Naturals',       contact: 'Anita Bose',   email: 'anita@vedanaturals.com', phone: '+91 97654 32109', city: 'Bengaluru', estimate_count: 2 },
  { id: 4, name: 'Elite Brands',        contact: 'Suresh Kumar', email: 'suresh@elitebrands.in',  phone: '+91 96543 21098', city: 'Hyderabad', estimate_count: 5 },
];

function AddModal({ onClose, onSaved }) {
  const EMPTY = { name: '', contact: '', email: '', phone: '', city: '', state: '', address: '', gst_number: '' };
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = async () => {
    if (!form.name.trim()) { setErr('Customer name is required'); return; }
    setSaving(true);
    try {
      await createCustomer(form);
      onSaved();
    } catch (e) {
      setErr(e.message);
      setSaving(false);
    }
  };

  const FIELDS = [
    ['name', 'Company Name *', true], ['contact', 'Contact Person'],
    ['email', 'Email'], ['phone', 'Phone'],
    ['city', 'City'], ['state', 'State'], ['gst_number', 'GST Number'],
  ];

  return (
    <div className="modal-backdrop">
      <div className="modal" style={{ width: 520 }}>
        <div className="modal-header">
          <div>
            <span className="eyebrow">New Customer</span>
            <h2>Add Customer</h2>
            <p>Fill in the company details to create a new customer record.</p>
          </div>
          <button className="modal-close" onClick={onClose}><X size={16} /></button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {FIELDS.map(([k, label, full]) => (
            <div className="form-group" key={k} style={full ? { gridColumn: '1 / -1' } : {}}>
              <label className="form-label">{label}</label>
              <input className="form-input" value={form[k]} onChange={e => set(k, e.target.value)} />
            </div>
          ))}
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="form-label">Address</label>
            <textarea className="form-input" style={{ height: 64, paddingTop: 8, resize: 'vertical' }}
              value={form.address} onChange={e => set('address', e.target.value)} />
          </div>
        </div>
        {err && (
          <div style={{ color: '#C53030', fontSize: 12, marginTop: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertCircle size={13} /> {err}
          </div>
        )}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Add Customer'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Customers() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [search,  setSearch]  = useState(() => searchParams.get('q') || '');
  const [showAdd, setShowAdd] = useState(false);
  const [toast,   setToast]   = useState(null);

  const showToast = (msg, isErr = false) => {
    setToast({ msg, isErr });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCustomers();
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
    if (!window.confirm(`Deactivate "${row.name}"?`)) return;
    try {
      await deleteCustomer(row.id);
      showToast(`${row.name} deactivated`);
      load();
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const filtered = rows.filter(r =>
    !search ||
    r.name?.toLowerCase().includes(search.toLowerCase()) ||
    r.city?.toLowerCase().includes(search.toLowerCase()) ||
    r.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Customers</span>
          <h1 style={{ marginTop: 4 }}>Customers</h1>
          <p>Manage your B2B packaging customers</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={load} title="Refresh">
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={15} /> Add Customer
          </button>
        </div>
      </div>

      {offline && (
        <div className="warn-banner" style={{ marginBottom: 16 }}>
          <AlertCircle size={15} />
          <span>Backend offline — showing demo data.</span>
        </div>
      )}

      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 300 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }}
              placeholder="Search customers…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>
            {loading ? 'Loading…' : `${filtered.length} customers`}
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Contact</th>
              <th>Location</th>
              <th style={{ textAlign: 'right' }}>Estimates</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => (
              <tr key={c.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/customers/${c.id}`)}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="avatar orange" style={{ width: 34, height: 34, fontSize: 12 }}>
                      {(c.name || '?').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{c.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>{c.email}</div>
                    </div>
                  </div>
                </td>
                <td style={{ fontSize: 12 }}>{c.contact}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                    <MapPin size={11} style={{ color: 'var(--muted-2)' }} />
                    {c.city}
                  </div>
                </td>
                <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>
                  {c.estimate_count ?? 0}
                </td>
                <td onClick={e => e.stopPropagation()}>
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                    <button className="btn btn-ghost btn-sm btn-icon" title="View profile"
                      onClick={e => { e.stopPropagation(); navigate(`/customers/${c.id}`); }}>
                      <ChevronRight size={14} />
                    </button>
                    {!offline && (
                      <button className="btn btn-ghost btn-sm btn-icon" title="Deactivate"
                        style={{ color: '#E53E3E' }}
                        onClick={e => handleDelete(e, c)}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)', fontSize: 13 }}>
                  No customers yet.{' '}
                  <button className="btn btn-ghost btn-sm" onClick={() => setShowAdd(true)} style={{ color: 'var(--orange)' }}>
                    Add one →
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <AddModal
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); load(); showToast('Customer added successfully'); }}
        />
      )}

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
