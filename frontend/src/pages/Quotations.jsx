import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Download, Eye, Trash2, RefreshCw, AlertCircle, CheckCircle2, X, ExternalLink } from 'lucide-react';
import { StatusPill } from '../components/CostCard';
import { listQuotations, deleteQuotation, pdfUrl } from '../services/api';

const DEMO = [
  { id: 1, quotation_number: 'QUO-2026-09-0001', doc_type: 'Quotation',        customer_name: 'Luxe Beauty Pvt Ltd', job_name: 'Premium Rigid Box', order_quantity: 1000, unit_price: 23.03, grand_total: 27175, status: 'Finalized', created_at: '24 Sep 2026', has_pdf: false },
  { id: 2, quotation_number: 'QUO-2026-09-0002', doc_type: 'Quotation',        customer_name: 'Aura Skincare',       job_name: 'Gift Box',           order_quantity: 2000, unit_price: 26.70, grand_total: 63012, status: 'Draft',     created_at: '20 Sep 2026', has_pdf: false },
  { id: 3, quotation_number: 'PI-2026-09-0001',  doc_type: 'Proforma Invoice', customer_name: 'Elite Brands',        job_name: 'Luxury Box',         order_quantity: 1500, unit_price: 24.06, grand_total: 42586, status: 'Finalized', created_at: '16 Sep 2026', has_pdf: false },
];

/* PDF preview modal */
function PdfModal({ quotationId, quotationNumber, onClose }) {
  const url = pdfUrl(quotationId);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, overflow: 'hidden',
          width: '80vw', maxWidth: 900, height: '88vh',
          display: 'flex', flexDirection: 'column', boxShadow: '0 24px 64px rgba(0,0,0,0.25)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid var(--line)',
          background: 'var(--panel)',
        }}>
          <div>
            <div style={{ fontFamily: 'Manrope', fontWeight: 700, fontSize: 15 }}>
              {quotationNumber}
            </div>
            <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>PDF Preview</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a
              href={url}
              download={`${quotationNumber}.pdf`}
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Download size={13} /> Download
            </a>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <ExternalLink size={13} /> Open
            </a>
            <button className="modal-close" onClick={onClose}><X size={16} /></button>
          </div>
        </div>

        {/* iFrame */}
        <iframe
          src={url}
          title={quotationNumber}
          style={{ flex: 1, border: 'none', background: '#f0f0f0' }}
        />
      </div>
    </div>
  );
}

export default function Quotations() {
  const navigate = useNavigate();
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [search,  setSearch]  = useState('');
  const [preview, setPreview] = useState(null); // { id, number }
  const [toast,   setToast]   = useState(null);

  const showToast = (msg, isErr = false) => {
    setToast({ msg, isErr });
    setTimeout(() => setToast(null), 3500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listQuotations();
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

  const handleDelete = async (e, row) => {
    e.stopPropagation();
    if (!window.confirm(`Delete ${row.quotation_number}?`)) return;
    if (offline) { showToast('Backend offline', true); return; }
    try {
      await deleteQuotation(row.id);
      showToast(`${row.quotation_number} deleted`);
      load();
    } catch (err) {
      showToast(err.message, true);
    }
  };

  const handleDownload = (e, row) => {
    e.stopPropagation();
    if (offline) { showToast('PDF not available in demo mode', true); return; }
    const url = pdfUrl(row.id);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${row.quotation_number}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const filtered = rows.filter(r =>
    !search ||
    r.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.quotation_number?.toLowerCase().includes(search.toLowerCase()) ||
    r.job_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Quotations</span>
          <h1 style={{ marginTop: 4 }}>Quotations</h1>
          <p>Customer-facing quotation and proforma documents</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={load} title="Refresh">
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/estimator/new')}>
            <Plus size={15} /> New Quotation
          </button>
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
          <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }}
              placeholder="Search quotations…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>
            {loading ? 'Loading…' : `${filtered.length} documents`}
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Document No.</th>
                <th>Type</th>
                <th>Customer</th>
                <th>Product</th>
                <th style={{ textAlign: 'right' }}>Qty</th>
                <th style={{ textAlign: 'right' }}>Unit Price</th>
                <th style={{ textAlign: 'right' }}>Grand Total</th>
                <th>Date</th>
                <th>Status</th>
                <th style={{ textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(q => (
                <tr key={q.id}>
                  <td style={{ fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)', fontSize: 11 }}>
                    {q.quotation_number}
                  </td>
                  <td>
                    <span className={`pill ${q.doc_type === 'Proforma Invoice' ? 'pill-blue' : 'pill-orange'}`} style={{ fontSize: 10 }}>
                      {q.doc_type === 'Proforma Invoice' ? 'Proforma' : 'Quotation'}
                    </span>
                  </td>
                  <td><strong style={{ fontSize: 12 }}>{q.customer_name}</strong></td>
                  <td style={{ fontSize: 12 }}>{q.job_name}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>
                    {Number(q.order_quantity || 0).toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700 }}>
                    ₹ {Number(q.unit_price || 0).toFixed(2)}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)' }}>
                    ₹ {Number(q.grand_total || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--muted-2)' }}>{q.created_at}</td>
                  <td><StatusPill status={q.status} /></td>
                  <td>
                    <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                      {/* Preview PDF */}
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        title="Preview PDF"
                        onClick={e => {
                          e.stopPropagation();
                          if (offline) { showToast('PDF requires backend', true); return; }
                          setPreview({ id: q.id, number: q.quotation_number });
                        }}
                      >
                        <Eye size={13} />
                      </button>
                      {/* Download PDF */}
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        title="Download PDF"
                        onClick={e => handleDownload(e, q)}
                        style={{ color: 'var(--orange)' }}
                      >
                        <Download size={13} />
                      </button>
                      {/* Delete */}
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        title="Delete"
                        style={{ color: '#E53E3E' }}
                        onClick={e => handleDelete(e, q)}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)', fontSize: 13 }}>
                    No quotations yet. Create an estimate and finalize it to generate a quotation.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--line)', fontSize: 12, color: 'var(--muted-2)' }}>
          {filtered.length} document{filtered.length !== 1 ? 's' : ''} · Internal manufacturing cost is excluded from all customer-facing PDFs
        </div>
      </div>

      {/* PDF Preview Modal */}
      {preview && (
        <PdfModal
          quotationId={preview.id}
          quotationNumber={preview.number}
          onClose={() => setPreview(null)}
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
