import React, { useState } from 'react';
import { Save, Building2, Receipt, Globe, Bell, Shield, Database } from 'lucide-react';

const TABS = ['Company Profile', 'Tax & GST', 'Document Numbering', 'Notifications', 'Security', 'Data'];

export default function Settings() {
  const [activeTab, setActiveTab] = useState('Company Profile');
  const [toast, setToast] = useState('');

  const showToast = () => { setToast('Settings saved'); setTimeout(() => setToast(''), 2500); };

  const tabIcons = {
    'Company Profile': Building2, 'Tax & GST': Receipt,
    'Document Numbering': Globe, 'Notifications': Bell,
    'Security': Shield, 'Data': Database,
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Settings</span>
          <h1 style={{ marginTop: 4 }}>Settings</h1>
          <p>Configure company profile, tax, and system preferences</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary" onClick={showToast}>
            <Save size={14} /> Save Changes
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20 }}>
        {/* Sidebar nav */}
        <div className="panel" style={{ height: 'fit-content', padding: 8 }}>
          {TABS.map(t => {
            const Icon = tabIcons[t];
            return (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`nav-item ${activeTab === t ? 'active' : ''}`}
                style={{ width: '100%', marginBottom: 2 }}
              >
                <Icon size={15} className="nav-icon" />
                <span style={{ fontSize: 13 }}>{t}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div>
          {activeTab === 'Company Profile' && (
            <div className="panel">
              <h3 style={{ marginBottom: 20 }}>Company Profile</h3>
              <div className="form-grid-2" style={{ gap: 16, marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Company Name</label>
                  <input className="form-input" defaultValue="Pacfully Packaging Pvt Ltd" />
                </div>
                <div className="form-group">
                  <label className="form-label">GST Number</label>
                  <input className="form-input" defaultValue="33AABCP1234F1Z5" />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input className="form-input" type="email" defaultValue="accounts@pacfully.in" />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input className="form-input" defaultValue="+91 44 1234 5678" />
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Address</label>
                <textarea
                  className="form-input"
                  style={{ height: 80, paddingTop: 8, resize: 'vertical' }}
                  defaultValue="120 Business Park, Chennai – 600001, Tamil Nadu, India"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Bank Details (for Proforma)</label>
                <textarea
                  className="form-input"
                  style={{ height: 80, paddingTop: 8, resize: 'vertical' }}
                  defaultValue="Bank: HDFC Bank | A/C: 50100123456789 | IFSC: HDFC0001234 | Branch: Chennai Main"
                />
              </div>
            </div>
          )}

          {activeTab === 'Tax & GST' && (
            <div className="panel">
              <h3 style={{ marginBottom: 20 }}>Tax & GST Configuration</h3>
              <div className="form-grid-2" style={{ gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Default GST Rate (%)</label>
                  <input className="form-input" type="number" defaultValue="18" />
                </div>
                <div className="form-group">
                  <label className="form-label">HSN Code</label>
                  <input className="form-input" defaultValue="4819" />
                </div>
                <div className="form-group">
                  <label className="form-label">Tax Regime</label>
                  <select className="form-select">
                    <option>GST (India)</option>
                    <option>VAT</option>
                    <option>No Tax</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'Document Numbering' && (
            <div className="panel">
              <h3 style={{ marginBottom: 20 }}>Document Numbering</h3>
              <div className="form-grid-2" style={{ gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Estimate Prefix</label>
                  <input className="form-input" defaultValue="EST-" />
                </div>
                <div className="form-group">
                  <label className="form-label">Quotation Prefix</label>
                  <input className="form-input" defaultValue="QUO-" />
                </div>
                <div className="form-group">
                  <label className="form-label">Proforma Prefix</label>
                  <input className="form-input" defaultValue="PI-" />
                </div>
                <div className="form-group">
                  <label className="form-label">Next Estimate Number</label>
                  <input className="form-input" type="number" defaultValue="125" />
                </div>
              </div>
            </div>
          )}

          {['Notifications', 'Security', 'Data'].includes(activeTab) && (
            <div className="panel">
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--muted-2)' }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 6 }}>Not yet configured</div>
                <div style={{ fontSize: 12 }}>{activeTab} settings will be available in a future update.</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {toast && (
        <div className="toast">
          <Save size={14} style={{ color: '#72D38D' }} />
          {toast}
        </div>
      )}
    </div>
  );
}
