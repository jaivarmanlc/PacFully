import React, { useState } from 'react';
import { Plus, Search, Shield, Edit2, Trash2 } from 'lucide-react';

const USERS = [
  { id: 1, name: 'Jaya Varma', email: 'jaya@pacfully.in', role: 'Administrator', lastLogin: '25 Sep 2026', status: 'Active' },
  { id: 2, name: 'Arjun Kapoor', email: 'arjun@pacfully.in', role: 'Estimator', lastLogin: '24 Sep 2026', status: 'Active' },
  { id: 3, name: 'Priya Menon', email: 'priya@pacfully.in', role: 'Viewer', lastLogin: '22 Sep 2026', status: 'Active' },
  { id: 4, name: 'Rahul Sharma', email: 'rahul@pacfully.in', role: 'Estimator', lastLogin: '20 Sep 2026', status: 'Inactive' },
];

const ROLES = [
  { role: 'Administrator', desc: 'Full access — all modules, master config, users', color: '#FF5A3A' },
  { role: 'Estimator', desc: 'Create and manage estimates, quotations, proformas', color: '#3B82F6' },
  { role: 'Viewer', desc: 'Read-only access to estimates and reports', color: '#48BB78' },
];

export default function Users() {
  const [search, setSearch] = useState('');

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-header-left">
          <span className="eyebrow">Users & Roles</span>
          <h1 style={{ marginTop: 4 }}>Users & Roles</h1>
          <p>Manage user access and permissions</p>
        </div>
        <div className="page-header-right">
          <button className="btn btn-primary"><Plus size={15} /> Invite User</button>
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
          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted-2)' }}>{USERS.length} users</div>
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
            {USERS.map(u => (
              <tr key={u.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div className="avatar" style={{ width: 32, height: 32, fontSize: 11 }}>
                      {u.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{u.name}</div>
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
                <td style={{ fontSize: 12, color: 'var(--muted-2)' }}>{u.lastLogin}</td>
                <td>
                  <span className={`pill ${u.status === 'Active' ? 'pill-confirmed' : 'pill-draft'}`} style={{ fontSize: 11 }}>
                    {u.status}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                    <button className="btn btn-ghost btn-sm btn-icon"><Edit2 size={13} /></button>
                    <button className="btn btn-ghost btn-sm btn-icon"><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
