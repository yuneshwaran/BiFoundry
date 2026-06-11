import React, { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Cable,
  Check,
  CircleX,
  Loader2,
  Plus,
  Server,
  Shield,
  Trash2,
  WifiOff,
  X,
  Zap,
} from 'lucide-react';
import {
  createPowerBiConnection,
  deletePowerBiConnection,
  startPowerBiLogin,
  updatePowerBiConnection,
} from '../services/projectApi';
import { usePowerBi } from '../context/PowerBiContext';

function toBlank(value) {
  if (!value) return '';
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

const ACCENT_COLORS = ['purple', 'teal', 'blue', 'pink', 'amber'];

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
  const [panelOpen, setPanelOpen] = useState(false);
  const [error, setError] = useState('');
  const [localNotice, setLocalNotice] = useState('');

  useEffect(() => {
    if (!selectedConnectionId && activeConnection?.id) {
      setSelectedConnectionId(activeConnection.id);
    }
  }, [activeConnection?.id, selectedConnectionId]);

  useEffect(() => {
    const selected = connections.find((c) => c.id === selectedConnectionId) || null;
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
    () => connections.find((c) => c.id === selectedConnectionId) || null,
    [connections, selectedConnectionId],
  );

  const createMutation = useMutation({
    mutationFn: createPowerBiConnection,
    onSuccess: async (created) => {
      setNotice(`Created connection "${created.label}".`);
      setLocalNotice(`Created "${created.label}".`);
      await refreshConnections();
      setSelectedConnectionId(created.id);
      setPanelOpen(false);
      if (created.is_active) selectConnection(created.id);
    },
    onError: (e) => setError(e.message || 'Failed to create connection.'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ connectionId, payload }) => updatePowerBiConnection(connectionId, payload),
    onSuccess: async (updated) => {
      setNotice(`Updated connection "${updated.label}".`);
      setLocalNotice(`Updated "${updated.label}".`);
      await refreshConnections();
      setSelectedConnectionId(updated.id);
      setPanelOpen(false);
    },
    onError: (e) => setError(e.message || 'Failed to update connection.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deletePowerBiConnection,
    onSuccess: async () => {
      setNotice('Connection deleted.');
      setLocalNotice('Connection deleted.');
      setSelectedConnectionId(null);
      await refreshConnections();
    },
    onError: (e) => setError(e.message || 'Failed to delete connection.'),
  });

  const loginMutation = useMutation({
    mutationFn: startPowerBiLogin,
    onSuccess: (payload) => { window.location.href = payload.authorization_url; },
    onError: (e) => setError(e.message || 'Failed to start Power BI login.'),
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
        { connectionId: selectedConnection.id, payload },
        {
          onSuccess: (updated) => {
            if (connectAfterSave) loginMutation.mutate(updated.id);
          },
        },
      );
      return;
    }

    createMutation.mutate(payload, {
      onSuccess: (created) => {
        if (connectAfterSave) loginMutation.mutate(created.id);
      },
    });
  };

  const handleSelectExisting = (conn) => {
    setSelectedConnectionId(conn.id);
    setForm(buildForm(conn, config));
    setFormTouched(false);
    setPanelOpen(true);
  };

  const handleNewProfile = () => {
    setSelectedConnectionId(null);
    setForm(buildForm(null, config));
    setFormTouched(false);
    setError('');
    setPanelOpen(true);
  };

  const handleConnect = (connectionId) => loginMutation.mutate(connectionId);

  const handleDelete = (conn) => {
    if (window.confirm(`Delete connection "${conn.label}"?`)) {
      deleteMutation.mutate(conn.id);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isConnecting = loginMutation.isPending;

  return (
    <div className="page-content">
      {/* Page Hero */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <Cable size={12} />
            Azure Active Directory
          </div>
          <h1 className="page-hero__title">Power BI Connections</h1>
          <p className="page-hero__subtitle">
            Create tenant-specific profiles, sign in with Microsoft Entra, and select the workspace
            and semantic model your projects should use.
          </p>
        </div>
        <div className="page-hero__chips">
          <div className="hero-chip">
            <Shield size={12} />
            {connections.length} profile{connections.length !== 1 ? 's' : ''} saved
          </div>
          <div className="hero-chip">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: activeConnection?.session?.is_authenticated ? '#10b981' : '#6b7280',
                display: 'inline-block',
              }}
            />
            {activeConnection?.label || 'No active profile'}
          </div>
        </div>
      </div>

      {/* Banners */}
      {error && (
        <div className="status-banner status-banner--error">
          <span><CircleX size={15} style={{ display: 'inline', marginRight: 6 }} />{error}</span>
          <button className="status-banner__close" onClick={() => setError('')} type="button"><X size={14} /></button>
        </div>
      )}
      {localNotice && (
        <div className="status-banner status-banner--success">
          <span><Check size={15} style={{ display: 'inline', marginRight: 6 }} />{localNotice}</span>
          <button className="status-banner__close" onClick={() => setLocalNotice('')} type="button"><X size={14} /></button>
        </div>
      )}

      {/* Main layout */}
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Connection cards grid */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div className="section-label" style={{ marginBottom: 0 }}>
              {connections.length ? `${connections.length} Saved Profile${connections.length !== 1 ? 's' : ''}` : 'Saved Profiles'}
            </div>
            <button className="btn btn-primary" onClick={handleNewProfile} type="button">
              <Plus size={16} />
              Add Connection
            </button>
          </div>

          {connections.length === 0 ? (
            <div className="card card--md">
              <div className="empty-state">
                <div className="empty-state__icon"><Cable size={24} /></div>
                <div className="empty-state__title">No connections yet</div>
                <div className="empty-state__body">
                  Add a Power BI connection profile to get started. You'll need your Azure AD
                  tenant details.
                </div>
                <button className="btn btn-primary" onClick={handleNewProfile} type="button">
                  <Plus size={15} />
                  Add First Connection
                </button>
              </div>
            </div>
          ) : (
            <div className="cards-grid">
              {connections.map((conn, idx) => {
                const color = ACCENT_COLORS[idx % ACCENT_COLORS.length];
                const isAuth = conn?.session?.is_authenticated;
                return (
                  <div
                    key={conn.id}
                    className={`conn-card${selectedConnectionId === conn.id ? ' conn-card--selected' : ''}`}
                    onClick={() => handleSelectExisting(conn)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSelectExisting(conn);
                      }
                    }}
                  >
                    <div className="conn-card__top">
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                        <div className={`conn-card__icon`} style={{
                          background: color === 'purple' ? 'linear-gradient(135deg,#7c3aed,#9f5de8)'
                            : color === 'teal' ? 'linear-gradient(135deg,#0d9488,#14b8a6)'
                            : color === 'blue' ? 'linear-gradient(135deg,#2563eb,#60a5fa)'
                            : color === 'pink' ? 'linear-gradient(135deg,#ec4899,#f472b6)'
                            : 'linear-gradient(135deg,#d97706,#f59e0b)',
                        }}>
                          <Server size={18} />
                        </div>
                        <div>
                          <div className="conn-card__title">{conn.label}</div>
                          <div className="conn-card__meta">
                            {conn.owner_user_email || conn.owner_user_name || 'No user specified'}
                          </div>
                        </div>
                      </div>
                      <div>
                        {isAuth ? (
                          <span className="badge badge--green">
                            <span className="badge__dot" />
                            Connected
                          </span>
                        ) : (
                          <span className="badge badge--grey">
                            <WifiOff size={10} />
                            Offline
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="conn-card__kv">
                      <div className="conn-card__kv-item">
                        <div className="conn-card__kv-label">Tenant ID</div>
                        <div className="conn-card__kv-value">{conn.tenant_id || '—'}</div>
                      </div>
                      <div className="conn-card__kv-item">
                        <div className="conn-card__kv-label">Workspace</div>
                        <div className="conn-card__kv-value">
                          {conn.active_workspace_name || conn.active_workspace_id || '—'}
                        </div>
                      </div>
                      <div className="conn-card__kv-item">
                        <div className="conn-card__kv-label">Semantic Model</div>
                        <div className="conn-card__kv-value">
                          {conn.active_semantic_model_name || conn.active_semantic_model_id || '—'}
                        </div>
                      </div>
                      <div className="conn-card__kv-item">
                        <div className="conn-card__kv-label">Status</div>
                        <div className="conn-card__kv-value" style={{ color: conn.is_active ? 'var(--teal)' : undefined }}>
                          {conn.is_active ? 'Active' : 'Saved'}
                        </div>
                      </div>
                    </div>

                    <div className="conn-card__actions" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        onClick={() => selectConnection(conn.id)}
                      >
                        Make Active
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        type="button"
                        onClick={() => handleConnect(conn.id)}
                        disabled={isConnecting}
                      >
                        {isConnecting ? <Loader2 size={14} className="spinner" style={{ animation: 'spin 0.7s linear infinite' }} /> : <Zap size={14} />}
                        Connect
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        type="button"
                        onClick={() => handleDelete(conn)}
                        style={{ marginLeft: 'auto' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right summary panel */}
        <div style={{ width: 280, flexShrink: 0 }} className="sticky-panel">
          <div className="section-label">Connection Summary</div>
          <div className="panel-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div
                style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: selectedConnection ? 'linear-gradient(135deg,#7c3aed,#9f5de8)' : 'var(--bg-2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: selectedConnection ? '#fff' : 'var(--muted)',
                }}
              >
                <Server size={18} />
              </div>
              <div>
                <div className="panel-card__title">
                  {selectedConnection?.label || 'No profile selected'}
                </div>
                <div className="panel-card__body" style={{ marginTop: 0 }}>
                  {selectedConnection?.session?.is_authenticated
                    ? `Signed in as ${selectedConnection.session.user_email || selectedConnection.session.user_name || 'user'}`
                    : 'Sign in to load workspace data.'}
                </div>
              </div>
            </div>
            <div className="panel-card__kv">
              {[
                { label: 'Tenant', value: selectedConnection?.tenant_id },
                { label: 'Workspace', value: selectedConnection?.active_workspace_name || selectedConnection?.active_workspace_id },
                { label: 'Model', value: selectedConnection?.active_semantic_model_name || selectedConnection?.active_semantic_model_id },
                { label: 'Authority', value: selectedConnection?.authority_base },
              ].map((row) => (
                <div key={row.label} className="panel-card__kv-row">
                  <div className="panel-card__kv-label">{row.label}</div>
                  <div
                    className="panel-card__kv-value"
                    style={{ color: row.value ? undefined : 'var(--muted-light)', fontStyle: row.value ? 'normal' : 'italic' }}
                  >
                    {row.value || 'Not set'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel-card" style={{ marginTop: 12 }}>
            <div className="panel-card__title">💡 Tips</div>
            <div className="panel-card__body">
              <p style={{ marginBottom: 10 }}>
                Avoid using <code>/common</code> as tenant. Each profile should have a
                tenant-specific authority URL.
              </p>
              <p>
                To enable full metadata scans, add <code>Tenant.Read.All</code> to your scopes and
                enable Power BI admin API scanning in tenant settings.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Slide-in form panel */}
      <div className={`panel-overlay${panelOpen ? ' panel-overlay--active' : ''}`}>
        <div className="panel-backdrop" onClick={() => setPanelOpen(false)} />
        <div className="slide-panel">
          <div className="slide-panel__header">
            <div className="slide-panel__title">
              {selectedConnection?.id ? 'Edit Profile' : 'New Connection Profile'}
            </div>
            <button
              className="btn btn-icon btn-ghost"
              type="button"
              onClick={() => setPanelOpen(false)}
            >
              <X size={18} />
            </button>
          </div>

          <div className="slide-panel__body">
            <div className="form-stack">
              {[
                { key: 'label', label: 'Label', placeholder: 'e.g. Contoso Production' },
                { key: 'tenant_id', label: 'Tenant ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
                { key: 'authority_base', label: 'Authority Base', placeholder: 'https://login.microsoftonline.com/' },
                { key: 'client_id', label: 'Client ID', placeholder: 'Client app registration ID' },
                { key: 'redirect_uri', label: 'Redirect URI', placeholder: 'http://localhost:3000/' },
                { key: 'owner_user_email', label: 'User Email', placeholder: 'user@contoso.com' },
                { key: 'owner_user_name', label: 'User Name', placeholder: 'Display name (optional)' },
              ].map(({ key, label, placeholder }) => (
                <div key={key} className="form-group">
                  <label className="form-label" htmlFor={`conn-${key}`}>{label}</label>
                  <input
                    id={`conn-${key}`}
                    className="form-input"
                    value={form[key]}
                    placeholder={placeholder}
                    onChange={(e) => {
                      setFormTouched(true);
                      setForm((prev) => ({ ...prev, [key]: e.target.value }));
                    }}
                  />
                </div>
              ))}
              <div className="form-group">
                <label className="form-label" htmlFor="conn-scopes">Scopes</label>
                <textarea
                  id="conn-scopes"
                  className="form-input form-input--textarea"
                  value={form.scopes}
                  placeholder="https://analysis.windows.net/powerbi/api/.default"
                  onChange={(e) => {
                    setFormTouched(true);
                    setForm((prev) => ({ ...prev, scopes: e.target.value }));
                  }}
                />
              </div>
            </div>
          </div>

          <div className="slide-panel__footer">
            <button
              className="btn btn-primary"
              type="button"
              onClick={() => handleSubmit(false)}
              disabled={isSaving}
              style={{ flex: 1 }}
            >
              {isSaving ? <Loader2 size={15} style={{ animation: 'spin 0.7s linear infinite' }} /> : null}
              Save Profile
            </button>
            <button
              className="btn btn-teal"
              type="button"
              onClick={() => handleSubmit(true)}
              disabled={isSaving || isConnecting}
              style={{ flex: 1 }}
            >
              <Zap size={15} />
              Save &amp; Connect
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
