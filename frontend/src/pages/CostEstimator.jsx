import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import BrandLogo from '../components/BrandLogo.jsx';
import {
  Upload, FileText, ChevronDown, Plus, Save, ArrowRight, ArrowLeft,
  CheckCircle2, AlertCircle, RotateCcw, Edit3, Eye, Download,
  Cpu, Layers, Printer, Droplets, Scissors, Sparkles,
  Package, Zap, Box, X, Check, Info
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { Stepper, RateConfigRow, CalcTracePanel, money } from '../components/CostCard';
import { listCustomers, createCustomer, getMasterConfig, getNextQuotationNumber, previewQuotationPdf, saveEstimate, finalizeEstimate, createQuotation } from '../services/api';

// ── Constants ─────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const STEPS = ['Layout & AI Extraction', 'Technical Data', 'Costing Modules', 'Summary & Margin', 'Quotation / Proforma'];

const MODULE_TABS = ['Kappa', 'Wrapper', 'Printing', 'Lamination', 'Glue', 'Punching', 'Embellishments', 'Accessories', 'Conversion'];

const AI_FIELDS = [
  { label: 'Finished Size (L × W)', value: '320 × 120 × 80 mm', confidence: 98, status: 'Confirmed' },
  { label: 'Material', value: 'Kappa Board', confidence: 92, status: 'Confirmed' },
  { label: 'GSM', value: '1200 GSM', confidence: 88, status: 'Confirmed' },
  { label: 'Thickness', value: '1.8 mm', confidence: 85, status: 'Confirmed' },
  { label: 'Structure Type', value: 'Rigid Box', confidence: 96, status: 'Confirmed' },
  { label: 'Order Quantity', value: '1,000 boxes', confidence: 90, status: 'Confirmation Required' },
  { label: 'Printing', value: '4-Color (CMYK)', confidence: 94, status: 'Confirmed' },
  { label: 'Lamination', value: 'Matte Lamination', confidence: 91, status: 'Confirmed' },
  { label: 'Glue Area', value: 'Full Surface', confidence: 80, status: 'Confirmed' },
  { label: 'Punching', value: 'Standard', confidence: 93, status: 'Confirmed' },
  { label: 'Embellishments', value: 'Gold Foil', confidence: 76, status: 'Confirmation Required' },
  { label: 'Inserts', value: 'EVA Insert', confidence: 87, status: 'Confirmed' },
];

const INITIAL_FORM = {
  quantity: 1000, margin_percent: 20,
  kappa_material: 'Kappa Board', kappa_thickness_mm: 1.8, kappa_gsm_at_1mm: 1200, kappa_sheet_length_mm: 1000, kappa_sheet_width_mm: 700, kappa_ups: 2, kappa_wastage_percent: 10, kappa_rate_per_kg: 80,
  kappa_master_rate: 80, kappa_override_rate: null,
  wrapper_gsm: 128, wrapper_ups: 1, wrapper_sheet_length_mm: 1000, wrapper_sheet_width_mm: 700, wrapper_wastage_percent: 10, wrapper_make_ready_sheets: 150, wrapper_rate_per_kg: 95,
  wrapper_master_rate: 95, wrapper_override_rate: null,
  print_sheet_size: '28x40', print_master_rate: 6500, print_additional_rate: 0.8, print_override_rate: null,
  lamination_type: 'thermal', lamination_sheet_length_in: 28, lamination_sheet_width_in: 40,
  lam_master_rate: 1.10, lam_override_rate: null,
  glue_lines: [
    { name: 'Top Wrapper', area_sq_in: 620, gsm: 20, rate_per_kg: 90 },
    { name: 'Bottom Wrapper', area_sq_in: 480, gsm: 20, rate_per_kg: 90 },
  ],
  punching_material: 'Kappa', punching_machine_rate_per_hour: 400, punching_speed: 400, punching_setup_hours: 0.5,
  embellishment_area_sq_in: 24, embellishment_rate_per_sq_in: 2.5, embellishment_setup: 800, embellishment_minimum: 1000, embellishment_type: 'Gold Foil',
  accessories: [
    { name: 'Magnet Snap', quantity_per_box: 1, unit_cost: 3.5 },
    { name: 'Ribbon', quantity_per_box: 1, unit_cost: 1.2 },
  ],
  conversion_machine_rate: 0, conversion_machine_hours: 0, conversion_labour_rate: 0, conversion_labour_hours: 0, conversion_setup: 0,
  eb_method: 'box', eb_value: 0,
};

const PRINT_RATE_KEYS = {
  '15x20': ['print_15x20_first', 'print_15x20_additional'],
  '20x28': ['print_20x28_first', 'print_20x28_additional'],
  '28x40': ['print_28x40_first', 'print_28x40_additional'],
};
const PUNCH_SPEED_KEYS = {
  Kappa: 'punching_speed_kappa', Wrapper: 'punching_speed_wrapper', FBB: 'punching_speed_fbb',
  Duplex: 'punching_speed_duplex', 'Foam/EVA/EPE': 'punching_speed_foam',
};

function moduleInputs(module, form, wrapperFinalSheets) {
  const quantity = form.quantity;
  switch (module) {
    case 'Kappa':
      return {
        quantity,
        kappa_thickness_mm: form.kappa_thickness_mm,
        kappa_gsm_at_1mm: form.kappa_gsm_at_1mm,
        kappa_sheet_length_mm: form.kappa_sheet_length_mm,
        kappa_sheet_width_mm: form.kappa_sheet_width_mm,
        kappa_ups: form.kappa_ups,
        kappa_wastage_percent: form.kappa_wastage_percent,
        kappa_rate_per_kg: form.kappa_override_rate ?? form.kappa_master_rate,
        kappa_master_rate: form.kappa_master_rate,
        kappa_override_rate: form.kappa_override_rate,
      };
    case 'Wrapper':
      return {
        quantity,
        wrapper_gsm: form.wrapper_gsm,
        wrapper_ups: form.wrapper_ups,
        wrapper_sheet_length_mm: form.wrapper_sheet_length_mm,
        wrapper_sheet_width_mm: form.wrapper_sheet_width_mm,
        wrapper_wastage_percent: form.wrapper_wastage_percent,
        wrapper_make_ready_sheets: form.wrapper_make_ready_sheets,
        wrapper_rate_per_kg: form.wrapper_override_rate ?? form.wrapper_master_rate,
        wrapper_master_rate: form.wrapper_master_rate,
        wrapper_override_rate: form.wrapper_override_rate,
      };
    case 'Printing':
      return {
        quantity, wrapper_final_sheets: wrapperFinalSheets, print_sheet_size: form.print_sheet_size,
        print_master_rate: form.print_master_rate, print_additional_rate: form.print_additional_rate,
        print_override_rate: form.print_override_rate,
      };
    case 'Lamination':
      return {
        quantity, wrapper_final_sheets: wrapperFinalSheets,
        lamination_type: form.lamination_type,
        lamination_sheet_length_in: form.lamination_sheet_length_in,
        lamination_sheet_width_in: form.lamination_sheet_width_in,
        lam_master_rate: form.lam_master_rate,
        lam_override_rate: form.lam_override_rate,
      };
    case 'Glue':
      return { quantity, glue_lines: form.glue_lines };
    case 'Punching':
      return {
        quantity, punching_material: form.punching_material,
        punching_machine_rate_per_hour: form.punching_machine_rate_per_hour,
        punching_speed: form.punching_speed,
        punching_setup_hours: form.punching_setup_hours,
        ...(form.punching_material === 'Wrapper' ? { wrapper_final_sheets: wrapperFinalSheets } : {}),
      };
    case 'Embellishments':
      return {
        quantity,
        embellishment_area_sq_in: form.embellishment_area_sq_in,
        embellishment_rate_per_sq_in: form.embellishment_rate_per_sq_in,
        embellishment_setup: form.embellishment_setup,
        embellishment_minimum: form.embellishment_minimum,
      };
    case 'Accessories':
      return { quantity, accessories: form.accessories };
    default:
      return {};
  }
}

// ── Field Component ────────────────────────────────────────
function Field({ label, value, onChange, type = 'number', options, readOnly }) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      {options ? (
        <select className="form-select" value={value} onChange={e => onChange?.(e.target.value)} disabled={readOnly}>
          {options.map(o => <option key={o}>{o}</option>)}
        </select>
      ) : (
        <input
          className="form-input"
          type={type}
          value={value}
          readOnly={readOnly}
          onChange={e => onChange?.(type === 'number' ? Number(e.target.value) : e.target.value)}
        />
      )}
    </div>
  );
}

// ── Step 1: Layout Upload + AI Extraction ─────────────────
const DEMO_CUSTOMERS = [
  { name: 'Luxe Beauty Pvt Ltd' },
  { name: 'Aura Skincare' },
  { name: 'Veda Naturals' },
  { name: 'Elite Brands' },
];

function AddCustomerModal({ onClose, onSaved }) {
  const [form, setForm] = useState({ name: '', contact: '', email: '', phone: '', city: '', state: '', address: '', gst_number: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (key, value) => setForm(current => ({ ...current, [key]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('Customer name is required');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const created = await createCustomer({ ...form, name: form.name.trim() });
      onSaved(created);
    } catch (err) {
      setError(err.message || 'Unable to add customer');
      setSaving(false);
    }
  };

  const fields = [
    ['name', 'Company Name *'], ['contact', 'Contact Person'], ['email', 'Email'],
    ['phone', 'Phone'], ['city', 'City'], ['state', 'State'], ['gst_number', 'GST Number'],
  ];

  return (
    <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !saving) onClose(); }}>
      <form className="modal" style={{ width: 520 }} role="dialog" aria-modal="true" aria-labelledby="new-customer-title" onSubmit={handleSubmit}>
        <div className="modal-header">
          <div>
            <span className="eyebrow">New Customer</span>
            <h2 id="new-customer-title">Add Customer</h2>
            <p>Enter the company details to create a customer record.</p>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose} disabled={saving}><X size={16} /></button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {fields.map(([key, label]) => (
            <div className="form-group" key={key} style={key === 'name' ? { gridColumn: '1 / -1' } : {}}>
              <label className="form-label" htmlFor={`new-customer-${key}`}>{label}</label>
              <input
                id={`new-customer-${key}`}
                className="form-input"
                type={key === 'email' ? 'email' : 'text'}
                value={form[key]}
                onChange={event => set(key, event.target.value)}
                required={key === 'name'}
              />
            </div>
          ))}
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="form-label" htmlFor="new-customer-address">Address</label>
            <textarea id="new-customer-address" className="form-input" style={{ height: 64, paddingTop: 8, resize: 'vertical' }} value={form.address} onChange={event => set('address', event.target.value)} />
          </div>
        </div>
        {error && <div role="alert" style={{ color: '#C53030', fontSize: 12, marginTop: 10, display: 'flex', alignItems: 'center', gap: 6 }}><AlertCircle size={13} /> {error}</div>}
        <div className="modal-footer">
          <button className="btn btn-secondary" type="button" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving...' : 'Add Customer'}</button>
        </div>
      </form>
    </div>
  );
}

function StepLayout({ onNext, customer, setCustomer, jobName, setJobName }) {
  const [file, setFile] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [customers, setCustomers] = useState(DEMO_CUSTOMERS);
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [showDimensions, setShowDimensions] = useState(false);
  const previewRef = useRef(null);
  const fileRef = useRef();

  useEffect(() => {
    let active = true;
    listCustomers().then(data => {
      if (!active) return;
      const rows = Array.isArray(data) ? data : [];
      setCustomers(rows);
      setCustomer(current => rows.some(row => row.name === current) ? current : (rows[0]?.name || ''));
    }).catch(() => {});
    return () => { active = false; };
  }, [setCustomer]);

  const handleCustomerSaved = (created) => {
    setCustomers(current => [...current.filter(item => item.id !== created.id), created]);
    setCustomer(created.name);
    setShowAddCustomer(false);
  };

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setExtracting(true);
    setProgress(0);
    const steps = [20, 45, 65, 82, 95, 100];
    let i = 0;
    const tick = setInterval(() => {
      setProgress(steps[i++]);
      if (i >= steps.length) {
        clearInterval(tick);
        setTimeout(() => { setExtracting(false); setExtracted(true); }, 400);
      }
    }, 500);
  };

  const handleDownloadPreview = () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 130"><rect x="40" y="30" width="140" height="70" fill="#FFF1ED" stroke="#FF5A3A" stroke-width="1.5" stroke-dasharray="4,3"/><rect x="40" y="0" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C"/><rect x="40" y="100" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C"/><rect x="0" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C"/><rect x="180" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C"/><text x="110" y="68" text-anchor="middle" font-size="10" fill="#FF5A3A">220 mm</text></svg>';
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'layout-preview.svg';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const progressSteps = [
    'Reading layout file',
    'Detecting dimensions',
    'Identifying materials',
    'Analysing structure',
    'Extraction complete',
  ];
  const doneCount = Math.floor((progress / 100) * progressSteps.length);

  return (
    <div>
      {/* Customer / Job row */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 14, alignItems: 'end' }}>
          <div className="form-group">
            <label className="form-label">Customer</label>
            <div style={{ position: 'relative' }}>
              <select className="form-select" value={customer} onChange={e => setCustomer(e.target.value)}>
                {!customers.length && <option value="">Select a customer</option>}
                {customers.map((row, index) => <option key={row.id ?? row.name ?? index} value={row.name}>{row.name}</option>)}
              </select>
            </div>
          </div>
          <Field label="Job Name" type="text" value={jobName} onChange={setJobName} />
          <button type="button" className="btn btn-secondary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }} onClick={() => setShowAddCustomer(true)}>
            <Plus size={13} /> Add New
          </button>
        </div>
      </div>

      {!extracted ? (
        <div className="grid-col-6-4" style={{ gap: 16 }}>
          {/* Upload panel */}
          <div className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Upload Packaging Layout</div>
                <div className="panel-sub">PDF, PNG, JPG or JPEG · AI extraction ready</div>
              </div>
            </div>

            {!file ? (
              <div
                className="upload-box"
                onClick={() => fileRef.current?.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}
              >
                <div className="upload-icon"><Upload size={24} /></div>
                <h3>Drag & drop your packaging layout</h3>
                <p>(PDF, PNG, JPG, JPEG)</p>
                <p style={{ fontSize: 11, color: 'var(--muted-3)' }}>or</p>
                <button className="btn btn-secondary btn-sm" onClick={e => { e.stopPropagation(); fileRef.current?.click(); }}>
                  Choose File
                </button>
                <p style={{ fontSize: 11, color: 'var(--muted-3)', marginTop: 4 }}>Max file size: 20MB</p>
                <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg" style={{ display: 'none' }}
                  onChange={e => handleFile(e.target.files[0])} />
              </div>
            ) : (
              <div>
                {/* File bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--orange-light)', borderRadius: 8, marginBottom: 16, border: '1px solid var(--orange-border)' }}>
                  <FileText size={18} color="var(--orange)" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{file.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>
                      {(file.size / 1024).toFixed(0)} KB
                    </div>
                  </div>
                  <span className="pill pill-orange" style={{ fontSize: 10 }}>Layout analysed</span>
                </div>

                {/* Dieline preview */}
                <div ref={previewRef} style={{ background: '#FFFAF8', border: '1px solid var(--orange-border)', borderRadius: 8, padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-around', minHeight: 160 }}>
                  <div style={{ position: 'relative' }}>
                    {/* Simple dieline SVG */}
                    <svg width="220" height="130" viewBox="0 0 220 130">
                      <rect x="40" y="30" width="140" height="70" fill="#FFF1ED" stroke="#FF5A3A" strokeWidth="1.5" strokeDasharray="4,3" rx="2" />
                      <rect x="40" y="0" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                      <rect x="40" y="100" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                      <rect x="0" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                      <rect x="180" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                      <text x="110" y="68" textAnchor="middle" fontSize="10" fill="#FF5A3A" fontFamily="Manrope" fontWeight="600">220 mm</text>
                      <text x="8" y="68" textAnchor="middle" fontSize="9" fill="#FF7A5C" transform="rotate(-90,8,68)">80mm</text>
                    </svg>
                    <div style={{ position: 'absolute', top: -8, right: -8, background: '#3D9D62', color: '#fff', borderRadius: 6, padding: '3px 8px', fontSize: 10, fontWeight: 700 }}>
                      AI Detected
                    </div>
                  </div>
                  <div style={{ maxWidth: 160 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-2)', marginBottom: 8 }}>Rigid Box · Luxury</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.8 }}>
                      <div>L: <strong>320 mm</strong></div>
                      <div>W: <strong>120 mm</strong></div>
                      <div>H: <strong>80 mm</strong></div>
                    </div>
                  </div>
                </div>

                {extracting && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 600 }}>AI Extraction Progress</div>
                    </div>
                    <div className="bar-track" style={{ height: 6, marginBottom: 12 }}>
                      <div className="bar-fill" style={{ width: `${progress}%`, transition: 'width 0.5s' }} />
                    </div>
                    {progressSteps.map((s, i) => (
                      <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5, fontSize: 12 }}>
                        {i < doneCount
                          ? <CheckCircle2 size={13} color="#3D9D62" />
                          : <div style={{ width: 13, height: 13, borderRadius: '50%', border: '1.5px solid var(--muted-3)' }} />
                        }
                        <span style={{ color: i < doneCount ? 'var(--ink-3)' : 'var(--muted-2)' }}>{s}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Supported formats */}
          <div className="panel" style={{ height: 'fit-content' }}>
            <div className="panel-title" style={{ marginBottom: 14 }}>Supported formats</div>
            {[
              { fmt: 'PDF', desc: 'Vector dieline files', icon: '📄' },
              { fmt: 'PNG', desc: 'High-res layout images', icon: '🖼' },
              { fmt: 'JPG', desc: 'Scanned layouts', icon: '📷' },
              { fmt: 'JPEG', desc: 'Compressed images', icon: '📷' },
            ].map(f => (
              <div key={f.fmt} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: '1px solid var(--line-2)' }}>
                <span style={{ fontSize: 16 }}>{f.icon}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{f.fmt}</div>
                  <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>{f.desc}</div>
                </div>
              </div>
            ))}
            <div style={{ marginTop: 14, background: 'var(--orange-light)', borderRadius: 7, padding: '10px 12px', fontSize: 11, color: 'var(--ink-3)' }}>
              💡 For best results, upload a clear outline with dimensions.
            </div>
          </div>
        </div>
      ) : (
        /* ── Extraction results ── */
        <div className="grid-col-6-4" style={{ gap: 16 }}>
          <div className="panel">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, padding: '10px 14px', background: '#E8F8ED', borderRadius: 8 }}>
              <CheckCircle2 size={18} color="#3D9D62" />
              <div style={{ flex: 1, fontSize: 12, fontWeight: 600, color: '#2D6A4F' }}>
                {file.name} — Layout analysed successfully
              </div>
              <span className="pill pill-confirmed" style={{ fontSize: 10 }}>98% Confidence</span>
            </div>

            <div className="panel-title" style={{ marginBottom: 12 }}>AI Extraction Progress</div>
            {progressSteps.map(s => (
              <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
                <CheckCircle2 size={13} color="#3D9D62" />
                <span style={{ color: 'var(--ink-3)' }}>{s}</span>
              </div>
            ))}

            <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowDimensions(true)}>View dimensions</button>
              <button className="btn btn-secondary btn-sm" onClick={() => previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}>Preview layout</button>
              <button className="btn btn-secondary btn-sm" onClick={handleDownloadPreview}>Download preview</button>
            </div>
          </div>

          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 12 }}>Extraction Confidence</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { label: 'Dimensions', pct: 98, color: '#3D9D62' },
                { label: 'Material', pct: 90, color: '#3D9D62' },
                { label: 'Structure', pct: 85, color: '#3D9D62' },
                { label: 'Finishing', pct: 78, color: '#D97706' },
              ].map(c => (
                <div key={c.label} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
                  <span style={{ width: 80, color: 'var(--muted)' }}>{c.label}</span>
                  <div className="bar-track">
                    <div style={{ height: '100%', width: `${c.pct}%`, background: c.color, borderRadius: 99, transition: 'width 0.6s' }} />
                  </div>
                  <span style={{ fontFamily: 'Manrope', fontWeight: 700, fontSize: 11 }}>{c.pct}%</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 16, padding: '10px 12px', background: 'var(--orange-light)', borderRadius: 7, fontSize: 11, color: 'var(--ink-3)', border: '1px solid var(--orange-border)' }}>
              <strong>Confirmation Required</strong> for 2 fields — review in Technical Data step.
            </div>
          </div>
        </div>
      )}

      {/* Nav */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
        <button className="btn btn-primary" onClick={onNext} disabled={!extracted && !file}>
          Continue to Technical Data <ArrowRight size={15} />
        </button>
      </div>
      {showDimensions && (
        <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setShowDimensions(false); }}>
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="derived-dimensions-title" style={{ width: 420 }}>
            <div className="modal-header">
              <div><span className="eyebrow">Layout extraction</span><h2 id="derived-dimensions-title">Extracted dimensions</h2></div>
              <button className="modal-close" type="button" aria-label="Close dimensions" onClick={() => setShowDimensions(false)}><X size={16} /></button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              {[['Length', '320 mm'], ['Width', '120 mm'], ['Height', '80 mm']].map(([label, value]) => (
                <div key={label}><div className="form-label">{label}</div><strong>{value}</strong></div>
              ))}
            </div>
            <div className="modal-footer"><button className="btn btn-primary" type="button" onClick={() => setShowDimensions(false)}>Done</button></div>
          </section>
        </div>
      )}
      {showAddCustomer && <AddCustomerModal onClose={() => setShowAddCustomer(false)} onSaved={handleCustomerSaved} />}
    </div>
  );
}

// ── Step 2: Technical Data Review ─────────────────────────
function StepTechnicalData({ form, setForm, onNext, onBack }) {
  const [notes, setNotes] = useState('');

  const handleStatus = (i, status) => {
    // toggle confirmation status (visual only for demo)
  };

  return (
    <div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {/* Fields table */}
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)' }}>
            <div className="panel-title">AI Extracted Technical Data</div>
            <div className="panel-sub">Review and confirm the extracted information</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Parameter</th>
                <th style={{ textAlign: 'right' }}>Extracted Value</th>
                <th style={{ textAlign: 'right' }}>Confidence</th>
                <th>Review Status</th>
              </tr>
            </thead>
            <tbody>
              {AI_FIELDS.map((f, i) => (
                <tr key={f.label}>
                  <td style={{ fontWeight: 500, fontSize: 12 }}>{f.label}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600, fontSize: 12 }}>{f.value}</td>
                  <td style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: f.confidence >= 90 ? '#3D9D62' : f.confidence >= 80 ? '#D97706' : '#E53E3E' }}>
                      {f.confidence}%
                    </span>
                  </td>
                  <td>
                    {f.status === 'Confirmed' ? (
                      <span className="pill pill-confirmed" style={{ fontSize: 10 }}>
                        <CheckCircle2 size={10} style={{ marginRight: 3 }} />Confirmed
                      </span>
                    ) : (
                      <span className="pill pill-required" style={{ fontSize: 10 }}>
                        <AlertCircle size={10} style={{ marginRight: 3 }} />Confirmation Required
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Right panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Layout thumbnail */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 12 }}>Layout Thumbnail</div>
            <div style={{ background: '#FFFAF8', border: '1px solid var(--orange-border)', borderRadius: 8, padding: 16, display: 'flex', justifyContent: 'center' }}>
              <svg width="160" height="110" viewBox="0 0 220 130">
                <rect x="40" y="30" width="140" height="70" fill="#FFF1ED" stroke="#FF5A3A" strokeWidth="1.5" strokeDasharray="4,3" rx="2" />
                <rect x="40" y="0" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                <rect x="40" y="100" width="140" height="30" fill="#FFE8E2" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                <rect x="0" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                <rect x="180" y="30" width="40" height="70" fill="#FFF8F5" stroke="#FF7A5C" strokeWidth="1" rx="1" />
                <text x="110" y="68" textAnchor="middle" fontSize="11" fill="#FF5A3A" fontFamily="Manrope" fontWeight="600">220 mm</text>
              </svg>
            </div>
          </div>

          {/* Notes */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 10 }}>Notes</div>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Add any additional notes or corrections..."
              style={{
                width: '100%', minHeight: 90, border: '1px solid var(--line)',
                borderRadius: 7, padding: 10, fontSize: 12, fontFamily: 'Inter',
                outline: 'none', resize: 'vertical', color: 'var(--ink)',
              }}
            />
          </div>

          {/* Warnings */}
          <div className="warn-banner">
            <AlertCircle size={15} />
            <div>
              <strong style={{ fontSize: 12 }}>2 fields need confirmation</strong>
              <div style={{ fontSize: 11, marginTop: 2 }}>Order Quantity and Embellishments require manual verification.</div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={15} /> Back
        </button>
        <button className="btn btn-primary" onClick={onNext}>
          Continue to Costing Modules <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}

// ── Step 3: Costing Modules ────────────────────────────────
function StepCostingModules({ form, setForm, masterRates, result, moduleResults, onCalculate, onCalculateModule, calculatingAll, calculatingModule, onNext, onBack }) {
  const [activeTab, setActiveTab] = useState('Kappa');
  const update = (key, val) => setForm(f => ({ ...f, [key]: val }));
  const line = moduleResults[activeTab] ?? result?.lines?.find(l => l.module === activeTab);

  const tabIcons = {
    Kappa: Layers, Wrapper: Box, Printing: Printer, Lamination: Layers,
    Glue: Droplets, Punching: Scissors, Embellishments: Sparkles,
    Accessories: Package, Conversion: Zap,
  };

  return (
    <div>
      {/* Top calculate bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, fontSize: 13, color: 'var(--muted)' }}>
          <span>Order Qty: <strong style={{ color: 'var(--ink-2)', fontFamily: 'Manrope', fontSize: 22, fontWeight: 800, lineHeight: 1 }}>{form.quantity.toLocaleString()}</strong></span>
          {result && <span>Cost/Box: <strong style={{ color: 'var(--orange)' }}>₹ {result.cost_per_box?.toFixed(2)}</strong></span>}
        </div>
        <button className="btn btn-primary" onClick={onCalculate} disabled={calculatingAll || calculatingModule !== null}>
          <Cpu size={14} /> {calculatingAll ? 'Calculating...' : 'Calculate All Modules'}
        </button>
      </div>

      {/* Module tabs */}
      <div className="module-tabs">
        {MODULE_TABS.map(t => (
          <button key={t} className={`module-tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Module panels */}
      {activeTab === 'Kappa' && <KappaModule form={form} update={update} masterRates={masterRates} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Wrapper' && <WrapperModule form={form} update={update} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Printing' && <PrintingModule form={form} update={update} masterRates={masterRates} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Lamination' && <LaminationModule form={form} update={update} masterRates={masterRates} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Glue' && <GlueModule form={form} update={update} masterRates={masterRates} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Punching' && <PunchingModule form={form} update={update} masterRates={masterRates} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Embellishments' && <EmbellishmentsModule form={form} update={update} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Accessories' && <AccessoriesModule form={form} update={update} line={line} onCalculate={() => onCalculateModule(activeTab)} calculating={calculatingAll || calculatingModule === activeTab} />}
      {activeTab === 'Conversion' && <ConfigRequiredModule title="Conversion" desc="Machine + Labour + Setup formula is pending business confirmation." />}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
        <button className="btn btn-secondary" onClick={onBack}><ArrowLeft size={15} /> Back</button>
        <button className="btn btn-primary" onClick={onNext}>Continue to Summary <ArrowRight size={15} /></button>
      </div>
    </div>
  );
}

function ModuleResultCard({ line, onCalculate, calculating }) {
  return (
    <div style={{ background: 'var(--line-2)', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="line-item">
        <span>Total Cost</span>
        <strong style={{ fontFamily: 'Manrope', fontSize: 15 }}>{line ? money(line.total_cost) : '—'}</strong>
      </div>
      <div className="line-item">
        <span>Cost / Box</span>
        <strong style={{ fontFamily: 'Manrope', fontSize: 15, color: 'var(--orange)' }}>{line ? money(line.cost_per_box) : '—'}</strong>
      </div>
      <div className="line-item">
        <span>Weightage</span>
        <strong>{line?.weightage_percent == null ? '—' : `${line.weightage_percent.toFixed(1)}%`}</strong>
      </div>
      <button className="btn btn-primary btn-sm" onClick={onCalculate} disabled={calculating}>
        {calculating ? 'Calculating...' : 'Calculate'}
      </button>
    </div>
  );
}

// ── Kappa Module ───────────────────────────────────────────
function KappaModule({ form, update, masterRates, line, onCalculate, calculating }) {
  const effectiveRate = form.kappa_override_rate ?? form.kappa_master_rate;
  return (
    <div className="panel" style={{ marginBottom: 0 }}>
      <div className="panel-header">
        <div>
          <div className="panel-title">Kappa Costing Details</div>
          <div className="panel-sub">Board material costing — Effective GSM = GSM@1mm × Thickness</div>
        </div>
        {line && <span className="pill pill-confirmed">Calculated</span>}
      </div>

      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="Board Type" options={['Kappa Board', 'FBB', 'Duplex Board']} value={form.kappa_material} onChange={value => {
          const rateKey = { 'Kappa Board': 'kappa_rate_per_kg', FBB: 'fbb_rate_per_kg', 'Duplex Board': 'duplex_board_rate_per_kg' }[value];
          const rate = masterRates?.[rateKey] ?? form.kappa_master_rate;
          update('kappa_material', value);
          update('kappa_master_rate', rate);
          update('kappa_rate_per_kg', rate);
        }} />
        <Field label="GSM" value={form.kappa_gsm_at_1mm} onChange={v => update('kappa_gsm_at_1mm', v)} />
        <Field label="Thickness (mm)" value={form.kappa_thickness_mm} onChange={v => update('kappa_thickness_mm', v)} />
        <Field label="Sheet Size (L × W mm)" type="text" value={`${form.kappa_sheet_length_mm} × ${form.kappa_sheet_width_mm}`} readOnly />
      </div>
      <div className="form-grid-4" style={{ marginBottom: 20 }}>
        <Field label="UPS (Sheets)" value={form.kappa_ups} onChange={v => update('kappa_ups', v)} />
        <Field label="Order Quantity" value={form.quantity} onChange={v => update('quantity', v)} />
        <Field label="Wastage (%)" value={form.kappa_wastage_percent} onChange={v => update('kappa_wastage_percent', v)} />
      </div>

      <div style={{ marginBottom: 20 }}>
        <div className="form-label" style={{ marginBottom: 8 }}>Rate Configuration (₹/kg)</div>
        <RateConfigRow
          masterRate={form.kappa_master_rate}
          overrideRate={form.kappa_override_rate}
          effectiveRate={effectiveRate}
          onOverrideChange={v => update('kappa_override_rate', v)}
          onReset={() => update('kappa_override_rate', null)}
        />
      </div>

      <div className="grid-col-6-4" style={{ gap: 16 }}>
          {line ? <CalcTracePanel
            rows={line.trace.map(t => ({ label: t.label, value: t.value }))}
            formula="Total Cost = Final Sheets × KG/Sheet × Rate/KG"
          /> : <div />}
          <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Wrapper Module ─────────────────────────────────────────
function WrapperModule({ form, update, line, onCalculate, calculating }) {
  const effectiveRate = form.wrapper_override_rate ?? form.wrapper_master_rate;
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">Wrapper Costing Details</div>
          <div className="panel-sub">Art paper / cover material — Final Sheets = Base + Wastage + Make-ready</div>
        </div>
        {line && <span className="pill pill-confirmed">Calculated</span>}
      </div>
      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="GSM" value={form.wrapper_gsm} onChange={v => update('wrapper_gsm', v)} />
        <Field label="UPS" value={form.wrapper_ups} onChange={v => update('wrapper_ups', v)} />
        <Field label="Sheet L (mm)" value={form.wrapper_sheet_length_mm} onChange={v => update('wrapper_sheet_length_mm', v)} />
        <Field label="Sheet W (mm)" value={form.wrapper_sheet_width_mm} onChange={v => update('wrapper_sheet_width_mm', v)} />
      </div>
      <div className="form-grid-4" style={{ marginBottom: 20 }}>
        <Field label="Wastage (%)" value={form.wrapper_wastage_percent} onChange={v => update('wrapper_wastage_percent', v)} />
        <Field label="Make-ready Sheets" value={form.wrapper_make_ready_sheets} onChange={v => update('wrapper_make_ready_sheets', v)} />
      </div>
      <div style={{ marginBottom: 20 }}>
        <div className="form-label" style={{ marginBottom: 8 }}>Rate Configuration (₹/kg)</div>
        <RateConfigRow
          masterRate={form.wrapper_master_rate}
          overrideRate={form.wrapper_override_rate}
          effectiveRate={effectiveRate}
          onOverrideChange={v => update('wrapper_override_rate', v)}
          onReset={() => update('wrapper_override_rate', null)}
        />
      </div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Total Cost = Final Sheets × KG/Sheet × Rate/KG" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Printing Module ────────────────────────────────────────
function PrintingModule({ form, update, masterRates, line, onCalculate, calculating }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">Printing Costing Details</div>
          <div className="panel-sub">Consumes Final Wrapper Sheets — tiered rate by sheet size</div>
        </div>
        {line && <span className="pill pill-confirmed">Calculated</span>}
      </div>

      {/* Printing preview box */}
      <div className="grid-col-6-4" style={{ gap: 16, marginBottom: 20 }}>
        <div>
          <div className="form-grid-4" style={{ marginBottom: 16 }}>
            <Field label="Printing Type" type="text" value="Offset Printing" readOnly />
            <Field label="Colors" type="text" value="4-Color (CMYK)" readOnly />
            <Field label="Printing Size (mm)" type="text" value={`${form.lamination_sheet_length_in * 25.4 | 0} × ${form.lamination_sheet_width_in * 25.4 | 0}`} readOnly />
          </div>
          <div className="form-grid-4" style={{ marginBottom: 16 }}>
            <Field label="UPS / Quantity" value={form.wrapper_ups} readOnly />
            <Field label="Order Quantity" value={form.quantity} readOnly />
            <Field label="Wastage (%)" value={form.wrapper_wastage_percent} readOnly />
          </div>
          <div style={{ marginBottom: 16 }}>
            <div className="form-label" style={{ marginBottom: 8 }}>First 1,000 Sheets Rate (₹ flat)</div>
            <RateConfigRow
              masterRate={form.print_master_rate}
              overrideRate={form.print_override_rate}
              effectiveRate={form.print_override_rate ?? form.print_master_rate}
              onOverrideChange={v => update('print_override_rate', v)}
              onReset={() => update('print_override_rate', null)}
              label="First 1,000 sheets (₹ flat)"
            />
            <div style={{ fontSize: 11, color: 'var(--muted-2)', marginTop: 6 }}>Additional sheets: ₹ {Number(form.print_additional_rate || 0).toFixed(2)} each</div>
          </div>
          <div>
            <div className="form-label" style={{ marginBottom: 8 }}>Sheet Size</div>
            <Field label="" options={['15x20', '20x28', '28x40']} value={form.print_sheet_size} onChange={value => {
              const [firstKey, additionalKey] = PRINT_RATE_KEYS[value];
              update('print_sheet_size', value);
              update('print_master_rate', masterRates?.[firstKey] ?? form.print_master_rate);
              update('print_additional_rate', masterRates?.[additionalKey] ?? form.print_additional_rate);
            }} />
          </div>
        </div>
        {/* Box preview */}
        <div style={{ background: 'var(--orange-light)', borderRadius: 10, padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            width: 110, height: 100,
            background: 'linear-gradient(135deg, #FF7A5C, #FF5A3A)',
            borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 24px rgba(255,90,58,0.3)', position: 'relative',
          }}>
            <Package size={40} color="rgba(255,255,255,0.9)" />
            <BrandLogo width={52} style={{ position: 'absolute', bottom: 8, left: 8, background: '#fff', padding: 2, borderRadius: 2 }} />
          </div>
        </div>
      </div>

      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Total Cost = First 1000 Rate + (Sheets − 1000) × Additional Rate" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Lamination ─────────────────────────────────────────────
function LaminationModule({ form, update, masterRates, line, onCalculate, calculating }) {
  const masterRate = form.lam_master_rate;
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Lamination Costing Details</div>
        <div className="panel-sub">Cost = Sheet Area × Rate / 100 sq.in × Final Wrapper Sheets</div>
      </div>
      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="Type" options={['thermal', 'cold', 'dry']} value={form.lamination_type} onChange={value => {
          update('lamination_type', value);
          update('lam_master_rate', masterRates?.[`lamination_${value}`] ?? form.lam_master_rate);
        }} />
        <Field label="Sheet L (in)" value={form.lamination_sheet_length_in} onChange={v => update('lamination_sheet_length_in', v)} />
        <Field label="Sheet W (in)" value={form.lamination_sheet_width_in} onChange={v => update('lamination_sheet_width_in', v)} />
      </div>
      <RateConfigRow masterRate={masterRate} overrideRate={form.lam_override_rate} effectiveRate={form.lam_override_rate ?? masterRate} onOverrideChange={v => update('lam_override_rate', v)} onReset={() => update('lam_override_rate', null)} />
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Cost/Sheet = L(in) × W(in) × Rate / 100" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Glue ───────────────────────────────────────────────────
function GlueModule({ form, update, masterRates, line, onCalculate, calculating }) {
  const updateLine = (i, key, val) => {
    const next = form.glue_lines.map((l, idx) => idx === i ? { ...l, [key]: val } : l);
    update('glue_lines', next);
  };
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Glue Costing Details</div>
        <div className="panel-sub">Weight = Area × 0.00064516 × GSM / 1000; Cost = Weight × Rate/KG</div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 10, marginBottom: 8 }}>
          <span className="form-label">Component</span>
          <span className="form-label">Area (sq.in)</span>
          <span className="form-label">GSM</span>
          <span className="form-label">Rate (₹/kg)</span>
        </div>
        {form.glue_lines.map((gl, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 10, marginBottom: 8 }}>
            <input className="form-input" type="text" value={gl.name} onChange={e => updateLine(i, 'name', e.target.value)} />
            <input className="form-input" type="number" value={gl.area_sq_in} onChange={e => updateLine(i, 'area_sq_in', Number(e.target.value))} />
            <input className="form-input" type="number" value={gl.gsm} onChange={e => updateLine(i, 'gsm', Number(e.target.value))} />
            <input className="form-input" type="number" value={gl.rate_per_kg} onChange={e => updateLine(i, 'rate_per_kg', Number(e.target.value))} />
          </div>
        ))}
        <button className="btn btn-secondary btn-sm" onClick={() => update('glue_lines', [...form.glue_lines, { name: 'Component', area_sq_in: 0, gsm: 20, rate_per_kg: masterRates?.glue_rate_per_kg ?? 90 }])}>
          <Plus size={13} /> Add Component
        </button>
      </div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Glue Weight = Area × 0.00064516 × GSM / 1000" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Punching ───────────────────────────────────────────────
function PunchingModule({ form, update, masterRates, line, onCalculate, calculating }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Punching Costing Details</div>
        <div className="panel-sub">Cost = (Qty ÷ Speed + Setup Hrs) × Machine Rate</div>
      </div>
      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="Material" options={['Kappa', 'Wrapper', 'FBB', 'Duplex', 'Foam/EVA/EPE']} value={form.punching_material} onChange={value => {
          update('punching_material', value);
          update('punching_speed', masterRates?.[PUNCH_SPEED_KEYS[value]] ?? form.punching_speed);
        }} />
        <Field label="Machine Rate (₹/hr)" value={form.punching_machine_rate_per_hour} onChange={v => update('punching_machine_rate_per_hour', v)} />
      </div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Punching Cost = (Production Hrs + Setup Hrs) × Machine Rate" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Embellishments ─────────────────────────────────────────
function EmbellishmentsModule({ form, update, line, onCalculate, calculating }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Embellishments Costing Details</div>
        <div className="panel-sub">Applied cost = max(Area × Rate + Setup, Minimum)</div>
      </div>
      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="Type" options={['Gold Foil', 'Silver Foil', 'Rose Gold', 'Spot UV', 'Drip-Off', 'Embossing', 'Debossing']} value={form.embellishment_type} onChange={v => update('embellishment_type', v)} />
        <Field label="Area (sq.in)" value={form.embellishment_area_sq_in} onChange={v => update('embellishment_area_sq_in', v)} />
        <Field label="Rate (₹/sq.in)" value={form.embellishment_rate_per_sq_in} onChange={v => update('embellishment_rate_per_sq_in', v)} />
        <Field label="Setup (₹)" value={form.embellishment_setup} onChange={v => update('embellishment_setup', v)} />
      </div>
      <div className="form-grid-4" style={{ marginBottom: 16 }}>
        <Field label="Minimum Charge (₹)" value={form.embellishment_minimum} onChange={v => update('embellishment_minimum', v)} />
      </div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} formula="Embellishment Cost = max(Area × Rate + Setup, Minimum)" /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Accessories ────────────────────────────────────────────
function AccessoriesModule({ form, update, line, onCalculate, calculating }) {
  const updateAcc = (i, key, val) => {
    const next = form.accessories.map((a, idx) => idx === i ? { ...a, [key]: val } : a);
    update('accessories', next);
  };
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">Accessories Costing</div>
        <div className="panel-sub">Total = Qty per Box × Unit Cost × Order Quantity</div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 10, marginBottom: 8 }}>
          <span className="form-label">Item</span>
          <span className="form-label">Qty / Box</span>
          <span className="form-label">Unit Cost (₹)</span>
        </div>
        {form.accessories.map((a, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 10, marginBottom: 8 }}>
            <input className="form-input" type="text" value={a.name} onChange={e => updateAcc(i, 'name', e.target.value)} />
            <input className="form-input" type="number" value={a.quantity_per_box} onChange={e => updateAcc(i, 'quantity_per_box', Number(e.target.value))} />
            <input className="form-input" type="number" value={a.unit_cost} onChange={e => updateAcc(i, 'unit_cost', Number(e.target.value))} />
          </div>
        ))}
        <button className="btn btn-secondary btn-sm" onClick={() => update('accessories', [...form.accessories, { name: 'Accessory', quantity_per_box: 1, unit_cost: 0 }])}>
          <Plus size={13} /> Add Accessory
        </button>
      </div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {line ? <CalcTracePanel rows={line.trace.map(t => ({ label: t.label, value: t.value }))} /> : <div />}
        <ModuleResultCard line={line} onCalculate={onCalculate} calculating={calculating} />
      </div>
    </div>
  );
}

// ── Config Required ────────────────────────────────────────
function ConfigRequiredModule({ title, desc }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">{title}</div>
        <span className="pill pill-required">CONFIGURATION REQUIRED</span>
      </div>
      <div className="warn-banner">
        <AlertCircle size={15} />
        <div>
          <strong style={{ fontSize: 12 }}>Formula not yet configured</strong>
          <div style={{ fontSize: 11, marginTop: 2 }}>{desc}</div>
        </div>
      </div>
      <div style={{ marginTop: 16, padding: '16px', background: 'var(--line-2)', borderRadius: 8, fontSize: 12, color: 'var(--muted)' }}>
        This module will display <strong>CONFIGURATION REQUIRED</strong> until the business formula is confirmed and configured in Master Configuration.
      </div>
    </div>
  );
}

// ── Step 4: Summary & Margin ───────────────────────────────
function StepSummary({ form, setForm, result, onCalculate, onNext, onBack }) {
  const [margin, setMargin] = useState(form.margin_percent);

  const PIE_COLORS = ['#FF5A3A', '#FF7A5C', '#FFB09C', '#FFC352', '#86B9EE', '#A78BFA', '#48BB78', '#F6AD55', '#DCE1E5', '#CBD5E0'];

  const pieData = result?.lines?.map((l, i) => ({
    name: l.module, value: l.total_cost, pct: l.weightage_percent, color: PIE_COLORS[i % PIE_COLORS.length],
  })) || [];

  const sp = result ? result.total_manufacturing_cost / result.order_quantity / (1 - margin / 100) : 0;

  return (
    <div>
      {!result && (
        <div className="info-banner" style={{ marginBottom: 16 }}>
          <Info size={15} />
          <span>Click <strong>Calculate All Modules</strong> in the previous step to generate costing data, then come back to see the summary.</span>
          <button className="btn btn-primary btn-sm" onClick={onCalculate} style={{ marginLeft: 'auto' }}>Calculate Now</button>
        </div>
      )}

      <div className="grid-col-6-4" style={{ gap: 16, marginBottom: 16 }}>
        {/* Module table */}
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--line)' }}>
            <div className="panel-title">Costing Summary (Per Box)</div>
            <div className="panel-sub">All configured module outputs</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Module</th>
                <th style={{ textAlign: 'right' }}>Total Cost (₹)</th>
                <th style={{ textAlign: 'right' }}>Cost / Box (₹)</th>
                <th style={{ textAlign: 'right' }}>Weightage (%)</th>
              </tr>
            </thead>
            <tbody>
              {result?.lines?.map((l, i) => (
                <tr key={l.module}>
                  <td style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
                    {l.module}
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>{money(l.total_cost)}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 700, color: 'var(--orange)' }}>{money(l.cost_per_box)}</td>
                  <td style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{l.weightage_percent?.toFixed(1)}%</span>
                  </td>
                </tr>
              ))}
              {result && (
                <tr style={{ background: 'var(--orange-light)' }}>
                  <td><strong>Total Manufacturing Cost</strong></td>
                  <td style={{ textAlign: 'right' }}><strong style={{ fontFamily: 'Manrope', fontSize: 14 }}>{money(result.total_manufacturing_cost)}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong style={{ fontFamily: 'Manrope', fontSize: 14, color: 'var(--orange)' }}>{money(result.cost_per_box)}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>100%</strong></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Margin & Selling Price */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Pie chart */}
          {result && (
            <div className="panel">
              <div className="panel-title" style={{ marginBottom: 12 }}>Module Weightage</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <ResponsiveContainer width={120} height={120}>
                  <PieChart>
                    <Pie data={pieData} cx={55} cy={55} innerRadius={32} outerRadius={55} dataKey="value" paddingAngle={2}>
                      {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1 }}>
                  {pieData.slice(0, 6).map(d => (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontSize: 11 }}>
                      <div style={{ width: 7, height: 7, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                      <span style={{ flex: 1, color: 'var(--muted)' }}>{d.name}</span>
                      <strong style={{ fontFamily: 'Manrope' }}>{d.pct?.toFixed(1)}%</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Margin panel */}
          <div className="panel" style={{ background: '#262A30', border: 'none', color: '#fff' }}>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#9CA3AF', marginBottom: 8 }}>Margin & Selling Price</div>
            <div style={{ fontFamily: 'Manrope', fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>Manufacturing Cost / Box</div>
            <div style={{ fontFamily: 'Manrope', fontSize: 26, fontWeight: 800, borderBottom: '1px solid #454950', paddingBottom: 14, marginBottom: 14 }}>
              ₹ {result?.cost_per_box?.toFixed(2) || '—'}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>Margin Type</span>
              <span style={{ fontSize: 12, fontWeight: 600 }}>Percentage</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>Margin (%)</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <input
                  type="number"
                  value={margin}
                  onChange={e => { setMargin(Number(e.target.value)); setForm(f => ({ ...f, margin_percent: Number(e.target.value) })); }}
                  style={{ width: 50, background: '#3B4047', border: '1px solid #535860', color: '#fff', borderRadius: 5, padding: '4px 8px', fontSize: 12, textAlign: 'right' }}
                />
                <span style={{ fontSize: 12 }}>%</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderTop: '1px solid #454950', borderBottom: '1px solid #454950', marginBottom: 12 }}>
              <span style={{ fontSize: 12, color: '#9CA3AF' }}>Selling Price / Box</span>
              <span style={{ fontFamily: 'Manrope', fontSize: 20, fontWeight: 800, color: '#FF9B87' }}>
                ₹ {result ? sp.toFixed(2) : '—'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
              <span style={{ color: '#9CA3AF' }}>Order Quantity</span>
              <span style={{ fontWeight: 600 }}>{form.quantity.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 700, marginBottom: 16 }}>
              <span style={{ color: '#9CA3AF' }}>Total Order Value</span>
              <span style={{ color: '#FF9B87', fontFamily: 'Manrope' }}>₹ {result ? (sp * form.quantity).toLocaleString('en-IN', { maximumFractionDigits: 0 }) : '—'}</span>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <button className="btn btn-secondary" onClick={onBack}><ArrowLeft size={15} /> Back</button>
        <button className="btn btn-primary" onClick={onNext}>Continue to Quotation <ArrowRight size={15} /></button>
      </div>
    </div>
  );
}

// ── Step 5: Quotation / Proforma ───────────────────────────
function StepQuotation({ form, result, customer, jobName, onBack, onSave, saving }) {
  const [docType, setDocType] = useState('Quotation');
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
  const [pdfAction, setPdfAction] = useState('');
  const [pdfError, setPdfError] = useState('');
  const [numberEdited, setNumberEdited] = useState(false);
  const [customerRecords, setCustomerRecords] = useState([]);
  const [addressEdited, setAddressEdited] = useState(false);
  const [document, setDocument] = useState(() => {
    const localDate = new Date();
    localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
    return {
      quotation_number: '', document_date: localDate.toISOString().slice(0, 10),
      customer_name: customer, customer_address: '', job_name: jobName,
      order_quantity: form.quantity,
      unit_price: result ? result.cost_per_box / (1 - form.margin_percent / 100) : 0,
      gst_percent: 18, validity_days: 15,
      notes: '1. Prices are valid for 15 days.\n2. This is a budgetary quotation.\n3. Final pricing may vary based on final artwork and specifications.',
    };
  });
  const updateDocument = (key, value) => setDocument(current => ({ ...current, [key]: value }));

  useEffect(() => {
    let active = true;
    getNextQuotationNumber(docType).then(({ quotation_number }) => {
      if (active && !numberEdited && quotation_number) {
        setDocument(current => ({ ...current, quotation_number }));
      }
    }).catch(() => {
      if (!active || numberEdited) return;
      const localDate = new Date();
      const datePart = `${localDate.getFullYear()}${String(localDate.getMonth() + 1).padStart(2, '0')}${String(localDate.getDate()).padStart(2, '0')}`;
      const prefix = docType === 'Proforma Invoice' ? 'PI' : 'QUO';
      setDocument(current => ({ ...current, quotation_number: current.quotation_number || `${prefix}-${datePart}-${Date.now().toString().slice(-5)}` }));
    });
    return () => { active = false; };
  }, [docType, numberEdited]);

  useEffect(() => {
    let active = true;
    listCustomers().then(records => { if (active && Array.isArray(records)) setCustomerRecords(records); }).catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (addressEdited) return;
    const selected = customerRecords.find(record => record.name?.trim().toLowerCase() === document.customer_name.trim().toLowerCase());
    const address = selected
      ? [selected.address, [selected.city, selected.state].filter(Boolean).join(', ')].filter(Boolean).join('\n')
      : '';
    if (address !== document.customer_address) updateDocument('customer_address', address);
  }, [addressEdited, customerRecords, document.customer_address, document.customer_name]);

  const formatDate = value => value ? new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';
  const today = formatDate(document.document_date);
  const quantity = Number(document.order_quantity) || 0;
  const unitPrice = Number(document.unit_price) || 0;
  const total = quantity * unitPrice;
  const gstPercent = Number(document.gst_percent) || 0;
  const gst = total * gstPercent / 100;
  const grandTotal = total + gst;
  const validUntil = new Date(`${document.document_date}T00:00:00`);
  validUntil.setDate(validUntil.getDate() + (Number(document.validity_days) || 0));
  const validUntilText = Number.isNaN(validUntil.getTime()) ? '—' : formatDate(validUntil.toISOString().slice(0, 10));

  const getDocumentPdf = async () => previewQuotationPdf({
    ...document,
    quotation_number: document.quotation_number.trim() || null,
    doc_type: docType,
    order_quantity: Number(document.order_quantity),
    unit_price: Number(document.unit_price),
    gst_percent: Number(document.gst_percent),
    validity_days: Number(document.validity_days),
  });

  const handlePdfAction = async (action) => {
    setPdfAction(action);
    setPdfError('');
    try {
      const blob = await getDocumentPdf();
      const url = URL.createObjectURL(blob);
      if (action === 'preview') {
        if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
        setPdfPreviewUrl(url);
      } else {
        const link = window.document.createElement('a');
        link.href = url;
        link.download = `${document.quotation_number.trim() || docType.replaceAll(' ', '-')}.pdf`;
        link.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      setPdfError(error.message || 'Unable to generate PDF');
    } finally {
      setPdfAction('');
    }
  };

  const closePdfPreview = () => {
    if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
    setPdfPreviewUrl(null);
  };

  return (
    <div>
      <div className="grid-col-6-4" style={{ gap: 16 }}>
        {/* Left: settings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Doc type */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 14 }}>Document Type</div>
            <div style={{ display: 'flex', gap: 10 }}>
              {['Quotation', 'Proforma Invoice'].map(t => (
                <button
                  key={t}
                  onClick={() => setDocType(t)}
                  style={{
                    flex: 1, padding: '9px', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer',
                    border: `1.5px solid ${docType === t ? 'var(--orange)' : 'var(--line)'}`,
                    background: docType === t ? 'var(--orange-light)' : 'var(--panel)',
                    color: docType === t ? 'var(--orange)' : 'var(--muted)',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Details */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 14 }}>Document Details</div>
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Quotation No.</label>
                <input className="form-input" value={document.quotation_number} onChange={event => { setNumberEdited(Boolean(event.target.value)); updateDocument('quotation_number', event.target.value); }} />
              </div>
              <div className="form-group">
                <label className="form-label">Date</label>
                <input className="form-input" type="date" value={document.document_date} onChange={event => updateDocument('document_date', event.target.value)} />
              </div>
            </div>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Customer</label>
              <input className="form-input" value={document.customer_name} onChange={event => updateDocument('customer_name', event.target.value)} />
            </div>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Billing Address</label>
              <textarea className="form-input" rows={2} value={document.customer_address} onChange={event => { setAddressEdited(true); updateDocument('customer_address', event.target.value); }} />
            </div>
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="form-label">Job / Product Description</label>
              <input className="form-input" value={document.job_name} onChange={event => updateDocument('job_name', event.target.value)} />
            </div>
            <div className="form-grid-2" style={{ marginTop: 12 }}>
              <div className="form-group">
                <label className="form-label">Quantity</label>
                <input className="form-input" type="number" min="1" value={document.order_quantity} onChange={event => updateDocument('order_quantity', event.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Unit Price (₹)</label>
                <input className="form-input" type="number" min="0" step="0.01" value={document.unit_price} onChange={event => updateDocument('unit_price', event.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">GST (%)</label>
                <input className="form-input" type="number" min="0" max="99.99" step="0.01" value={document.gst_percent} onChange={event => updateDocument('gst_percent', event.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Validity (days)</label>
                <input className="form-input" type="number" min="0" value={document.validity_days} onChange={event => updateDocument('validity_days', event.target.value)} />
              </div>
            </div>
          </div>

          {/* Terms */}
          <div className="panel">
            <div className="panel-title" style={{ marginBottom: 12 }}>Terms & Conditions</div>
            <textarea className="form-input" rows={5} value={document.notes} onChange={event => updateDocument('notes', event.target.value)} aria-label="Terms and conditions" />
          </div>
        </div>

        {/* Right: preview */}
        <div className="panel" style={{ padding: 24 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div style={{ fontFamily: 'Manrope', fontSize: 22, fontWeight: 800, color: '#1A1D23' }}>
              Pac<span style={{ color: '#FF5A3A' }}>fully</span>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: 'Manrope', fontSize: 15, fontWeight: 700 }}>{docType.toUpperCase()}</div>
              <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>{document.quotation_number || 'Number assigned on save'}</div>
              <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>{today}</div>
              <div style={{ fontSize: 10, color: 'var(--muted-2)' }}>Valid until {validUntilText}</div>
            </div>
          </div>

          <div style={{ borderTop: '2px solid var(--orange)', marginBottom: 16 }} />

          {/* Bill to */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--muted-2)', marginBottom: 4 }}>Bill To</div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>{document.customer_name || 'Customer name'}</div>
            <div style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'pre-line' }}>{document.customer_address || 'Billing address'}</div>
          </div>

          {/* Line items */}
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', fontSize: 10, color: 'var(--muted-2)', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>Description</th>
                <th style={{ textAlign: 'right', fontSize: 10, color: 'var(--muted-2)', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>Qty</th>
                <th style={{ textAlign: 'right', fontSize: 10, color: 'var(--muted-2)', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>Unit Price</th>
                <th style={{ textAlign: 'right', fontSize: 10, color: 'var(--muted-2)', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontSize: 12, padding: '8px 0', borderBottom: '1px solid var(--line-2)' }}>{document.job_name || 'Packaging'}</td>
                <td style={{ textAlign: 'right', fontSize: 12, padding: '8px 0', borderBottom: '1px solid var(--line-2)' }}>{quantity.toLocaleString()}</td>
                <td style={{ textAlign: 'right', fontSize: 12, padding: '8px 0', borderBottom: '1px solid var(--line-2)', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {unitPrice.toFixed(2)}</td>
                <td style={{ textAlign: 'right', fontSize: 12, padding: '8px 0', borderBottom: '1px solid var(--line-2)', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
              </tr>
            </tbody>
          </table>

          {/* Totals */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: 'var(--muted)' }}>Subtotal</span>
              <span style={{ fontFamily: 'Manrope', fontWeight: 600 }}>₹ {total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: 'var(--muted)' }}>GST ({gstPercent}%)</span>
              <span style={{ fontFamily: 'Manrope', fontWeight: 600 }}>₹ {gst.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1.5px solid var(--ink-2)', borderBottom: '1.5px solid var(--ink-2)', marginTop: 4 }}>
              <strong style={{ fontSize: 14 }}>Total Order Value</strong>
              <strong style={{ fontFamily: 'Manrope', fontSize: 16, color: 'var(--orange)' }}>₹ {grandTotal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</strong>
            </div>
          </div>

          {document.notes.split('\n').filter(Boolean).length > 0 && (
            <div style={{ fontSize: 10, color: 'var(--muted-2)', marginBottom: 12, whiteSpace: 'pre-line' }}>{document.notes}</div>
          )}

          <div style={{ fontSize: 11, color: 'var(--muted-2)', marginBottom: 14 }}>
            Internal manufacturing cost, module breakdown, and margin are intentionally excluded from this document.
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => handlePdfAction('preview')} disabled={Boolean(pdfAction)}>
              <Eye size={13} /> {pdfAction === 'preview' ? 'Generating...' : 'Preview PDF'}
            </button>
            <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => handlePdfAction('download')} disabled={Boolean(pdfAction)}>
              <Download size={13} /> {pdfAction === 'download' ? 'Generating...' : 'Download PDF'}
            </button>
          </div>
          {pdfError && <div role="alert" style={{ color: '#C53030', fontSize: 11, marginTop: 10 }}>{pdfError}</div>}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <button className="btn btn-secondary" onClick={onBack}><ArrowLeft size={15} /> Back</button>
        <button className="btn btn-primary btn-lg" onClick={() => onSave({ ...document, doc_type: docType })} disabled={saving}>
          <Check size={15} /> {saving ? 'Saving...' : 'Save & Finalize'}
        </button>
      </div>
      {pdfPreviewUrl && (
        <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) closePdfPreview(); }}>
          <div role="dialog" aria-modal="true" aria-label={`${docType} PDF preview`} style={{ background: '#fff', borderRadius: 8, width: 'min(900px, calc(100vw - 32px))', height: '88vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
              <strong style={{ fontSize: 13 }}>{docType} PDF Preview</strong>
              <button className="modal-close" aria-label="Close preview" onClick={closePdfPreview}><X size={16} /></button>
            </div>
            <iframe src={pdfPreviewUrl} title={`${docType} preview`} style={{ flex: 1, border: 0 }} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Cost Estimator Page ───────────────────────────────
export default function CostEstimator() {
  const navigate = useNavigate();
  const [step,       setStep]       = useState(0);
  const [form,       setForm]       = useState(INITIAL_FORM);
  const [masterRates, setMasterRates] = useState(null);
  const [result,     setResult]     = useState(null);
  const [moduleResults, setModuleResults] = useState({});
  const [moduleSnapshots, setModuleSnapshots] = useState({});
  const [calculatingAll, setCalculatingAll] = useState(false);
  const [calculatingModule, setCalculatingModule] = useState(null);
  const [customer,   setCustomer]   = useState('Luxe Beauty Pvt Ltd');
  const [jobName,    setJobName]    = useState('Premium Rigid Box - Skincare');
  const [toast,      setToast]      = useState(null);
  const [estimateId, setEstimateId] = useState(null);   // persisted DB id
  const [saving,     setSaving]     = useState(false);

  const showToast = (msg, isErr = false) => {
    setToast({ msg, isErr });
    setTimeout(() => setToast(null), 3500);
  };

  useEffect(() => {
    let active = true;
    getMasterConfig().then(({ rates }) => {
      if (!active || !rates) return;
      setMasterRates(rates);
      setForm(current => {
        const [printFirstKey, printAdditionalKey] = PRINT_RATE_KEYS[current.print_sheet_size];
        const materialRateKey = { 'Kappa Board': 'kappa_rate_per_kg', FBB: 'fbb_rate_per_kg', 'Duplex Board': 'duplex_board_rate_per_kg' }[current.kappa_material];
        const punchingSpeedKey = PUNCH_SPEED_KEYS[current.punching_material];
        return {
          ...current,
          kappa_master_rate: rates[materialRateKey] ?? current.kappa_master_rate,
          kappa_rate_per_kg: rates[materialRateKey] ?? current.kappa_rate_per_kg,
          wrapper_master_rate: rates.wrapper_rate_per_kg ?? current.wrapper_master_rate,
          wrapper_rate_per_kg: rates.wrapper_rate_per_kg ?? current.wrapper_rate_per_kg,
          wrapper_make_ready_sheets: rates.wrapper_make_ready_sheets ?? current.wrapper_make_ready_sheets,
          print_master_rate: rates[printFirstKey] ?? current.print_master_rate,
          print_additional_rate: rates[printAdditionalKey] ?? current.print_additional_rate,
          lam_master_rate: rates[`lamination_${current.lamination_type}`] ?? current.lam_master_rate,
          glue_lines: current.glue_lines.map(line => ({ ...line, rate_per_kg: rates.glue_rate_per_kg ?? line.rate_per_kg })),
          punching_machine_rate_per_hour: rates.punching_machine_rate_per_hour ?? current.punching_machine_rate_per_hour,
          punching_speed: rates[punchingSpeedKey] ?? current.punching_speed,
          punching_setup_hours: rates.punching_setup_hours ?? current.punching_setup_hours,
          embellishment_rate_per_sq_in: rates.embellishment_rate_per_sq_in ?? current.embellishment_rate_per_sq_in,
          embellishment_setup: rates.embellishment_setup ?? current.embellishment_setup,
          embellishment_minimum: rates.embellishment_minimum ?? current.embellishment_minimum,
        };
      });
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  // ── Calculate (stateless — no DB write) ────────────────
  const handleCalculate = async () => {
    if (calculatingAll || calculatingModule) return;
    setCalculatingAll(true);
    try {
      const res = await fetch(`${API_BASE}/estimates/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || 'Unable to calculate estimate');
      }
      const data = await res.json();
      setResult(data);
      setModuleResults({});
      setModuleSnapshots({ Wrapper: moduleInputs('Wrapper', form) });
      showToast('Calculation complete — all modules updated');
    } catch (error) {
      showToast(error.message || 'Calculation failed. Please try again.', true);
    } finally {
      setCalculatingAll(false);
    }
  };

  const handleCalculateModule = async (module) => {
    if (calculatingAll || calculatingModule) return;
    const wrapperSnapshot = moduleSnapshots.Wrapper;
    const currentWrapperInputs = moduleInputs('Wrapper', form);
    const wrapperIsCurrent = wrapperSnapshot
      && JSON.stringify(wrapperSnapshot) === JSON.stringify(currentWrapperInputs);
    const wrapperLine = moduleResults.Wrapper;
    const wrapperFinalSheets = wrapperIsCurrent
      ? wrapperLine?.wrapper_final_sheets ?? result?.wrapper_final_sheets
      : undefined;
    const needsWrapper = ['Printing', 'Lamination'].includes(module)
      || (module === 'Punching' && form.punching_material === 'Wrapper');

    if (needsWrapper && !wrapperFinalSheets) {
      showToast('Calculate Wrapper first to determine current Final Wrapper Sheets.', true);
      return;
    }

    setCalculatingModule(module);
    try {
      const inputs = moduleInputs(module, form, wrapperFinalSheets);
      const res = await fetch(`${API_BASE}/estimates/calculate/module`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module, inputs, estimate_id: estimateId }),
      });
      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        const detail = Array.isArray(error.detail)
          ? error.detail.map(item => item.msg).join('; ')
          : error.detail;
        throw new Error(detail || `Unable to calculate ${module}`);
      }
      const data = await res.json();
      const nextLine = { ...data.line };
      if (module === 'Wrapper') nextLine.wrapper_final_sheets = data.wrapper_final_sheets;

      if (nextLine.weightage_percent == null && result?.lines) {
        const required = ['Kappa', 'Wrapper', 'Printing', 'Lamination', 'Glue', 'Punching', 'Embellishments', 'Accessories'];
        if (required.every(name => name === module || result.lines.some(item => item.module === name))) {
          const total = result.lines.reduce((sum, item) => sum + (item.module === module ? nextLine.total_cost : item.total_cost), 0);
          nextLine.weightage_percent = total ? Number((nextLine.total_cost / total * 100).toFixed(4)) : 0;
        }
      }

      setModuleResults(previous => ({ ...previous, [module]: nextLine }));
      if (module === 'Wrapper') {
        setModuleSnapshots(previous => ({ ...previous, Wrapper: moduleInputs('Wrapper', form) }));
      }
      showToast(`${module} calculation complete`);
    } catch (error) {
      showToast(error.message || `${module} calculation failed. Please try again.`, true);
    } finally {
      setCalculatingModule(null);
    }
  };

  // ── Save Draft to DB ────────────────────────────────────
  const handleSaveDraft = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/estimates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, customer_name: customer, job_name: jobName }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setEstimateId(data.estimate_id);
      showToast(`Draft saved — ${data.estimate_number}`);
    } catch (e) {
      showToast('Backend offline — draft not saved to DB', true);
    } finally {
      setSaving(false);
    }
  };

  // ── Finalize + create quotation ─────────────────────────
  const handleSave = async (document) => {
    setSaving(true);
    try {
      const saved = await saveEstimate({ ...form, customer_name: customer, job_name: jobName });
      const eid = saved.estimate_id;
      setEstimateId(eid);

      await finalizeEstimate(eid);

      await createQuotation({
        estimate_id: eid,
        ...document,
        quotation_number: document.quotation_number?.trim() || null,
        order_quantity: Number(document.order_quantity),
        unit_price: Number(document.unit_price),
        gst_percent: Number(document.gst_percent),
        validity_days: Number(document.validity_days),
      });
      showToast(`Estimate finalized — ${saved.estimate_number}`);
      setTimeout(() => navigate('/estimates'), 1400);
    } catch (e) {
      showToast(e.message || 'Unable to save the quotation. Please try again.', true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Cost Estimator › New Estimate</span>
          <h1 style={{ marginTop: 4 }}>New Cost Estimate</h1>
          <p>Create a new packaging cost estimate with AI-powered layout analysis</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={handleSaveDraft} disabled={saving}>
            <Save size={14} /> {saving ? 'Saving…' : 'Save Draft'}
          </button>
        </div>
      </div>

      {/* Stepper */}
      <Stepper steps={STEPS} current={step} />

      {/* Steps */}
      {step === 0 && (
        <StepLayout onNext={() => setStep(1)} customer={customer} setCustomer={setCustomer} jobName={jobName} setJobName={setJobName} />
      )}
      {step === 1 && (
        <StepTechnicalData form={form} setForm={setForm} onNext={() => setStep(2)} onBack={() => setStep(0)} />
      )}
      {step === 2 && (
        <StepCostingModules form={form} setForm={setForm} masterRates={masterRates} result={result} moduleResults={moduleResults} onCalculate={handleCalculate} onCalculateModule={handleCalculateModule} calculatingAll={calculatingAll} calculatingModule={calculatingModule} onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      {step === 3 && (
        <StepSummary form={form} setForm={setForm} result={result} onCalculate={handleCalculate} onNext={() => setStep(4)} onBack={() => setStep(2)} />
      )}
      {step === 4 && (
        <StepQuotation form={form} result={result} customer={customer} jobName={jobName} onBack={() => setStep(3)} onSave={handleSave} saving={saving} />
      )}

      {/* Toast */}
      {toast && (
        <div className="toast" style={{ background: toast.isErr ? '#C53030' : 'var(--ink-2)' }}>
          {toast.isErr
            ? <AlertCircle size={15} style={{ color: '#FCA5A5' }} />
            : <CheckCircle2 size={15} className="toast-icon" />}
          {toast.msg}
        </div>
      )}
    </div>
  );
}
