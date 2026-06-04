import React, { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  createPowerBiConnection,
  deletePowerBiConnection,
  startPowerBiLogin,
  updatePowerBiConnection,
} from '../services/projectApi';
import { usePowerBi } from '../context/PowerBiContext';

function toBlank(value) {
  if (!value) {
    return '';
  }
  return String(value).toLowerCase() === 'common' ? '' : String(value);
}

function buildForm(connection, defaults = {}) {
  return {
    label: connection?.label || 'Power BI Connection',
    tenant_id: toBlank(connection?.tenant_id || defaults.tenant_id),
    authority_base: connection?.authority_base || defaults.authority_base || '',
    client_id: connection?.client_id || defaults.client_id || '',
    redirect_uri: connection?.redirect_uri || defaults.redirect_uri || '',
    scopes: connection?.scopes || defaults.scopes || '',
    owner_user_email: connection?.owner_user_email || '',
    owner_user_name: connection?.owner_user_name || '',
  };
}

function connectionStatusText(connection) {
  if (connection?.session?.is_authenticated) {
    return connection.session.user_email || connection.session.user_name || 'Authenticated';
  }
  return 'Not authenticated yet';
}

export default function ConnectionsPage() {
  const {
    config,
    activeConnection,
    connections,
    refreshConnections,
    selectConnection,
    setNotice,
  } = usePowerBi();
  const [selectedConnectionId, setSelectedConnectionId] = useState(activeConnection?.id || null);
  const [form, setForm] = useState(() => buildForm(activeConnection, config));
  const [formTouched, setFormTouched] = useState(false);
  const [error, setError] = useState('');
  const [notice, setLocalNotice] = useState('');

  useEffect(() => {
    if (!selectedConnectionId && activeConnection?.id) {
      setSelectedConnectionId(activeConnection.id);
    }
  }, [activeConnection?.id, selectedConnectionId]);

  useEffect(() => {
    const selected = connections.find((connection) => connection.id === selectedConnectionId) || null;
    if (selected) {
      setForm(buildForm(selected, config));
      setFormTouched(false);
      return;
    }
    if (!selectedConnectionId && !formTouched) {
      setForm(buildForm(null, config));
    }
  }, [config, connections, formTouched, selectedConnectionId]);

  useEffect(() => {
    if (!selectedConnectionId && !formTouched) {
      setForm(buildForm(null, config));
    }
  }, [config, formTouched, selectedConnectionId]);

  const selectedConnection = useMemo(
    () => connections.find((connection) => connection.id === selectedConnectionId) || null,
    [connections, selectedConnectionId],
  );

  const createMutation = useMutation({
    mutationFn: createPowerBiConnection,
    onSuccess: async (created) => {
      setNotice(`Created connection "${created.label}".`);
      setLocalNotice(`Created connection "${created.label}".`);
      await refreshConnections();
      setSelectedConnectionId(created.id);
      if (created.is_active) {
        selectConnection(created.id);
      }
    },
    onError: (requestError) => setError(requestError.message || 'Failed to create connection.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ connectionId, payload }) => updatePowerBiConnection(connectionId, payload),
    onSuccess: async (updated) => {
      setNotice(`Updated connection "${updated.label}".`);
      setLocalNotice(`Updated connection "${updated.label}".`);
      await refreshConnections();
      setSelectedConnectionId(updated.id);
    },
    onError: (requestError) => setError(requestError.message || 'Failed to update connection.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePowerBiConnection,
    onSuccess: async () => {
      setNotice('Connection deleted.');
      setLocalNotice('Connection deleted.');
      setSelectedConnectionId(null);
      await refreshConnections();
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete connection.'),
  });

  const loginMutation = useMutation({
    mutationFn: startPowerBiLogin,
    onSuccess: (payload) => {
      window.location.href = payload.authorization_url;
    },
    onError: (requestError) => setError(requestError.message || 'Failed to start Power BI login.'),
  });

  const handleSubmit = (connectAfterSave = false) => {
    setError('');
    const payload = {
      label: form.label.trim() || 'Power BI Connection',
      tenant_id: form.tenant_id.trim(),
      authority_base: form.authority_base.trim(),
      client_id: form.client_id.trim(),
      redirect_uri: form.redirect_uri.trim(),
      scopes: form.scopes.trim(),
      owner_user_email: form.owner_user_email.trim(),
      owner_user_name: form.owner_user_name.trim(),
      is_active: !connections.length,
    };

    if (selectedConnection?.id) {
      updateMutation.mutate(
        {
          connectionId: selectedConnection.id,
          payload,
        },
        {
          onSuccess: (updated) => {
            if (connectAfterSave) {
              loginMutation.mutate(updated.id);
            }
          },
        },
      );
      return;
    }

    createMutation.mutate(payload, {
      onSuccess: (created) => {
        if (connectAfterSave) {
          loginMutation.mutate(created.id);
        }
      },
    });
  };

  const handleSelectExisting = (connection) => {
    setSelectedConnectionId(connection.id);
    setForm(buildForm(connection, config));
    setFormTouched(false);
  };

  const handleNewProfile = () => {
    setSelectedConnectionId(null);
    setForm(buildForm(null, config));
    setFormTouched(false);
    setError('');
  };

  const handleConnect = (connectionId) => {
    loginMutation.mutate(connectionId);
  };

  const handleDelete = (connection) => {
    if (window.confirm(`Delete connection "${connection.label}"?`)) {
      deleteMutation.mutate(connection.id);
    }
  };

  return (
    <div className="page-stack">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BIFoundry</div>
          <h1>Power BI Connections</h1>
          <p>Create tenant-specific Power BI profiles, sign in with Entra, and pick the workspace and semantic model your projects should use.</p>
        </div>
        <div className="hero__status">
          <div className="status-chip">{connections.length ? `${connections.length} profiles` : 'No saved profiles'}</div>
          <div className="status-chip status-chip--muted">{activeConnection?.label || 'No active profile'}</div>
        </div>
      </header>

      {error ? <div className="status-banner status-banner--error">{error}</div> : null}
      {notice ? <div className="status-banner status-banner--success">{notice}</div> : null}

      <main className="workspace page-grid page-grid--builder">
        <section className="project-panel">
          <div className="section-title">Saved profiles</div>
          <div className="list">
            {connections.map((connection) => (
              <div
                key={connection.id}
                className={`connection-card${selectedConnectionId === connection.id ? ' connection-card--active' : ''}`}
                onClick={() => handleSelectExisting(connection)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    handleSelectExisting(connection);
                  }
                }}
              >
                <div className="connection-card__header">
                  <div>
                    <div className="connection-card__title">{connection.label}</div>
                    <div className="connection-card__meta">{connectionStatusText(connection)}</div>
                  </div>
                  {connection.is_active ? <span className="status-chip">Active</span> : null}
                </div>
                <div className="connection-card__grid">
                  <div>
                    <div className="field-label">Tenant</div>
                    <div>{connection.tenant_id}</div>
                  </div>
                  <div>
                    <div className="field-label">Workspace</div>
                    <div>{connection.active_workspace_name || connection.active_workspace_id || 'Not selected'}</div>
                  </div>
                  <div>
                    <div className="field-label">Model</div>
                    <div>{connection.active_semantic_model_name || connection.active_semantic_model_id || 'Not selected'}</div>
                  </div>
                </div>
                <div className="connection-card__actions">
                  <button className="button" type="button" onClick={(event) => { event.stopPropagation(); selectConnection(connection.id); }}>
                    Make active
                  </button>
                  <button className="button button--primary" type="button" onClick={(event) => { event.stopPropagation(); handleConnect(connection.id); }}>
                    Connect
                  </button>
                  <button className="button button--danger" type="button" onClick={(event) => { event.stopPropagation(); handleDelete(connection); }}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {!connections.length ? <div className="empty-state">No Power BI connection profiles yet.</div> : null}
          </div>
        </section>

        <section className="canvas-shell">
          <div className="canvas-shell__header">
            <div>
              <div className="section-title">{selectedConnection?.id ? 'Edit profile' : 'New profile'}</div>
              <div className="canvas-shell__subtitle">
                Fill in your tenant and Entra details, then connect to authorize workspaces and semantic models.
              </div>
            </div>
            <button className="button" type="button" onClick={handleNewProfile}>
              New profile
            </button>
          </div>
          <div className="stack">
            <input
              className="input"
              value={form.label}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, label: event.target.value }));
              }}
              placeholder="Connection label"
            />
            <input
              className="input"
              value={form.tenant_id}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, tenant_id: event.target.value }));
              }}
              placeholder="Tenant id"
            />
            <input
              className="input"
              value={form.authority_base}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, authority_base: event.target.value }));
              }}
              placeholder="Authority base"
            />
            <input
              className="input"
              value={form.client_id}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, client_id: event.target.value }));
              }}
              placeholder="Client id (optional override)"
            />
            <input
              className="input"
              value={form.redirect_uri}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, redirect_uri: event.target.value }));
              }}
              placeholder="Redirect URI"
            />
            <textarea
              className="input input--textarea"
              value={form.scopes}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, scopes: event.target.value }));
              }}
              placeholder="Scopes"
            />
            <input
              className="input"
              value={form.owner_user_email}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, owner_user_email: event.target.value }));
              }}
              placeholder="Expected user email or UPN"
            />
            <input
              className="input"
              value={form.owner_user_name}
              onChange={(event) => {
                setFormTouched(true);
                setForm((current) => ({ ...current, owner_user_name: event.target.value }));
              }}
              placeholder="Friendly user name"
            />
            <div className="stack">
              <button className="button button--primary" type="button" onClick={() => handleSubmit(false)} disabled={createMutation.isPending || updateMutation.isPending}>
                Save profile
              </button>
              <button className="button button--accent" type="button" onClick={() => handleSubmit(true)} disabled={loginMutation.isPending || createMutation.isPending || updateMutation.isPending}>
                Save and connect
              </button>
            </div>
          </div>
        </section>

        <section className="properties-panel">
          <div className="section-title">Connection summary</div>
          <div className="panel-card">
            <div className="panel-card__title">{selectedConnection?.label || 'No profile selected'}</div>
            <div className="helper-text">
              {selectedConnection?.session?.is_authenticated
                ? `Signed in as ${selectedConnection.session.user_email || selectedConnection.session.user_name || 'connected user'}`
                : 'Sign in to load workspaces and semantic models.'}
            </div>
            <div className="mini-summary">
              <div>Tenant: {selectedConnection?.tenant_id || 'Not set'}</div>
              <div>Workspace: {selectedConnection?.active_workspace_name || selectedConnection?.active_workspace_id || 'Not selected'}</div>
              <div>Model: {selectedConnection?.active_semantic_model_name || selectedConnection?.active_semantic_model_id || 'Not selected'}</div>
            </div>
          </div>
          <div className="section-title">Tips</div>
          <div className="panel-card">
            <div className="panel-card__title">Avoid /common</div>
            <div className="helper-text">
              Give each connection a tenant-specific authority. This app now stores connection profiles separately, so different users can keep their own saved Entra details.
            </div>
            <div className="helper-text" style={{ marginTop: '0.75rem' }}>
              To unlock tenant-wide metadata scans, add `Tenant.Read.All` to the scopes and enable the Power BI admin API metadata scanning tenant settings.
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
