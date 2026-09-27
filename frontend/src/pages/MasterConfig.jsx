import React, { useState } from 'react';
import { Save, Plus, AlertCircle, RotateCcw } from 'lucide-react';

const MATERIAL_RATES = [
  { material: 'Kappa Board', unit: '₹/kg', master: 80, category: 'Material' },
  { material: 'Art Paper / Wrapper', unit: '₹/kg', master: 95, category: 'Material' },
  { material: 'FBB', unit: '₹/kg', master: 88, category: 'Material' },
  { material: 'Duplex Board', unit: '₹/kg', master: 72, category: 'Material' },
  { material: 'Glue', unit: '₹/kg', master: 90, category: 'Material' },
];

const PROCESS_RATES = [
  { process: 'Printing 15×20 — First 1000', unit: '₹ flat', master: 1500, category: 'Printing' },
  { process: 'Printing 15×20 — Additional', unit: '₹/sheet', master: 0.40, category: 'Printing' },
  { process: 'Printing 20×28 — First 1000', unit: '₹ flat', master: 3500, category: 'Printing' },
  { process: 'Printing 20×28 — Additional', unit: '₹/sheet', master: 0.50, category: 'Printing' },
  { process: 'Printing 28×40 — First 1000', unit: '₹ flat', master: 6500, category: 'Printing' },
  { process: 'Printing 28×40 — Additional', unit: '₹/sheet', master: 0.80, category: 'Printing' },
  { process: 'Lamination Thermal', unit: '₹/100 sq.in', master: 1.10, category: 'Lamination' },
  { process: 'Lamination Cold', unit: '₹/100 sq.in', master: 0.70, category: 'Lamination' },
  { process: 'Lamination Dry', unit: '₹/100 sq.in', master: 0.80, category: 'Lamination' },
];

const TABS = ['Material Rates', 'Process Rates', 'Punching', 'Make-ready Defaults'];

export default function MasterConfig() {
  const [activeTab, setActiveTab] = useState('Material Rates');
  const [matRates, setMatRates] = useState(MATERIAL_RATES.map(r => ({ ...r, value: r.master })));
  const [procRates, setProcRates] = useState(PROCESS_RATES.map(r => ({ ...r, value: r.master })));
  const [toast, setToast] = useState('');

  const showToast = (m) => { setToast(m); setTimeout(() => setToast(''), 2500); };

  const updateMat = (i, val) => setMatRates(prev => prev.map((r, idx) => idx === i ? { ...r, value: val } : r));
  const resetMat = (i) => setMatRates(prev => prev.map((r, idx) => idx === i ? { ...r, value: r.master } : r));
  const updateProc = (i, val) => setProcRates(prev => prev.map((r, idx) => idx === i ? { ...r, value: val } : r));

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Master Configuration</span>
          <h1 style={{ marginTop: 4 }}>Master Configuration</h1>
          <p>Default rates resolve first — overridable at estimate level</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary" onClick={() => showToast('Master values saved successfully')}>
            <Save size={14} /> Save Changes
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
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Material</th>
                <th>Category</th>
                <th>Unit</th>
                <th style={{ textAlign: 'right' }}>Master Rate</th>
                <th style={{ textAlign: 'right', width: 160 }}>Current Value</th>
                <th style={{ textAlign: 'center' }}>Reset</th>
              </tr>
            </thead>
            <tbody>
              {matRates.map((r, i) => (
                <tr key={r.material}>
                  <td><strong style={{ fontSize: 13 }}>{r.material}</strong></td>
                  <td><span className="pill pill-orange" style={{ fontSize: 10 }}>{r.category}</span></td>
                  <td style={{ fontSize: 12, color: 'var(--muted)' }}>{r.unit}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {r.master}</td>
                  <td style={{ textAlign: 'right' }}>
                    <input
                      type="number"
                      value={r.value}
                      onChange={e => updateMat(i, Number(e.target.value))}
                      style={{
                        width: 90, height: 32, border: `1px solid ${r.value !== r.master ? 'var(--orange)' : 'var(--line)'}`,
                        borderRadius: 6, padding: '0 10px', fontSize: 13, fontFamily: 'Manrope',
                        fontWeight: 700, textAlign: 'right', outline: 'none',
                        background: r.value !== r.master ? 'var(--orange-light)' : 'var(--panel)',
                        color: r.value !== r.master ? 'var(--orange)' : 'var(--ink)',
                      }}
                    />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {r.value !== r.master && (
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => resetMat(i)} title="Reset to master">
                        <RotateCcw size={13} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'Process Rates' && (
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr>
                <th>Process</th>
                <th>Category</th>
                <th>Unit</th>
                <th style={{ textAlign: 'right' }}>Master Rate</th>
                <th style={{ textAlign: 'right', width: 160 }}>Current Value</th>
              </tr>
            </thead>
            <tbody>
              {procRates.map((r, i) => (
                <tr key={r.process}>
                  <td><strong style={{ fontSize: 12 }}>{r.process}</strong></td>
                  <td><span className="pill pill-blue" style={{ fontSize: 10 }}>{r.category}</span></td>
                  <td style={{ fontSize: 12, color: 'var(--muted)' }}>{r.unit}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Manrope', fontWeight: 600 }}>₹ {r.master}</td>
                  <td style={{ textAlign: 'right' }}>
                    <input
                      type="number"
                      value={r.value}
                      onChange={e => updateProc(i, Number(e.target.value))}
                      style={{
                        width: 100, height: 32, border: '1px solid var(--line)',
                        borderRadius: 6, padding: '0 10px', fontSize: 13,
                        fontFamily: 'Manrope', fontWeight: 600, textAlign: 'right', outline: 'none',
                      }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(activeTab === 'Punching' || activeTab === 'Make-ready Defaults') && (
        <div className="panel">
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--muted-2)' }}>
            <AlertCircle size={28} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
            <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--muted)', marginBottom: 6 }}>Not yet configured</div>
            <div style={{ fontSize: 12 }}>{activeTab} configuration will be available in a future update.</div>
          </div>
        </div>
      )}

      {toast && (
        <div className="toast">
          <Save size={14} style={{ color: '#72D38D' }} />
          {toast}
        </div>
      )}
    </div>
  );
}
