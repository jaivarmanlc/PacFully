import React, { useEffect, useState } from 'react';
import { Download, Eye, Save, X } from 'lucide-react';
import { getQuotation, getQuotationPdf, previewQuotationPdf, updateQuotation } from '../services/api';

const localToday = () => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
};

const toForm = quotation => ({
  ...quotation,
  document_date: String(quotation.created_at || '').slice(0, 10) || localToday(),
  customer_address: quotation.customer_address || '',
  notes: quotation.notes || '',
});

const toPayload = document => ({
  doc_type: document.doc_type,
  quotation_number: document.quotation_number.trim(),
  document_date: document.document_date,
  customer_name: document.customer_name,
  customer_address: document.customer_address,
  job_name: document.job_name,
  order_quantity: Number(document.order_quantity),
  unit_price: Number(document.unit_price),
  gst_percent: Number(document.gst_percent),
  validity_days: Number(document.validity_days),
  notes: document.notes,
});

const money = value => `₹ ${Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function QuotationPdfModal({ quotationId, quotationNumber, onClose }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    let objectUrl;
    getQuotationPdf(quotationId)
      .then(blob => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setUrl(objectUrl);
      })
      .catch(err => { if (active) setError(err.message || 'Unable to load PDF'); });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [quotationId]);

  return (
    <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-label={`${quotationNumber} PDF preview`} style={{ background: '#fff', borderRadius: 8, width: 'min(900px, calc(100vw - 32px))', height: '88vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
          <strong style={{ fontSize: 13 }}>{quotationNumber} PDF Preview</strong>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {url && <a href={url} download={`${quotationNumber}.pdf`} className="btn btn-secondary btn-sm"><Download size={13} /> Download</a>}
            <button className="modal-close" aria-label="Close preview" onClick={onClose}><X size={16} /></button>
          </div>
        </div>
        {url ? <iframe src={url} title={quotationNumber} style={{ flex: 1, border: 0 }} /> : <div role="status" style={{ padding: 24, color: error ? '#C53030' : 'var(--muted)' }}>{error || 'Loading PDF…'}</div>}
      </div>
    </div>
  );
}

export function QuotationEditor({ quotationId, onClose, onSaved }) {
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pdfAction, setPdfAction] = useState('');
  const [error, setError] = useState('');
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState('');

  useEffect(() => {
    let active = true;
    getQuotation(quotationId)
      .then(data => { if (active) setDocument(toForm(data)); })
      .catch(err => { if (active) setError(err.message || 'Unable to load document'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [quotationId]);

  useEffect(() => () => {
    if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
  }, [pdfPreviewUrl]);

  const update = (key, value) => setDocument(current => ({ ...current, [key]: value }));
  const quantity = Number(document?.order_quantity) || 0;
  const unitPrice = Number(document?.unit_price) || 0;
  const subtotal = quantity * unitPrice;
  const gstAmount = subtotal * (Number(document?.gst_percent) || 0) / 100;

  const downloadBlob = (blob, filename) => {
    const objectUrl = URL.createObjectURL(blob);
    const link = window.document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  };

  const handlePdf = async action => {
    setPdfAction(action);
    setError('');
    try {
      const blob = await previewQuotationPdf(toPayload(document));
      if (action === 'download') {
        downloadBlob(blob, `${document.quotation_number || 'document'}.pdf`);
      } else {
        setPdfPreviewUrl(current => {
          if (current) URL.revokeObjectURL(current);
          return URL.createObjectURL(blob);
        });
      }
    } catch (err) {
      setError(err.message || 'Unable to generate PDF');
    } finally {
      setPdfAction('');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      await updateQuotation(quotationId, toPayload(document));
      await onSaved();
      onClose();
    } catch (err) {
      setError(err.message || 'Unable to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
      <div role="dialog" aria-modal="true" aria-label="Edit quotation or proforma" style={{ background: 'var(--bg)', borderRadius: 8, width: 'min(1120px, calc(100vw - 32px))', height: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', background: 'var(--panel)', borderBottom: '1px solid var(--line)' }}>
          <div><strong style={{ fontSize: 15 }}>Edit Document</strong><div style={{ fontSize: 11, color: 'var(--muted-2)' }}>Changes update the saved document and PDF.</div></div>
          <button className="modal-close" aria-label="Close editor" onClick={onClose}><X size={16} /></button>
        </div>
        {loading ? <div role="status" style={{ padding: 24 }}>Loading document…</div> : document && (
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <section className="panel">
                <div className="form-grid-2">
                  <div className="form-group"><label className="form-label">Document Type</label><select className="form-input" value={document.doc_type} onChange={event => update('doc_type', event.target.value)}><option>Quotation</option><option>Proforma Invoice</option></select></div>
                  <div className="form-group"><label className="form-label">Document No.</label><input className="form-input" value={document.quotation_number} onChange={event => update('quotation_number', event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Date</label><input className="form-input" type="date" value={document.document_date} onChange={event => update('document_date', event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Customer</label><input className="form-input" value={document.customer_name || ''} onChange={event => update('customer_name', event.target.value)} /></div>
                </div>
                <div className="form-group" style={{ marginTop: 12 }}><label className="form-label">Billing Address</label><textarea className="form-input" rows={2} value={document.customer_address} onChange={event => update('customer_address', event.target.value)} /></div>
                <div className="form-group" style={{ marginTop: 12 }}><label className="form-label">Job / Product Description</label><input className="form-input" value={document.job_name || ''} onChange={event => update('job_name', event.target.value)} /></div>
                <div className="form-grid-2" style={{ marginTop: 12 }}>
                  <div className="form-group"><label className="form-label">Quantity</label><input className="form-input" type="number" min="1" value={document.order_quantity} onChange={event => update('order_quantity', event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Unit Price (₹)</label><input className="form-input" type="number" min="0" step="0.01" value={document.unit_price} onChange={event => update('unit_price', event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">GST (%)</label><input className="form-input" type="number" min="0" max="99.99" step="0.01" value={document.gst_percent} onChange={event => update('gst_percent', event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Validity (days)</label><input className="form-input" type="number" min="0" value={document.validity_days} onChange={event => update('validity_days', event.target.value)} /></div>
                </div>
              </section>
              <section className="panel"><label className="form-label">Terms &amp; Conditions</label><textarea className="form-input" rows={5} value={document.notes} onChange={event => update('notes', event.target.value)} /></section>
            </div>

            <section className="panel" style={{ padding: 22 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
                <strong style={{ fontFamily: 'Manrope', fontSize: 21 }}>Pac<span style={{ color: 'var(--orange)' }}>fully</span></strong>
                <div style={{ textAlign: 'right', fontSize: 11 }}><strong>{document.doc_type?.toUpperCase()}</strong><div>{document.quotation_number || 'Document number'}</div><div>{document.document_date}</div></div>
              </div>
              <div style={{ borderTop: '2px solid var(--orange)', marginBottom: 16 }} />
              <div style={{ marginBottom: 18 }}><div className="form-label">Bill To</div><strong>{document.customer_name || 'Customer name'}</strong><div style={{ whiteSpace: 'pre-line', color: 'var(--muted)', fontSize: 12 }}>{document.customer_address || 'Billing address'}</div></div>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto auto auto', gap: 10, borderBottom: '1px solid var(--line)', paddingBottom: 8, fontSize: 11, color: 'var(--muted)' }}><span>Description</span><span>Qty</span><span>Unit Price</span><span>Total</span></div>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto auto auto', gap: 10, padding: '12px 0', borderBottom: '1px solid var(--line-2)', fontSize: 12 }}><span>{document.job_name || 'Packaging'}</span><span>{quantity.toLocaleString()}</span><span>{money(unitPrice)}</span><strong>{money(subtotal)}</strong></div>
              <div style={{ marginLeft: 'auto', maxWidth: 300, display: 'grid', gap: 7, paddingTop: 14, fontSize: 12 }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Subtotal</span><strong>{money(subtotal)}</strong></div><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>GST ({Number(document.gst_percent) || 0}%)</span><strong>{money(gstAmount)}</strong></div><div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--ink-2)', paddingTop: 10, fontSize: 14 }}><strong>Total Order Value</strong><strong style={{ color: 'var(--orange)' }}>{money(subtotal + gstAmount)}</strong></div></div>
              <div style={{ whiteSpace: 'pre-line', color: 'var(--muted-2)', fontSize: 11, marginTop: 18 }}>{document.notes}</div>
            </section>
          </div>
        )}
        {error && <div role="alert" style={{ color: '#C53030', fontSize: 12, padding: '0 18px 10px' }}>{error}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: 14, borderTop: '1px solid var(--line)', background: 'var(--panel)' }}>
          <button className="btn btn-secondary" onClick={() => handlePdf('preview')} disabled={!document || Boolean(pdfAction) || saving}><Eye size={14} /> {pdfAction === 'preview' ? 'Generating…' : 'Preview PDF'}</button>
          <button className="btn btn-secondary" onClick={() => handlePdf('download')} disabled={!document || Boolean(pdfAction) || saving}><Download size={14} /> {pdfAction === 'download' ? 'Generating…' : 'Download PDF'}</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={!document || saving || Boolean(pdfAction)}><Save size={14} /> {saving ? 'Saving…' : 'Save Changes'}</button>
        </div>
      </div>
      {pdfPreviewUrl && <div className="modal-backdrop" style={{ zIndex: 1200 }} onMouseDown={event => { if (event.target === event.currentTarget) setPdfPreviewUrl(''); }}><div role="dialog" aria-modal="true" aria-label="PDF preview" style={{ background: '#fff', width: 'min(900px, calc(100vw - 32px))', height: '88vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}><div style={{ display: 'flex', justifyContent: 'space-between', padding: 12, borderBottom: '1px solid var(--line)' }}><strong>PDF Preview</strong><button className="modal-close" onClick={() => setPdfPreviewUrl('')}><X size={16} /></button></div><iframe src={pdfPreviewUrl} title="Edited document preview" style={{ flex: 1, border: 0 }} /></div></div>}
    </div>
  );
}