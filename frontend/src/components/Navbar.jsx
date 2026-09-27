import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Search, Bell, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext.jsx';

const ROUTE_LABELS = {
  '/dashboard':    ['Dashboard', 'Cost Intelligence'],
  '/estimator':    ['Cost Estimator', 'New Estimate'],
  '/estimates':    ['Estimates'],
  '/customers':    ['Customers'],
  '/reports':      ['Reports & Analytics'],
  '/master-config':['Master Configuration'],
  '/quotations':   ['Quotations'],
  '/proforma':     ['Proforma'],
  '/settings':     ['Settings'],
  '/users':        ['Users & Roles'],
  '/audit-log':    ['Audit Log'],
};

function getBreadcrumb(pathname) {
  for (const [route, crumbs] of Object.entries(ROUTE_LABELS)) {
    if (pathname.startsWith(route)) return crumbs;
  }
  return ['Pacfully'];
}

export default function Navbar() {
  const location            = useLocation();
  const navigate            = useNavigate();
  const { user, initials, logout } = useAuth();
  const crumbs              = getBreadcrumb(location.pathname);
  const [search, setSearch] = useState('');
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const handleSearch = (event) => {
    event.preventDefault();
    const query = search.trim().toLowerCase();
    if (!query) return;
    const destination = query.includes('customer') || query.includes('client')
      ? '/customers'
      : query.includes('quotation') || query.includes('quote')
        ? '/quotations'
        : query.includes('report')
          ? '/reports'
          : '/estimates';
    navigate(destination);
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="topbar">
      {/* Breadcrumb */}
      <div className="topbar-breadcrumb">
        <span>Cost Intelligence</span>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            <span>/</span>
            <strong>{c}</strong>
          </React.Fragment>
        ))}
      </div>

      {/* Search */}
      <form className="topbar-search" onSubmit={handleSearch} role="search">
        <Search size={14} className="topbar-search-icon" />
        <input
          placeholder="Search estimates, customers, materials..."
          value={search}
          onChange={event => setSearch(event.target.value)}
          aria-label="Search estimates, customers, and materials"
        />
      </form>

      {/* Right actions */}
      <div className="topbar-actions">
        <div style={{ position: 'relative' }}>
          <button
            className="topbar-icon-btn"
            type="button"
            aria-label="Notifications"
            aria-expanded={notificationsOpen}
            onClick={() => { setNotificationsOpen(value => !value); setProfileOpen(false); }}
          >
          <Bell size={16} />
          <span className="topbar-badge" />
          </button>
          {notificationsOpen && (
            <div style={{
              position: 'absolute', right: 0, top: 'calc(100% + 10px)', zIndex: 110,
              width: 280, padding: 14, background: '#fff', border: '1px solid var(--line)',
              borderRadius: 10, boxShadow: 'var(--shadow-lg)',
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Notifications</div>
              <div style={{ padding: '10px 0', borderTop: '1px solid var(--line-2)', fontSize: 12, color: 'var(--muted)' }}>
                Your workspace is up to date.
              </div>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('/audit-log')}>
                View audit log
              </button>
            </div>
          )}
        </div>

        {/* Profile chip — shows the REAL logged-in user */}
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="topbar-profile"
            aria-label="Open account menu"
            aria-expanded={profileOpen}
            onClick={() => { setProfileOpen(value => !value); setNotificationsOpen(false); }}
          >
          <div className="avatar sm" style={{ background: 'var(--orange-light)', color: 'var(--orange)' }}>
            {initials}
          </div>
          <div className="topbar-profile-info">
            {user?.full_name ?? 'Guest'}
            <span>{user?.role ?? ''}</span>
          </div>
          <ChevronDown size={13} style={{ color: 'var(--muted-2)' }} />
          </button>
          {profileOpen && (
            <div style={{
              position: 'absolute', right: 0, top: 'calc(100% + 10px)', zIndex: 110,
              width: 190, padding: 8, background: '#fff', border: '1px solid var(--line)',
              borderRadius: 10, boxShadow: 'var(--shadow-lg)',
            }}>
              <div style={{ padding: '8px 10px 10px', borderBottom: '1px solid var(--line-2)', marginBottom: 5 }}>
                <div style={{ fontSize: 12, fontWeight: 700 }}>{user?.full_name ?? 'Guest'}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{user?.email ?? ''}</div>
              </div>
              <button type="button" className="nav-item" onClick={() => navigate('/settings')}>Account settings</button>
              <button type="button" className="nav-item" onClick={handleLogout}>Sign out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
