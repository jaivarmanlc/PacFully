import React, { useEffect, useState } from 'react';
import { AlertCircle, RotateCcw, Save } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { getFormulaConfig, saveFormulaConfig } from '../services/api.js';

export default function FormulaConfig() {
  const { user } = useAuth();
  const isLoggedIn = Boolean(user);
  const canEdit = user?.role === 'Administrator';
  const [formulaRows, setFormulaRows] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [formulaVersion, setFormulaVersion] = useState('');

  useEffect(() => {
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }
    let active = true;
    getFormulaConfig()
      .then(({ formulas, version }) => {
        if (!active) return;
        setFormulaVersion(version || '');
        const rows = Object.entries(formulas);
        setFormulaRows(rows);
        setDrafts(Object.fromEntries(rows.map(([key, definition]) => [key, definition.expression])));
      })
      .catch(requestError => {
        if (active) setError(requestError.message || 'Unable to load formulas');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [isLoggedIn]);

  const saveChanges = async () => {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await saveFormulaConfig(drafts);
      setFormulaVersion(saved.version || '');
      setFormulaRows(rows => rows.map(([key, definition]) => [key, { ...definition, expression: drafts[key] }]));
      setNotice('Formulas saved. New calculations will use these expressions.');
    } catch (saveError) {
      setError(saveError.message || 'Unable to save formulas');
    } finally {
      setSaving(false);
    }
  };

  const resetDrafts = () => {
    if (!formulaRows.length) return;
    setDrafts(Object.fromEntries(formulaRows.map(([key, definition]) => [key, definition.default_expression])));
    setNotice('Default formulas loaded. Save to apply them.');
    setError('');
  };

  if (!isLoggedIn) {
    return (
      <div className="page-content">
        <div className="warn-banner"><AlertCircle size={16} /> Sign in to manage project formulas.</div>
      </div>
    );
  }

  const groups = [...new Set(formulaRows.map(([, definition]) => definition.group))];

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Project Configuration</span>
          <h1 style={{ marginTop: 4 }}>Formula Configuration</h1>
          <p>Saved formulas are used by future module and estimate calculations{formulaVersion ? ` · Version ${formulaVersion}` : ''}</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-secondary" onClick={resetDrafts} disabled={loading || saving || formulaRows.length === 0 || !canEdit}>
            <RotateCcw size={14} /> Reset Defaults
          </button>
          <button className="btn btn-primary" onClick={saveChanges} disabled={loading || saving || formulaRows.length === 0 || !canEdit}>
            <Save size={14} /> {saving ? 'Saving...' : 'Save Formulas'}
          </button>
        </div>
      </div>

      {error && <div className="warn-banner" style={{ marginBottom: 16 }}><AlertCircle size={15} /> {error}</div>}
      {notice && <div className="info-banner" style={{ marginBottom: 16 }}>{notice}</div>}

      {loading ? <div className="panel">Loading formulas...</div> : formulaRows.length === 0 ? (
        <div className="panel" style={{ color: 'var(--muted)' }}>
          No formulas were loaded. Confirm your account is authenticated with the backend, then reload this page.
        </div>
      ) : (
        <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
          {groups.map(group => (
            <section key={group} style={{ padding: 20, borderBottom: '1px solid var(--line)' }}>
              <h2 style={{ marginBottom: 14 }}>{group}</h2>
              {formulaRows.filter(([, definition]) => definition.group === group).map(([key, definition]) => (
                <div key={key} className="form-grid-2" style={{ padding: '12px 0', borderTop: '1px solid var(--line-2)', alignItems: 'start' }}>
                  <div>
                    <label className="form-label">{definition.title}</label>
                    <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8 }}>{definition.description}</div>
                    <div style={{ color: 'var(--muted-2)', fontSize: 11, lineHeight: 1.7 }}>
                      {Object.entries(definition.variables).map(([name, description]) => (
                        <div key={name}><code>{name}</code>: {description}</div>
                      ))}
                    </div>
                  </div>
                  <textarea
                    className="form-input"
                    aria-label={`${group} ${definition.title} formula`}
                    value={drafts[key] ?? ''}
                    readOnly={!canEdit}
                    onChange={event => setDrafts(current => ({ ...current, [key]: event.target.value }))}
                    rows={3}
                    spellCheck={false}
                    style={{ height: 'auto', minHeight: 76, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                  />
                </div>
              ))}
            </section>
          ))}
          <div style={{ padding: 16, color: 'var(--muted)', fontSize: 12 }}>
            Formula expressions allow arithmetic, comparisons, conditional expressions, and the functions sum, min, max, abs, ceil, floor, and round. EB remains configuration-required; One Time Cost uses configured die rates and area-based formulas.
          </div>
        </div>
      )}
    </div>
  );
}