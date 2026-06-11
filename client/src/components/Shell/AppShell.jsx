import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  BarChart3,
  Cable,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  FileStack,
  Gauge,
  LayoutTemplate,
  Settings2,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { usePowerBi } from '../../context/PowerBiContext';

function ShellNavLink({ to, icon: Icon, children, collapsed }) {
  return (
    <NavLink
      to={to}
      title={collapsed ? children : undefined}
      className={({ isActive }) =>
        `shell-nav__link${isActive ? ' shell-nav__link--active' : ''}`
      }
      end={to === '/'}
    >
      <span className="shell-nav__icon">
        <Icon size={18} strokeWidth={2} />
      </span>
      <span className="shell-nav__label">{children}</span>
    </NavLink>
  );
}

export default function AppShell() {
  const { activeConnection, connections, notice, setNotice } = usePowerBi();
  const [collapsed, setCollapsed] = useState(false);
  const [banners, setBanners] = useState([]);

  const isConnected = activeConnection?.session?.is_authenticated;

  const dismissBanner = (id) => setBanners((prev) => prev.filter((b) => b.id !== id));

  // Expose a way for child pages to push banners via context — for now just show the global notice
  const globalNotice = notice;

  return (
    <div className="app-frame">
      {/* ── SIDEBAR ─────────────────────────────────────────── */}
      <aside className={`shell-sidebar${collapsed ? ' shell-sidebar--collapsed' : ''}`}>
        {/* Brand */}
        <div className="shell-brand">
          <div className="shell-brand__mark">B</div>
          <div className="shell-brand__text">
            <div className="shell-brand__title">BI-Foundry</div>
            <div className="shell-brand__subtitle">Power BI Studio</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="shell-nav" aria-label="Primary navigation">
          <span className="shell-nav__section-label">Main</span>
          <ShellNavLink to="/" icon={Gauge} collapsed={collapsed}>Dashboard</ShellNavLink>
          <ShellNavLink to="/connections" icon={Cable} collapsed={collapsed}>Connections</ShellNavLink>
          <ShellNavLink to="/projects" icon={BarChart3} collapsed={collapsed}>Projects</ShellNavLink>

          <span className="shell-nav__section-label" style={{ marginTop: 8 }}>Build</span>
          <ShellNavLink to="/create" icon={FileStack} collapsed={collapsed}>Create Report</ShellNavLink>
          <ShellNavLink to="/templates" icon={LayoutTemplate} collapsed={collapsed}>Templates</ShellNavLink>

          <span className="shell-nav__section-label" style={{ marginTop: 8 }}>System</span>
          <ShellNavLink to="/settings" icon={Settings2} collapsed={collapsed}>Settings</ShellNavLink>

          {/* Collapse toggle */}
          <div style={{ flex: 1 }} />
          <button
            className="shell-collapse-btn"
            onClick={() => setCollapsed((v) => !v)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            type="button"
          >
            <span className="shell-nav__icon">
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </span>
            <span className="shell-nav__label">Collapse</span>
          </button>
        </nav>

        {/* Active Connection mini-card */}
        <div className="shell-connection-card">
          <div className="shell-connection-card__header">
            <div
              className={`shell-connection-card__dot${isConnected ? ' shell-connection-card__dot--connected' : ''}`}
            />
            <div className="shell-connection-card__name">
              {activeConnection?.label || 'No connection'}
            </div>
            {isConnected ? (
              <Wifi size={12} style={{ color: '#10b981', marginLeft: 'auto', flexShrink: 0 }} />
            ) : (
              <WifiOff size={12} style={{ color: '#6b7280', marginLeft: 'auto', flexShrink: 0 }} />
            )}
          </div>
          <div className="shell-connection-card__meta">
            {isConnected
              ? activeConnection?.session?.user_email || 'Authenticated'
              : activeConnection
                ? `${connections.length} profile${connections.length !== 1 ? 's' : ''} saved`
                : 'Connect a profile to begin'}
          </div>
        </div>
      </aside>

      {/* ── MAIN ────────────────────────────────────────────── */}
      <div className="shell-main">
        {/* Global notice banner */}
        {globalNotice && (
          <div style={{ padding: '12px 28px 0' }}>
            <div className="status-banner status-banner--success">
              <span><CircleCheck size={15} style={{ display: 'inline', marginRight: 6 }} />{globalNotice}</span>
              <button className="status-banner__close" onClick={() => setNotice?.('')} type="button">
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Per-page banners */}
        {banners.length > 0 && (
          <div className="banner-area" style={{ paddingTop: 12 }}>
            {banners.map((b) => (
              <div key={b.id} className={`status-banner status-banner--${b.type}`}>
                <span>{b.message}</span>
                <button className="status-banner__close" onClick={() => dismissBanner(b.id)} type="button">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        <Outlet />
      </div>
    </div>
  );
}
