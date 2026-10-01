import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Plus, Search, Download, Eye, RefreshCw, AlertCircle, CheckCircle2, Trash2, Edit2 } from 'lucide-react';
import { StatusPill } from '../components/CostCard';
import { listQuotations, deleteQuotation, getQuotationPdf } from '../services/api';
import { QuotationEditor, QuotationPdfModal } from '../components/QuotationDocuments';

export default function Proforma() {
  const [searchParams] = useSearchParams();
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [search,  setSearch]  = useState(() => searchParams.get('q') || '');
  const [preview, setPreview] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [toast,   setToast]   = useState(null);

  const showToast = (msg, isErr = false) => { setToast({ msg, isErr }); setTimeout(() => setToast(null), 3500); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listQuotations();
      // Filter only Proforma Invoice type
      setRows(data.filter(q => q.doc_type === 'Proforma Invoice'));
      setOffline(false);
    } catch {
      setRows([
        { id: 1, quotation_number: 'PI-2026-09-0001', doc_type: 'Proforma Invoice', customer_name: 'Luxe Beauty Pvt Ltd', job_name: 'Premium Rigid Box', order_quantity: 1000, unit_price: 23.03, subtotal: 23030, gst_amount: 4145, grand_total: 27175, status: 'Finalized', created_at: '24 Sep 2026', has_pdf: false },
        { id: 2, quotation_number: 'PI-2026-09-0002', doc_type: 'Proforma Invoice', customer_name: 'Elite Brands',        job_name: 'Luxury Box',         order_quantity: 1500, unit_price: 24.06, subtotal: 36090, gst_amount: 6496, grand_total: 42586, status: 'Finalized', created_at: '16 Sep 2026', has_pdf: false },
      ]);
      setOffline(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setSearch(searchParams.get('q') || ''); }, [searchParams]);

  const handleDelete = async (e, row) => {
    e.stopPropagation();
    if (!window.confirm(`Delete ${row.quotation_number}?`)) return;
    if (offline) { showToast('Backend offline', true); return; }
    try { await deleteQuotation(row.id); showToast(`${row.quotation_number} deleted`); load(); }
    catch (err) { showToast(err.message, true); }
  };

  const handleDownload = async (e, row) => {
    e.stopPropagation();
    if (offline) { showToast('PDF requires backend', true); return; }
    try {
      const blob = await getQuotationPdf(row.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${row.quotation_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { showToast(err.message || 'Unable to download PDF', true); }
  };

  const filtered = rows.filter(r =>
    !search ||
    r.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.quotation_number?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Proforma</span>
          <h1 style={{ marginTop: 4 }}>Proforma Invoices</h1>
          <p>Formal proforma invoices with bank details and GST</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={load}><RefreshCw size={14} /></button>
        </div>
      </div>

      {offline && (
        <div className="warn-banner" style={{ marginBottom: 16 }}>
          <AlertCircle size={15} />
          <span>Backend offline — showing demo data. PDFs require a live backend.</span>
        </div>
      )}

      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 300 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }}
              placeholder="Search proforma…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>{loading ? 'Loading…' : `${filtered.length} proforma invoices`}</div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>PI Number</th>
                <th>Customer</th>
                <th>Product</th>
                <th style={{ textAlign: 'right' }}>Qty</th>
                <th style={{ textAlign: 'right' }}>Subtotal</th>
                <th style={{ textAlign: 'right' }}>GST</th>
                <th style={{ textAlign: 'right' }}>Grand Total</th>
                <th>Date</th>
                <th>Status</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(q => (
                <tr key={q.id}>
                  <td style={{ fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)', fontSize: 11 }}>{q.quotation_number}</td>
                  <td><strong style={{ fontSize: 12 }}>{q.customer_name}</strong></td>
                  <td style={{ fontSize: 12 }}>{q.job_name}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>{Number(q.order_quantity || 0).toLocaleString()}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {Number(q.subtotal || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                  <td style={{ textAlign: 'right', fontSize: 12 }}>₹ {Number(q.gst_amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)' }}>₹ {Number(q.grand_total || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                  <td style={{ fontSize: 11, color: 'var(--muted-2)' }}>{q.created_at}</td>
                  <td><StatusPill status={q.status} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                      <button className="btn btn-ghost btn-sm btn-icon" title="Edit document" onClick={e => { e.stopPropagation(); if (!offline) setEditingId(q.id); }}><Edit2 size={13} /></button>
                      <button className="btn btn-ghost btn-sm btn-icon" title="Preview PDF"
                        onClick={e => { e.stopPropagation(); if (offline) { showToast('PDF requires backend', true); return; } setPreview({ id: q.id, number: q.quotation_number }); }}>
                        <Eye size={13} />
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" title="Download PDF" style={{ color: 'var(--orange)' }}
                        onClick={e => handleDownload(e, q)}>
                        <Download size={13} />
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" title="Delete" style={{ color: '#E53E3E' }}
                        onClick={e => handleDelete(e, q)}>
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)', fontSize: 13 }}>
                    No proforma invoices yet. Generate one from a finalized estimate.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)', fontSize: 12, color: 'var(--muted-2)' }}>
          {filtered.length} proforma invoice{filtered.length !== 1 ? 's' : ''} · Bank details and GST included
        </div>
      </div>

      {editingId && <QuotationEditor quotationId={editingId} onClose={() => setEditingId(null)} onSaved={async () => { await load(); showToast('Proforma updated'); }} />}
      {preview && <QuotationPdfModal quotationId={preview.id} quotationNumber={preview.number} onClose={() => setPreview(null)} />}

      {toast && (
        <div className="toast" style={{ background: toast.isErr ? '#C53030' : 'var(--ink-2)' }}>
          {toast.isErr ? <AlertCircle size={14} style={{ color: '#FCA5A5' }} /> : <CheckCircle2 size={14} style={{ color: '#72D38D' }} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
}
