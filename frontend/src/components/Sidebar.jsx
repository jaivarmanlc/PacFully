import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Calculator, ClipboardList, Users, BarChart3,
  Settings2, FileText, Receipt, HelpCircle,
  Shield, BookOpen, Sigma, LogOut,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import BrandLogo from './BrandLogo.jsx';

const NAV_MAIN = [
  { label: 'Dashboard',           icon: LayoutDashboard, to: '/dashboard'    },
  { label: 'Cost Estimator',      icon: Calculator,      to: '/estimator/new' },
  { label: 'Estimates',           icon: ClipboardList,   to: '/estimates'    },
  { label: 'Customers',           icon: Users,           to: '/customers'    },
  { label: 'Reports',             icon: BarChart3,       to: '/reports'      },
  { label: 'Master Configuration',icon: Settings2,       to: '/master-config'},
  { label: 'Formulas',            icon: Sigma,           to: '/formulas'     },
  { label: 'Quotations',          icon: FileText,        to: '/quotations'   },
  { label: 'Proforma',            icon: Receipt,         to: '/proforma'     },
];

const NAV_ADMIN = [
  { label: 'Settings',    icon: Settings2, to: '/settings'  },
  { label: 'Users & Roles', icon: Shield,  to: '/users'     },
  { label: 'Audit Log',   icon: BookOpen,  to: '/audit-log' },
];

export default function Sidebar({ open = false, onClose }) {
  const location                   = useLocation();
  const navigate                   = useNavigate();
  const { user, initials, logout, publicAccess } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const isActive = (to) => {
    if (to === '/estimator/new') return location.pathname.startsWith('/estimator');
    return location.pathname.startsWith(to);
  };

  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <BrandLogo width={142} />
      </div>

      {/* Workspace badge */}
      <div style={{ margin: '0 10px 8px' }}>
        <div className="sidebar-workspace">
          <div>
            <span className="sidebar-workspace-label">Workspace</span>
            <span className="sidebar-workspace-name">Cost Intelligence</span>
          </div>
        </div>
      </div>

      {/* Main nav */}
      <nav className="sidebar-nav">
        {NAV_MAIN.map(({ label, icon: Icon, to }) => (
          <NavLink
            key={to}
            to={to}
            className={() => `nav-item ${isActive(to) ? 'active' : ''}`}
            onClick={onClose}
          >
            <Icon size={16} className="nav-icon" />
            <span>{label}</span>
          </NavLink>
        ))}

        {!publicAccess && <>
          <span className="sidebar-section-label" style={{ marginTop: 8 }}>Administration</span>
          {NAV_ADMIN.map(({ label, icon: Icon, to }) => (
            <NavLink
              key={to}
              to={to}
              className={() => `nav-item ${isActive(to) ? 'active' : ''}`}
              onClick={onClose}
            >
              <Icon size={16} className="nav-icon" />
              <span>{label}</span>
            </NavLink>
          ))}
        </>}
      </nav>

      {/* Bottom: user chip + logout */}
      <div className="sidebar-bottom">
        <button
          className="nav-item"
          style={{ width: '100%' }}
          onClick={() => window.open('https://pacfully.com/', '_blank', 'noopener,noreferrer')}
          title="Open Pacfully website"
        >
          <HelpCircle size={16} className="nav-icon" />
          <span>Help Centre</span>
        </button>

        {/* Logged-in user — reads from AuthContext */}
        <div style={{
          borderTop: '1px solid var(--line-2)',
          marginTop: 4, padding: '12px 10px 0',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 9,
            padding: '8px 10px', borderRadius: 8,
            background: 'var(--line-2)',
          }}>
            {/* Avatar with initials */}
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--orange-light)', color: 'var(--orange)',
              display: 'grid', placeItems: 'center',
              fontFamily: 'Manrope', fontSize: 11, fontWeight: 800,
              flexShrink: 0,
            }}>
              {initials}
            </div>

            {/* Name + role */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 12, fontWeight: 700, color: 'var(--ink-2)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {user?.full_name ?? 'Guest'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted-2)' }}>
                {user?.role ?? ''}
              </div>
            </div>

            {/* Logout button */}
            {!publicAccess && <button
              onClick={handleLogout}
              title="Sign out"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--muted-2)', padding: 4, borderRadius: 5,
                display: 'grid', placeItems: 'center',
                transition: 'color 0.15s, background 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#E53E3E'; e.currentTarget.style.background = '#FFF5F5'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--muted-2)'; e.currentTarget.style.background = 'none'; }}
            >
              <LogOut size={15} />
            </button>}
          </div>
        </div>
      </div>
    </aside>
  );
}
