import React, { useEffect, useState } from 'react';
import { AlertCircle, Save, Building2, Receipt, Globe, Bell, Shield, Database } from 'lucide-react';
import { getSystemSettings, saveSystemSettings } from '../services/api.js';

const TABS = ['Company Profile', 'Tax & GST', 'Document Numbering', 'Notifications', 'Security', 'Data'];
const DEFAULT_SETTINGS = {
  company_name: 'Pacfully Packaging Pvt Ltd',
  gst_number: '33AABCP1234F1Z5',
  email: 'accounts@pacfully.in',
  phone: '+91 44 1234 5678',
  address: '120 Business Park, Chennai - 600001, Tamil Nadu, India',
  bank_details: 'Bank: HDFC Bank | A/C: 50100123456789 | IFSC: HDFC0001234 | Branch: Chennai Main',
  gst_rate: 18,
  hsn_code: '4819',
  tax_regime: 'GST (India)',
  estimate_prefix: 'EST-',
  quotation_prefix: 'QUO-',
  proforma_prefix: 'PI-',
  next_estimate_number: 125,
};

export default function Settings() {
  const [activeTab, setActiveTab] = useState('Company Profile');
  const [toast, setToast] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);

  useEffect(() => {
    getSystemSettings()
      .then(({ settings: savedSettings }) => setSettings({ ...DEFAULT_SETTINGS, ...savedSettings }))
      .catch(err => setError(err.message || 'Unable to load settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleChange = event => {
    const { name, value, type } = event.target;
    setSettings(current => ({ ...current, [name]: type === 'number' ? Number(value) : value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const response = await saveSystemSettings(settings);
      setSettings({ ...DEFAULT_SETTINGS, ...response.settings });
      setToast('Settings saved');
      setTimeout(() => setToast(''), 2500);
    } catch (err) {
      setError(err.message || 'Unable to save settings');
    } finally {
      setSaving(false);
    }
  };

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
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || loading}>
            <Save size={14} /> {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>

      {error && <div className="warn-banner" role="alert" style={{ marginBottom: 16 }}><AlertCircle size={15} />{error}</div>}
      {loading && <div role="status" style={{ marginBottom: 12, color: 'var(--muted-2)', fontSize: 12 }}>Loading settings…</div>}

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
                  <input className="form-input" name="company_name" value={settings.company_name} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">GST Number</label>
                  <input className="form-input" name="gst_number" value={settings.gst_number} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input className="form-input" type="email" name="email" value={settings.email} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input className="form-input" name="phone" value={settings.phone} onChange={handleChange} />
                </div>
              </div>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Address</label>
                <textarea
                  className="form-input"
                  name="address"
                  style={{ height: 80, paddingTop: 8, resize: 'vertical' }}
                  value={settings.address}
                  onChange={handleChange}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Bank Details (for Proforma)</label>
                <textarea
                  className="form-input"
                  name="bank_details"
                  style={{ height: 80, paddingTop: 8, resize: 'vertical' }}
                  value={settings.bank_details}
                  onChange={handleChange}
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
                  <input className="form-input" type="number" min="0" max="100" name="gst_rate" value={settings.gst_rate} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">HSN Code</label>
                  <input className="form-input" name="hsn_code" value={settings.hsn_code} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Tax Regime</label>
                  <select className="form-select" name="tax_regime" value={settings.tax_regime} onChange={handleChange}>
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
                  <input className="form-input" name="estimate_prefix" value={settings.estimate_prefix} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Quotation Prefix</label>
                  <input className="form-input" name="quotation_prefix" value={settings.quotation_prefix} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Proforma Prefix</label>
                  <input className="form-input" name="proforma_prefix" value={settings.proforma_prefix} onChange={handleChange} />
                </div>
                <div className="form-group">
                  <label className="form-label">Next Estimate Number</label>
                  <input className="form-input" type="number" min="1" name="next_estimate_number" value={settings.next_estimate_number} onChange={handleChange} />
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
