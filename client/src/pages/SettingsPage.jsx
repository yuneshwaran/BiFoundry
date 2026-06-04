import React from 'react';
import { useNavigate } from 'react-router-dom';
import { usePowerBi } from '../context/PowerBiContext';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { config, activeConnection } = usePowerBi();

  return (
    <div className="page-stack">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BIFoundry</div>
          <h1>Settings</h1>
          <p>Review the bootstrap Power BI defaults coming from the environment and jump back into the connection manager when you need to edit a profile.</p>
        </div>
        <div className="hero__status">
          <div className="status-chip">{activeConnection?.label || 'No active connection'}</div>
          <div className="status-chip status-chip--muted">{activeConnection?.tenant_id || 'Tenant not set'}</div>
        </div>
      </header>

      <main className="workspace page-grid page-grid--builder">
        <section className="project-panel">
          <div className="section-title">Defaults</div>
          <div className="panel-card">
            <div className="panel-card__title">Bootstrap configuration</div>
            <div className="mini-summary">
              <div>Tenant: {config.tenant_id || 'Not configured'}</div>
              <div>Authority: {config.authority_base || 'Not configured'}</div>
              <div>Redirect URI: {config.redirect_uri || 'Not configured'}</div>
              <div>Scopes: {config.scopes || 'Not configured'}</div>
              <div>Client id: {config.client_id || 'Not configured'}</div>
            </div>
          </div>
        </section>

        <section className="canvas-shell">
          <div className="canvas-shell__header">
            <div>
              <div className="section-title">Connection management</div>
              <div className="canvas-shell__subtitle">Use the dedicated connections page for creating, editing, and authorizing Power BI profiles.</div>
            </div>
          </div>
          <div className="stack">
            <button className="button button--primary" type="button" onClick={() => navigate('/connections')}>
              Open Power BI Connections
            </button>
            <button className="button" type="button" onClick={() => navigate('/projects')}>
              Back to projects
            </button>
          </div>
        </section>

        <section className="properties-panel">
          <div className="section-title">Notes</div>
          <div className="panel-card">
            <div className="panel-card__title">User-scoped auth</div>
            <div className="helper-text">
              Connection profiles are stored in the database and keyed by the Entra identity returned from Power BI. Local browser storage is no longer the source of truth for auth state.
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
