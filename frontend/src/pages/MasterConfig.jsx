import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Save, AlertCircle, RotateCcw } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { getMasterConfig, saveMasterConfig } from '../services/api';

const MATERIAL_RATES = [
  { key: 'kappa_rate_per_kg', name: 'Base Material', unit: '₹/kg', master: 80, category: 'Material' },
  { key: 'wrapper_rate_per_kg', name: 'Art Paper / Wrapper', unit: '₹/kg', master: 95, category: 'Material' },
  { key: 'fbb_rate_per_kg', name: 'FBB', unit: '₹/kg', master: 88, category: 'Material' },
  { key: 'duplex_board_rate_per_kg', name: 'Duplex Board', unit: '₹/kg', master: 72, category: 'Material' },
  { key: 'glue_rate_per_kg', name: 'Glue', unit: '₹/kg', master: 90, category: 'Material' },
];

const PROCESS_RATES = [
  { key: 'print_15x20_first', name: 'Printing 15×20 — First 1000', unit: '₹ flat', master: 1500, category: 'Printing' },
  { key: 'print_15x20_additional', name: 'Printing 15×20 — Additional', unit: '₹/sheet', master: 0.40, category: 'Printing' },
  { key: 'print_20x28_first', name: 'Printing 20×28 — First 1000', unit: '₹ flat', master: 3500, category: 'Printing' },
  { key: 'print_20x28_additional', name: 'Printing 20×28 — Additional', unit: '₹/sheet', master: 0.50, category: 'Printing' },
  { key: 'print_28x40_first', name: 'Printing 28×40 — First 1000', unit: '₹ flat', master: 6500, category: 'Printing' },
  { key: 'print_28x40_additional', name: 'Printing 28×40 — Additional', unit: '₹/sheet', master: 0.80, category: 'Printing' },
  { key: 'lamination_thermal', name: 'Lamination Thermal', unit: '₹/100 sq.in', master: 1.10, category: 'Lamination' },
  { key: 'lamination_cold', name: 'Lamination Cold', unit: '₹/100 sq.in', master: 0.70, category: 'Lamination' },
  { key: 'lamination_dry', name: 'Lamination Dry', unit: '₹/100 sq.in', master: 0.80, category: 'Lamination' },
  { key: 'lamination_rate_thermal_matte', name: 'Thermal + Matte', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_thermal_gloss', name: 'Thermal + Gloss', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_thermal_soft_touch', name: 'Thermal + Soft Touch', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_thermal_other', name: 'Thermal + Other', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_cold_matte', name: 'Cold + Matte', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_cold_gloss', name: 'Cold + Gloss', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_cold_soft_touch', name: 'Cold + Soft Touch', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_cold_other', name: 'Cold + Other', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_dry_matte', name: 'Dry + Matte', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_dry_gloss', name: 'Dry + Gloss', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_dry_soft_touch', name: 'Dry + Soft Touch', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'lamination_rate_dry_other', name: 'Dry + Other', unit: '₹/100 sq.in', master: 0, category: 'Lamination Method + Finish' },
  { key: 'embellishment_rate_per_sq_in', name: 'Embellishment Rate', unit: '₹/sq.in', master: 2.5, category: 'Embellishments' },
  { key: 'embellishment_setup', name: 'Embellishment Setup', unit: '₹ flat', master: 800, category: 'Embellishments' },
  { key: 'embellishment_minimum', name: 'Embellishment Minimum', unit: '₹/box', master: 1000, category: 'Embellishments' },
];

const TABS = ['Material Rates', 'Process Rates', 'Punching', 'Make-ready Defaults', 'Conversion & Tooling'];
const PUNCHING_RATES = [
  { key: 'punching_machine_rate_per_hour', name: 'Machine Rate', unit: '₹/hour', master: 400, category: 'Punching' },
  { key: 'punching_speed_kappa', name: 'Kappa Speed', unit: 'sheets/hour', master: 400, category: 'Punching' },
  { key: 'punching_speed_wrapper', name: 'Wrapper Speed', unit: 'sheets/hour', master: 600, category: 'Punching' },
  { key: 'punching_speed_fbb', name: 'FBB Speed', unit: 'sheets/hour', master: 600, category: 'Punching' },
  { key: 'punching_speed_duplex', name: 'Duplex Speed', unit: 'sheets/hour', master: 600, category: 'Punching' },
  { key: 'punching_speed_foam', name: 'Foam / EVA / EPE Speed', unit: 'sheets/hour', master: 500, category: 'Punching' },
  { key: 'punching_setup_hours', name: 'Setup Time', unit: 'hours', master: 0.5, category: 'Punching' },
];
const MAKE_READY_RATES = [
  { key: 'wrapper_make_ready_sheets', name: 'Wrapper Make-ready Sheets', unit: 'sheets', master: 150, category: 'Wrapper' },
];
const CONVERSION_TOOLING_RATES = [
  { key: 'conversion_semi_boxes_per_hour', name: 'Semi-automatic Kappa output', unit: 'boxes/hour', master: 400, category: 'Conversion' },
  { key: 'conversion_semi_workers', name: 'Semi-automatic labour count', unit: 'workers', master: 15, category: 'Conversion' },
  { key: 'conversion_monthly_salary', name: 'Monthly salary per worker', unit: '₹/month', master: 15000, category: 'Conversion' },
  { key: 'conversion_working_days', name: 'Working days per month', unit: 'days', master: 25, category: 'Conversion' },
  { key: 'conversion_hours_per_day', name: 'Working hours per day', unit: 'hours', master: 8, category: 'Conversion' },
  { key: 'conversion_side_pasting_rate_per_box', name: 'Side pasting', unit: '₹/box', master: 0.40, category: 'Conversion' },
  { key: 'conversion_automatic_boxes_per_hour', name: 'Automatic Kappa output', unit: 'boxes/hour', master: 600, category: 'Conversion' },
  { key: 'conversion_automatic_machine_rate', name: 'Automatic machine rate', unit: '₹/hour', master: 875, category: 'Conversion' },
  { key: 'conversion_automatic_setup_rate', name: 'Automatic setup rate', unit: '₹/hour', master: 645, category: 'Conversion' },
  { key: 'conversion_automatic_setup_hours', name: 'Automatic setup time', unit: 'hours', master: 4, category: 'Conversion' },
  { key: 'conversion_contract_rate_per_box', name: 'Contract conversion rate', unit: '₹/box', master: 3, category: 'Conversion' },
  { key: 'foiling_rate_per_100_sq_in', name: 'Foiling surface rate', unit: '₹/100 sq.in', master: 3, category: 'Embellishment' },
  { key: 'spot_uv_rate_per_100_sq_in', name: 'Spot UV surface rate', unit: '₹/100 sq.in', master: 1, category: 'Embellishment' },
  { key: 'embossing_cost_per_box', name: 'Embossing direct cost', unit: '₹/box', master: 1, category: 'Embellishment' },
  { key: 'debossing_cost_per_box', name: 'Debossing direct cost', unit: '₹/box', master: 1, category: 'Embellishment' },
  { key: 'punching_die_15x20', name: 'Punching die 15×20', unit: '₹/die', master: 1500, category: 'Tooling' },
  { key: 'punching_die_20x28', name: 'Punching die 20×28', unit: '₹/die', master: 3000, category: 'Tooling' },
  { key: 'punching_die_25x36', name: 'Punching die 25×36', unit: '₹/die', master: 4000, category: 'Tooling' },
  { key: 'punching_die_28x40', name: 'Punching die 28×40', unit: '₹/die', master: 4000, category: 'Tooling' },
  { key: 'emboss_deboss_die_rate_per_sq_cm', name: 'Emboss/deboss die', unit: '₹/sq.cm', master: 5, category: 'Tooling' },
  { key: 'foil_stamp_die_rate_per_sq_cm', name: 'Foil stamp die', unit: '₹/sq.cm', master: 5, category: 'Tooling' },
];

function tabForQuery(value = '') {
  const query = (value || '').toLowerCase();
  if (/conversion|tooling|die|foil|uv|emboss|deboss/.test(query)) return 'Conversion & Tooling';
  if (/punch|foam|duplex/.test(query)) return 'Punching';
  if (/make.?ready/.test(query)) return 'Make-ready Defaults';
  if (/print|lamin|embellish/.test(query)) return 'Process Rates';
  return 'Material Rates';
}

function RateTable({ rows, onChange, searchTerm, readOnly = false }) {
  return (
    <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
      <table>
        <thead><tr><th>Rate</th><th>Category</th><th>Unit</th><th style={{ textAlign: 'right' }}>Master Rate</th><th style={{ textAlign: 'right', width: 160 }}>Current Value</th><th style={{ textAlign: 'center' }}>Reset</th></tr></thead>
        <tbody>{rows.map((row, index) => (
          <tr key={row.key}>
            <td><strong style={{ fontSize: 13 }}>{row.name}</strong></td>
            <td><span className="pill pill-orange" style={{ fontSize: 10 }}>{row.category}</span></td>
            <td style={{ fontSize: 12, color: 'var(--muted)' }}>{row.unit}</td>
            <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {row.master}</td>
            <td style={{ textAlign: 'right' }}><input type="number" min="0" step="any" value={row.value} disabled={readOnly} onChange={event => onChange(index, event.target.value === '' ? '' : Number(event.target.value))} style={{ width: 100, height: 32, border: `1px solid ${row.value !== row.master ? 'var(--orange)' : 'var(--line)'}`, borderRadius: 6, padding: '0 10px', fontSize: 13, fontFamily: 'Manrope', fontWeight: 600, textAlign: 'right', outline: 'none', background: row.value !== row.master ? 'var(--orange-light)' : 'var(--panel)' }} /></td>
            <td style={{ textAlign: 'center' }}>{row.value !== row.master && <button className="btn btn-ghost btn-sm btn-icon" disabled={readOnly} onClick={() => onChange(index, row.master)} title="Reset to master"><RotateCcw size={13} /></button>}</td>
          </tr>
        ))}
        {!rows.length && <tr><td colSpan={6} style={{ padding: 24, textAlign: 'center', color: 'var(--muted-2)' }}>{searchTerm ? `No rates match "${searchTerm}".` : 'No rates configured.'}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function MasterConfig() {
  const { user } = useAuth();
  const canEdit = user?.role === 'Administrator';
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => tabForQuery(searchParams.get('q')));
  const [search, setSearch] = useState(() => searchParams.get('q') || '');
  const [matRates, setMatRates] = useState(MATERIAL_RATES.map(row => ({ ...row, value: row.master })));
  const [procRates, setProcRates] = useState(PROCESS_RATES.map(row => ({ ...row, value: row.master })));
  const [punchRates, setPunchRates] = useState(PUNCHING_RATES.map(row => ({ ...row, value: row.master })));
  const [makeReadyRates, setMakeReadyRates] = useState(MAKE_READY_RATES.map(row => ({ ...row, value: row.master })));
  const [conversionToolingRates, setConversionToolingRates] = useState(CONVERSION_TOOLING_RATES.map(row => ({ ...row, value: row.master })));
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState('');
  const [configVersion, setConfigVersion] = useState('');

  const showToast = (m) => { setToast(m); setTimeout(() => setToast(''), 2500); };

  useEffect(() => {
    const query = searchParams.get('q') || '';
    setSearch(query);
    setActiveTab(tabForQuery(query));
  }, [searchParams]);

  useEffect(() => {
    getMasterConfig().then(({ rates = {}, version = '' }) => {
      setConfigVersion(version);
      const applyRates = rows => rows.map(row => ({ ...row, value: rates[row.key] ?? row.master }));
      setMatRates(applyRates(MATERIAL_RATES));
      setProcRates(applyRates(PROCESS_RATES));
      setPunchRates(applyRates(PUNCHING_RATES));
      setMakeReadyRates(applyRates(MAKE_READY_RATES));
      setConversionToolingRates(applyRates(CONVERSION_TOOLING_RATES));
    }).catch(error => showToast(error.message || 'Unable to load master rates'));
  }, []);

  const updateRows = (setter, index, value) => setter(rows => rows.map((row, idx) => idx === index ? { ...row, value } : row));
  const filterRows = rows => {
    const query = search.toLowerCase().replace(/s$/, '');
    return rows.filter(row => !query || `${row.name} ${row.key} ${row.category} ${row.unit}`.toLowerCase().includes(query));
  };
  const saveChanges = async () => {
    const rows = [...matRates, ...procRates, ...punchRates, ...makeReadyRates, ...conversionToolingRates];
    if (rows.some(row => row.value === '')) {
      showToast('Enter a value in each rate field before saving');
      return;
    }
    setSaving(true);
    try {
      const saved = await saveMasterConfig(Object.fromEntries(rows.map(row => [row.key, Number(row.value)])));
      setConfigVersion(saved.version || '');
      showToast('Master values saved successfully');
    } catch (error) {
      showToast(error.message || 'Unable to save master rates');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Master Configuration</span>
          <h1 style={{ marginTop: 4 }}>Master Configuration</h1>
          <p>Default rates resolve first — overridable at estimate level{configVersion ? ` · Version ${configVersion}` : ''}</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={() => {
            if (window.history.state?.idx > 0) navigate(-1);
            else navigate('/dashboard');
          }}>
            <ArrowLeft size={14} /> Back
          </button>
          <button className="btn btn-primary" onClick={saveChanges} disabled={saving || !canEdit}>
            <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="info-banner" style={{ marginBottom: 16 }}>
        <AlertCircle size={15} />
        <span>
          Master values form the default for all new estimates. Individual estimates can override these values without changing the master.
          The hierarchy is: <strong>Layout Value → Master Default → Estimate Override → Effective Value</strong>
        </span>
      </div>

      <div className="tabs-bar">
        {TABS.map(t => (
          <button key={t} className={`tab-btn ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>{t}</button>
        ))}
      </div>

      {activeTab === 'Material Rates' && (
        <RateTable rows={filterRows(matRates)} searchTerm={search} onChange={(index, value) => updateRows(setMatRates, index, value)} readOnly={!canEdit} />
      )}

      {activeTab === 'Process Rates' && (
        <RateTable rows={filterRows(procRates)} searchTerm={search} onChange={(index, value) => updateRows(setProcRates, index, value)} readOnly={!canEdit} />
      )}

      {activeTab === 'Punching' && <RateTable rows={filterRows(punchRates)} searchTerm={search} onChange={(index, value) => updateRows(setPunchRates, index, value)} readOnly={!canEdit} />}

      {activeTab === 'Make-ready Defaults' && <RateTable rows={filterRows(makeReadyRates)} searchTerm={search} onChange={(index, value) => updateRows(setMakeReadyRates, index, value)} readOnly={!canEdit} />}

      {activeTab === 'Conversion & Tooling' && <RateTable rows={filterRows(conversionToolingRates)} searchTerm={search} onChange={(index, value) => updateRows(setConversionToolingRates, index, value)} readOnly={!canEdit} />}

      {toast && (
        <div className="toast">
          <Save size={14} style={{ color: '#72D38D' }} />
          {toast}
        </div>
      )}
    </div>
  );
}
