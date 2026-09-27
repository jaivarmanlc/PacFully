import React, { useState, useEffect, useCallback } from 'react';
import { Search, Download, RefreshCw, AlertCircle } from 'lucide-react';
import { getAuditLog } from '../services/api';

const DEMO = [
  { id: 1, user: 'Jaya Varma',   action: 'Estimate Finalized',    entity_type: 'estimate',   entity_id: 'EST-00001', detail: 'Premium Rigid Box — Luxe Beauty Pvt Ltd', timestamp: '25 Sep 2026, 14:32' },
  { id: 2, user: 'Arjun Kapoor', action: 'Quotation Generated',   entity_type: 'quotation',  entity_id: 'QUO-2026-09-0001', detail: 'Luxe Beauty Pvt Ltd — Grand Total ₹27,175', timestamp: '24 Sep 2026, 10:48' },
  { id: 3, user: 'Jaya Varma',   action: 'Estimate Created',      entity_type: 'estimate',   entity_id: 'EST-00002', detail: 'Gift Box — Aura Skincare — Qty 2000', timestamp: '23 Sep 2026, 16:22' },
  { id: 4, user: 'Admin',        action: 'Customer Created',      entity_type: 'customer',   entity_id: '1', detail: 'New customer: Luxe Beauty Pvt Ltd', timestamp: '22 Sep 2026, 09:00' },
];

const TYPE_STYLE = {
  estimate:  { bg: '#EAF3FF', color: '#2563EB' },
  quotation: { bg: '#E8F8ED', color: '#2D7A4F' },
  customer:  { bg: '#FFF1ED', color: '#FF5A3A' },
  config:    { bg: '#FFF3DC', color: '#B47A20' },
  override:  { bg: '#FFF1ED', color: '#FF5A3A' },
  admin:     { bg: '#F0ECFF', color: '#7C3AED' },
  ai:        { bg: '#E8F8ED', color: '#2D7A4F' },
};

export default function AuditLog() {
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [search,  setSearch]  = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAuditLog();
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

  const filtered = rows.filter(r =>
    !search ||
    r.action?.toLowerCase().includes(search.toLowerCase()) ||
    r.user?.toLowerCase().includes(search.toLowerCase()) ||
    r.entity_id?.toLowerCase().includes(search.toLowerCase()) ||
    r.detail?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Audit Log</span>
          <h1 style={{ marginTop: 4 }}>Audit Log</h1>
          <p>Complete immutable history of all system events</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={load}><RefreshCw size={14} /></button>
          <button className="btn btn-secondary"><Download size={14} /> Export</button>
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
          <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }}
              placeholder="Search events, users, entities…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>
            {loading ? 'Loading…' : `${filtered.length} events`}
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Detail</th>
                <th>Timestamp</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(e => {
                const tc = TYPE_STYLE[e.entity_type] || TYPE_STYLE.admin;
                return (
                  <tr key={e.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="avatar sm">
                          {(e.user || '?').split(' ').map(n => n[0]).join('').slice(0, 2)}
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 500 }}>{e.user}</span>
                      </div>
                    </td>
                    <td><strong style={{ fontSize: 12 }}>{e.action}</strong></td>
                    <td>
                      <span style={{ fontFamily: 'Manrope', fontWeight: 700, fontSize: 11, color: 'var(--orange)' }}>
                        {e.entity_id}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--muted)', maxWidth: 320 }}>{e.detail}</td>
                    <td style={{ fontSize: 11, color: 'var(--muted-2)', whiteSpace: 'nowrap' }}>{e.timestamp}</td>
                    <td>
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 99, background: tc.bg, color: tc.color, whiteSpace: 'nowrap' }}>
                        {(e.entity_type || 'system').toUpperCase()}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)', fontSize: 13 }}>
                    No audit events yet. Activity will appear here once estimates are created.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--muted-2)' }}>
          <span>{filtered.length} event{filtered.length !== 1 ? 's' : ''}</span>
          <span>Audit trail is append-only and immutable</span>
        </div>
      </div>
    </div>
  );
}
