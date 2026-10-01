import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Edit2, Plus, Search, Shield, Trash2, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';
import { createUser, deleteUser, listUsers, updateUserRole } from '../services/api.js';

const ROLES = [
  { role: 'Administrator', desc: 'Full access — all modules, master config, users', color: '#FF5A3A' },
  { role: 'Estimator', desc: 'Create and manage estimates, quotations, proformas', color: '#3B82F6' },
  { role: 'Viewer', desc: 'Read-only access to estimates and reports', color: '#48BB78' },
];

export default function Users() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalUser, setModalUser] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setUsers(await listUsers());
    } catch (err) {
      setError(err.message || 'Unable to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleSave = async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSaving(true);
    setError('');
    try {
      if (modalUser) {
        await updateUserRole(modalUser.id, data.get('role'));
        setToast('User role updated');
      } else {
        await createUser({
          full_name: data.get('full_name').trim(),
          email: data.get('email').trim(),
          password: data.get('password'),
          role: data.get('role'),
        });
        setToast('User created');
      }
      setModalUser(null);
      await loadUsers();
      setTimeout(() => setToast(''), 2500);
    } catch (err) {
      setError(err.message || 'Unable to save user');
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (target) => {
    if (!window.confirm(`Deactivate ${target.full_name}? They will no longer be able to sign in.`)) return;
    setError('');
    try {
      await deleteUser(target.id);
      setToast('User deactivated');
      await loadUsers();
      setTimeout(() => setToast(''), 2500);
    } catch (err) {
      setError(err.message || 'Unable to deactivate user');
    }
  };

  const filteredUsers = users.filter(item =>
    `${item.full_name} ${item.email} ${item.role}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Users & Roles</span>
          <h1 style={{ marginTop: 4 }}>Users & Roles</h1>
          <p>Manage user access and permissions</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary" type="button" onClick={() => { setError(''); setModalUser(false); }}>
            <Plus size={15} /> Invite User
          </button>
        </div>
      </div>

      {/* Role cards */}
      <div className="grid-3" style={{ marginBottom: 20 }}>
        {ROLES.map(r => (
          <div key={r.role} className="panel">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: r.color }} />
              <strong style={{ fontSize: 14 }}>{r.role}</strong>
            </div>
            <p style={{ fontSize: 12, color: 'var(--muted)', margin: 0 }}>{r.desc}</p>
          </div>
        ))}
      </div>

      {/* Users table */}
      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, maxWidth: 280 }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-3)' }} />
            <input className="form-input" style={{ paddingLeft: 32, height: 36, fontSize: 12 }} placeholder="Search users..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>{users.length} users</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Last Login</th>
              <th>Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(u => (
              <tr key={u.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="avatar" style={{ width: 32, height: 32, fontSize: 11 }}>
                      {u.full_name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{u.full_name}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted-2)' }}>{u.email}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Shield size={12} style={{ color: u.role === 'Administrator' ? '#FF5A3A' : u.role === 'Estimator' ? '#3B82F6' : '#48BB78' }} />
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{u.role}</span>
                  </div>
                </td>
                <td style={{ fontSize: 12, color: 'var(--muted-2)' }}>{u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}</td>
                <td>
                  <span className={`pill ${u.is_active ? 'pill-confirmed' : 'pill-draft'}`} style={{ fontSize: 11 }}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                    <button className="btn btn-ghost btn-sm btn-icon" title="Change role" aria-label={`Change role for ${u.full_name}`}
                      disabled={!u.is_active || u.id === currentUser?.id}
                      onClick={() => { setError(''); setModalUser(u); }}><Edit2 size={13} /></button>
                    <button className="btn btn-ghost btn-sm btn-icon" title="Deactivate user" aria-label={`Deactivate ${u.full_name}`}
                      disabled={!u.is_active || u.id === currentUser?.id}
                      onClick={() => handleDeactivate(u)}><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && <div role="status" style={{ marginTop: 8, color: 'var(--muted-2)', fontSize: 12 }}>Loading users…</div>}
      {error && <div className="warn-banner" role="alert" style={{ marginTop: 12 }}><AlertCircle size={15} />{error}</div>}

      {modalUser !== null && (
        <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !saving) setModalUser(null); }}>
          <form className="modal" role="dialog" aria-modal="true" aria-label={modalUser ? 'Edit user role' : 'Invite user'}
            onSubmit={handleSave} style={{ width: 460 }}>
            <div className="modal-header">
              <div><span className="eyebrow">Users & Roles</span><h2>{modalUser ? 'Change user role' : 'Invite user'}</h2></div>
              <button className="modal-close" type="button" aria-label="Close" disabled={saving} onClick={() => setModalUser(null)}><X size={16} /></button>
            </div>
            {!modalUser && <>
              <label className="form-group"><span className="form-label">Full name</span><input className="form-input" name="full_name" autoComplete="name" required /></label>
              <label className="form-group"><span className="form-label">Email</span><input className="form-input" name="email" type="email" autoComplete="email" required /></label>
              <label className="form-group"><span className="form-label">Temporary password</span><input className="form-input" name="password" type="password" minLength={12} maxLength={72} autoComplete="new-password" required /><span className="form-label">At least 12 characters</span></label>
            </>}
            <label className="form-group"><span className="form-label">Role</span>
              <select className="form-select" name="role" defaultValue={modalUser?.role || 'Estimator'}>
                {ROLES.map(option => <option key={option.role} value={option.role}>{option.role}</option>)}
              </select>
            </label>
            {error && <div role="alert" style={{ color: '#C53030', fontSize: 12, marginTop: 10 }}>{error}</div>}
            <div className="modal-footer">
              <button className="btn btn-secondary" type="button" disabled={saving} onClick={() => setModalUser(null)}>Cancel</button>
              <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : modalUser ? 'Save role' : 'Create user'}</button>
            </div>
          </form>
        </div>
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
