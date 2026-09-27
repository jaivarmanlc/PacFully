import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ChevronDown, Cpu, BarChart3, FileText, Package, CheckCircle2, Star } from 'lucide-react';
import BrandLogo from '../components/BrandLogo.jsx';

function PacfullyNavLogo() {
  return <BrandLogo width={150} />;
}

const FEATURES = [
  {
    num: '01',
    icon: Cpu,
    title: 'AI Layout Analysis',
    desc: 'Extract dimensions, materials and processes automatically.',
  },
  {
    num: '02',
    icon: BarChart3,
    title: 'Cost Intelligence',
    desc: 'Transparent, module-wise manufacturing cost calculation.',
  },
  {
    num: '03',
    icon: FileText,
    title: 'Smart Quotation',
    desc: 'Convert estimates into professional quotes and proforma instantly.',
  },
];

const STATS = [
  { value: '124+', label: 'Estimates Generated' },
  { value: '₹ 28L+', label: 'Quoted Value' },
  { value: '18.42', label: 'Avg. Cost / Box' },
  { value: '68%', label: 'Conversion Rate' },
];

export default function Home() {
  const navigate = useNavigate();
  const navItems = [
    { label: 'Industry Products', href: 'https://pacfully.com/industries', hasDropdown: true },
    { label: 'Infrastructure', href: 'https://pacfully.com/plant-capacity', hasDropdown: true },
    { label: 'Blog', href: 'https://pacfully.com/blog', hasDropdown: false },
    { label: 'Contact', href: 'https://pacfully.com/contact', hasDropdown: false },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#FFFFFF', fontFamily: 'Inter, sans-serif' }}>
      {/* ── Nav ─────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(8px)',
        borderBottom: '1px solid #F0F2F5',
        display: 'flex', alignItems: 'center',
        padding: '0 48px', height: 64,
        gap: 40,
      }}>
        <PacfullyNavLogo />
        <div style={{ display: 'flex', gap: 32, flex: 1 }}>
          {navItems.map(item => (
            <a
              key={item.label}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              style={{
                background: 'none', border: 'none',
                fontSize: 13, color: '#555', cursor: 'pointer', fontWeight: 500,
                display: 'flex', alignItems: 'center', gap: 4,
                textDecoration: 'none',
              }}
            >
              {item.label}
              {item.hasDropdown ? <ChevronDown size={13} /> : null}
            </a>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={() => navigate('/login')}
            style={{
              background: 'none', border: '1px solid #E5E9EE',
              padding: '8px 18px', borderRadius: 7,
              fontSize: 13, fontWeight: 600, cursor: 'pointer', color: '#333',
            }}
          >Sign In</button>
          <button
            onClick={() => navigate('/login')}
            style={{
              background: '#FF5A3A', color: '#fff',
              border: 'none', padding: '8px 18px',
              borderRadius: 7, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', boxShadow: '0 4px 14px rgba(255,90,58,0.3)',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            Get Started <ArrowRight size={14} />
          </button>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────── */}
      <section style={{
        background: 'linear-gradient(135deg, #FFF9F7 0%, #FFFFFF 60%, #FFF1ED 100%)',
        padding: '80px 48px 60px',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 60,
        alignItems: 'center',
        minHeight: '88vh',
        maxWidth: 1300,
        margin: '0 auto',
      }}>
        {/* Left */}
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            background: '#FFF1ED', border: '1px solid #FFD9D0',
            borderRadius: 99, padding: '4px 14px',
            fontSize: 11, fontWeight: 700, color: '#FF5A3A',
            letterSpacing: '0.08em', textTransform: 'uppercase',
            marginBottom: 22,
          }}>
            ✦ Premium Packaging & Cost Intelligence
          </div>

          <h1 style={{
            fontFamily: 'Manrope', fontSize: 56, fontWeight: 800,
            lineHeight: 1.1, letterSpacing: '-1.5px',
            margin: '0 0 22px', color: '#1A1D23',
          }}>
            Packaging that{' '}
            <span style={{ color: '#FF5A3A' }}>elevates</span>{' '}
            your<br />brand.
          </h1>

          <p style={{ fontSize: 16, color: '#6B7280', lineHeight: 1.7, marginBottom: 36, maxWidth: 480 }}>
            From packaging layout to accurate costing.<br />
            <strong style={{ color: '#434950' }}>Engineer. Calculate. Quote with precision.</strong>
          </p>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button
              onClick={() => navigate('/login')}
              style={{
                background: '#FF5A3A', color: '#fff',
                border: 'none', padding: '14px 28px',
                borderRadius: 9, fontSize: 14, fontWeight: 700,
                cursor: 'pointer', boxShadow: '0 6px 20px rgba(255,90,58,0.35)',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              Get Started <ArrowRight size={16} />
            </button>
            <button style={{
              background: 'transparent', color: '#434950',
              border: '1.5px solid #E5E9EE', padding: '14px 28px',
              borderRadius: 9, fontSize: 14, fontWeight: 600,
              cursor: 'pointer',
            }}>
              Explore Products
            </button>
          </div>

          {/* Stats row */}
          <div style={{ display: 'flex', gap: 32, marginTop: 48, paddingTop: 32, borderTop: '1px solid #F0F2F5' }}>
            {STATS.map(s => (
              <div key={s.label}>
                <div style={{ fontFamily: 'Manrope', fontSize: 22, fontWeight: 800, color: '#1A1D23' }}>{s.value}</div>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 3 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right - Box visual */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
          {/* Background circle */}
          <div style={{
            width: 420, height: 420, borderRadius: '50%',
            background: 'radial-gradient(circle, #FFF1ED 0%, #FFF8F6 60%, transparent 100%)',
            position: 'absolute',
          }} />
          {/* Stacked box illustration */}
          <div style={{ position: 'relative', zIndex: 1 }}>
            {/* Main box */}
            <div style={{
              width: 240, height: 200,
              background: 'linear-gradient(135deg, #FF7A5C, #FF5A3A)',
              borderRadius: 18,
              boxShadow: '0 24px 64px rgba(255,90,58,0.35)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              position: 'relative',
              overflow: 'hidden',
            }}>
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 60%)' }} />
              <Package size={64} color="rgba(255,255,255,0.9)" />
              <BrandLogo width={108} style={{ position: 'absolute', bottom: 16, left: 16, background: '#fff', padding: 3, borderRadius: 2 }} />
            </div>

            {/* Small box behind */}
            <div style={{
              width: 140, height: 120,
              background: 'linear-gradient(135deg, #FFB09C, #FF7A5C)',
              borderRadius: 12,
              position: 'absolute', top: -30, right: -50,
              boxShadow: '0 12px 32px rgba(255,90,58,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Package size={36} color="rgba(255,255,255,0.8)" />
            </div>

            {/* Tag on main box */}
            <div style={{
              position: 'absolute', bottom: -20, right: -20,
              background: '#fff', borderRadius: 10, padding: '10px 14px',
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              fontSize: 11, fontWeight: 600, color: '#1A1D23',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <CheckCircle2 size={14} color="#3D9D62" />
              Cost Calculated
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────────── */}
      <section style={{
        background: '#F7F8FA',
        padding: '60px 48px',
        borderTop: '1px solid #F0F2F5',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 44 }}>
            <span style={{
              fontSize: 11, fontWeight: 700, letterSpacing: '0.1em',
              textTransform: 'uppercase', color: '#FF5A3A',
            }}>Why Pacfully</span>
            <h2 style={{ fontFamily: 'Manrope', fontSize: 36, fontWeight: 800, margin: '10px 0 12px', color: '#1A1D23' }}>
              Built for packaging professionals
            </h2>
            <p style={{ fontSize: 15, color: '#6B7280', maxWidth: 500, margin: '0 auto' }}>
              Every costing module is deterministic, traceable and reproducible — no black boxes.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            {FEATURES.map(({ num, icon: Icon, title, desc }) => (
              <div key={num} style={{
                background: '#fff',
                border: '1px solid #E5E9EE',
                borderRadius: 14,
                padding: '28px 24px',
                transition: 'transform 0.2s, box-shadow 0.2s',
              }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 11,
                  background: '#FFF1ED',
                  display: 'grid', placeItems: 'center',
                  marginBottom: 18, color: '#FF5A3A',
                }}>
                  <Icon size={22} />
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#FF5A3A', marginBottom: 6 }}>{num}</div>
                <h3 style={{ fontFamily: 'Manrope', fontSize: 17, fontWeight: 700, margin: '0 0 8px', color: '#1A1D23' }}>{title}</h3>
                <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.6, margin: 0 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────── */}
      <section style={{
        background: 'linear-gradient(135deg, #FF5A3A, #FF7A5C)',
        padding: '60px 48px',
        textAlign: 'center',
      }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <h2 style={{ fontFamily: 'Manrope', fontSize: 36, fontWeight: 800, color: '#fff', margin: '0 0 14px' }}>
            Smart Packaging.<br />Smarter Business.
          </h2>
          <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.85)', marginBottom: 32 }}>
            Start your first cost estimate in minutes. No setup required.
          </p>
          <button
            onClick={() => navigate('/login')}
            style={{
              background: '#fff', color: '#FF5A3A',
              border: 'none', padding: '14px 32px',
              borderRadius: 9, fontSize: 14, fontWeight: 700,
              cursor: 'pointer', boxShadow: '0 6px 20px rgba(0,0,0,0.15)',
              display: 'inline-flex', alignItems: 'center', gap: 8,
            }}
          >
            Get Started Free <ArrowRight size={16} />
          </button>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer style={{
        background: '#1A1D23', padding: '32px 48px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <BrandLogo width={142} style={{ background: '#fff', padding: 4, borderRadius: 2 }} />
        </div>
        <div style={{ fontSize: 12, color: '#6B7280' }}>© 2026 Pacfully. All rights reserved.</div>
        <div style={{ display: 'flex', gap: 20 }}>
          {['Privacy', 'Terms', 'Support'].map(l => (
            <span key={l} style={{ fontSize: 12, color: '#9CA3AF', cursor: 'pointer' }}>{l}</span>
          ))}
        </div>
      </footer>
    </div>
  );
}
