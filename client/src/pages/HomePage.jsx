import React from 'react';
import { useNavigate } from 'react-router-dom';
import { usePowerBi } from '../context/PowerBiContext';

function activeConnectionStatus(connection) {
  if (connection?.session?.is_authenticated) {
    return connection.session.user_email || connection.session.user_name || 'Authenticated';
  }
  return 'Create a connection profile and sign in to see your workspace list.';
}

export default function HomePage() {
  const navigate = useNavigate();
  const { activeConnection, connections } = usePowerBi();

  return (
    <div className="page-stack">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BIFoundry</div>
          <h1>Home</h1>
          <p>Start here to confirm your Power BI connection, jump into projects, or open the connection settings.</p>
        </div>
        <div className="hero__status">
          <div className="status-chip">{activeConnection?.label || 'No active connection'}</div>
          <div className="status-chip status-chip--muted">{connections.length ? `${connections.length} saved profiles` : 'No saved profiles'}</div>
        </div>
      </header>

      <main className="workspace page-grid page-grid--builder">
        <section className="project-panel">
          <div className="section-title">Quick Actions</div>
          <div className="panel-card">
            <div className="panel-card__title">Power BI profile</div>
            <div className="helper-text">
              {activeConnectionStatus(activeConnection)}
            </div>
            <div className="stack">
              <button className="button button--primary" type="button" onClick={() => navigate('/connections')}>
                Open connections
              </button>
              <button className="button" type="button" onClick={() => navigate('/projects')}>
                Go to projects
              </button>
            </div>
          </div>
        </section>

        <section className="canvas-shell">
          <div className="canvas-shell__header">
            <div>
              <div className="section-title">Workspace status</div>
              <div className="canvas-shell__subtitle">The active profile drives the workspace and semantic model picker everywhere in the shell.</div>
            </div>
          </div>
          <div className="shell-mini-grid">
            <div className="shell-mini-card">
              <div className="shell-mini-card__label">Tenant</div>
              <div className="shell-mini-card__value">{activeConnection?.tenant_id || 'Not set'}</div>
            </div>
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

        <section className="properties-panel">
          <div className="section-title">Guidance</div>
          <div className="panel-card">
            <div className="panel-card__title">Next step</div>
            <div className="helper-text">
              1. Create or edit a connection profile.
              <br />
              2. Sign in against your tenant.
              <br />
              3. Select a workspace and semantic model.
              <br />
              4. Create a project shell and build the PBIP.
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
