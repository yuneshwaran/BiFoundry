import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { CheckCircle2, Gauge, Settings2, Workflow, Cable } from 'lucide-react';
import { usePowerBi } from '../../context/PowerBiContext';

function activeConnectionStatus(connection) {
  if (connection?.session?.is_authenticated) {
    return connection.session.user_email || connection.session.user_name || 'Authenticated';
  }
  return 'Connect a Power BI profile to begin.';
}

function ShellNavLink({ to, icon: Icon, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `shell-nav__link${isActive ? ' shell-nav__link--active' : ''}`}
      end={to === '/'}
    >
      <Icon size={16} />
      <span>{children}</span>
    </NavLink>
  );
}

export default function AppShell() {
  const location = useLocation();
  const {
    activeConnection,
    activeConnectionId,
    connections,
    notice,
    selectConnection,
    selectConnectionPending,
  } = usePowerBi();

  const currentPathLabel = location.pathname.startsWith('/projects/')
    ? 'Project editor'
    : location.pathname.startsWith('/projects')
      ? 'Projects'
      : location.pathname.startsWith('/connections')
        ? 'Power BI Connections'
        : location.pathname.startsWith('/settings')
          ? 'Settings'
          : 'Home';

  return (
    <div className="app-frame">
      <aside className="shell-sidebar">
        <div className="shell-brand">
          <div className="shell-brand__mark">B</div>
          <div>
            <div className="shell-brand__title">BIFoundry</div>
            <div className="shell-brand__subtitle">Power BI workspace shell</div>
          </div>
        </div>

        <nav className="shell-nav" aria-label="Primary">
          <ShellNavLink to="/" icon={Gauge}>Home</ShellNavLink>
          <ShellNavLink to="/projects" icon={Workflow}>Projects</ShellNavLink>
          <ShellNavLink to="/connections" icon={Cable}>Power BI Connections</ShellNavLink>
          <ShellNavLink to="/settings" icon={Settings2}>Settings</ShellNavLink>
        </nav>

        <section className="shell-panel">
          <div className="section-title">Active profile</div>
          <div className="shell-status">
            <div className="shell-status__title">{activeConnection?.label || 'No connection selected'}</div>
            <div className="shell-status__meta">
              {activeConnectionStatus(activeConnection)}
            </div>
            <div className="shell-status__chips">
              <span className="status-chip status-chip--muted">{connections.length ? `${connections.length} saved` : 'No saved profiles'}</span>
              <span className="status-chip status-chip--muted">{activeConnection?.tenant_id || 'No tenant'}</span>
            </div>
          </div>
          <div className="stack">
            <label className="field-label" htmlFor="connection-picker">
              Switch connection
            </label>
            <select
              id="connection-picker"
              className="input"
              value={activeConnectionId || ''}
              onChange={(event) => {
                if (!event.target.value) {
                  return;
                }
                selectConnection(Number(event.target.value));
              }}
              disabled={!connections.length || selectConnectionPending}
            >
              <option value="">Choose connection</option>
              {connections.map((connection) => (
                <option key={connection.id} value={connection.id}>
                  {connection.label}
                </option>
              ))}
            </select>
          </div>
          <div className="shell-mini-grid">
            <div className="shell-mini-card">
              <div className="shell-mini-card__label">Workspace</div>
              <div className="shell-mini-card__value">{activeConnection?.active_workspace_name || activeConnection?.active_workspace_id || 'Not selected'}</div>
            </div>
            <div className="shell-mini-card">
              <div className="shell-mini-card__label">Semantic model</div>
              <div className="shell-mini-card__value">{activeConnection?.active_semantic_model_name || activeConnection?.active_semantic_model_id || 'Not selected'}</div>
            </div>
          </div>
        </section>

        <section className="shell-panel shell-panel--muted">
          <div className="section-title">Focus</div>
          <div className="shell-focus">
            <CheckCircle2 size={16} />
            <span>{currentPathLabel}</span>
          </div>
          {notice ? <div className="shell-notice">{notice}</div> : null}
        </section>
      </aside>

      <div className="shell-main">
        <Outlet />
      </div>
    </div>
  );
}
