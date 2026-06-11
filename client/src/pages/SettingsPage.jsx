import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  Cable,
  ExternalLink,
  FileText,
  Info,
  Key,
  LayoutTemplate,
  RefreshCw,
  Settings2,
  Shield,
  UserCircle,
} from 'lucide-react';
import { usePowerBi } from '../context/PowerBiContext';

const QUICK_ACTIONS = [
  {
    id: 'connections',
    label: 'Manage Connections',
    meta: 'Add, edit, or remove Azure profiles',
    icon: Cable,
    colorClass: 'quick-action-btn__icon--purple',
    path: '/connections',
  },
  {
    id: 'templates',
    label: 'Browse Templates',
    meta: 'Import PBIP report templates',
    icon: LayoutTemplate,
    colorClass: 'quick-action-btn__icon--teal',
    path: '/templates',
  },
  {
    id: 'projects',
    label: 'Go to Projects',
    meta: 'Open or create report projects',
    icon: FileText,
    colorClass: 'quick-action-btn__icon--blue',
    path: '/projects',
  },
];

const TIPS = [
  {
    icon: Shield,
    title: 'User-scoped Auth',
    body: 'Connection profiles are stored in the database and keyed by the Entra identity returned from Power BI. Browser storage is no longer the auth source of truth.',
  },
  {
    icon: Key,
    title: 'Avoid /common Tenant',
    body: 'Use a tenant-specific authority URL (e.g. https://login.microsoftonline.com/{tenantId}) instead of /common to avoid cross-tenant token issues.',
  },
  {
    icon: AlertCircle,
    title: 'Tenant.Read.All',
    body: 'To unlock full metadata scans, add Tenant.Read.All to scopes and enable the Power BI admin API metadata scanning setting in your tenant.',
  },
];

export default function SettingsPage() {
  const navigate = useNavigate();
  const { config, activeConnection } = usePowerBi();

  const configRows = [
    { key: 'Tenant ID', value: config?.tenant_id },
    { key: 'Authority Base', value: config?.authority_base },
    { key: 'Redirect URI', value: config?.redirect_uri },
    { key: 'Scopes', value: config?.scopes },
    { key: 'Client ID', value: config?.client_id },
  ];

  return (
    <div className="page-content">
      {/* Hero */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <Settings2 size={12} />
            System Configuration
          </div>
          <h1 className="page-hero__title">Settings</h1>
          <p className="page-hero__subtitle">
            Review the bootstrap Power BI defaults from the environment and manage your
            connection profiles and tenant configuration.
          </p>
        </div>
        <div className="page-hero__chips">
          <div className="hero-chip">
            <UserCircle size={12} />
            {activeConnection?.label || 'No active connection'}
          </div>
          <div className="hero-chip">
            <Shield size={12} />
            {activeConnection?.tenant_id || 'Tenant not set'}
          </div>
        </div>
      </div>

      {/* 3-column grid */}
      <div className="settings-grid">
        {/* Left: Quick actions */}
        <div className="sticky-panel">
          <div className="section-label">Quick Actions</div>
          <div className="card card--md">
            <div className="card-body" style={{ padding: '12px' }}>
              <div className="quick-actions-list">
                {QUICK_ACTIONS.map((action) => {
                  const Icon = action.icon;
                  return (
                    <button
                      key={action.id}
                      className="quick-action-btn"
                      type="button"
                      onClick={() => navigate(action.path)}
                    >
                      <div className={`quick-action-btn__icon ${action.colorClass}`}>
                        <Icon size={17} />
                      </div>
                      <div>
                        <div className="quick-action-btn__label">{action.label}</div>
                        <div className="quick-action-btn__meta">{action.meta}</div>
                      </div>
                      <ExternalLink size={14} style={{ marginLeft: 'auto', opacity: 0.4 }} />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Active profile summary */}
          <div className="section-label" style={{ marginTop: 20 }}>Active Profile</div>
          <div className="card card--md">
            <div className="card-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <div
                  style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: activeConnection ? 'linear-gradient(135deg,#7c3aed,#9f5de8)' : 'var(--bg-2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: activeConnection ? '#fff' : 'var(--muted)',
                  }}
                >
                  <Cable size={18} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                    {activeConnection?.label || 'No connection'}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>
                    {activeConnection?.session?.is_authenticated ? '✓ Authenticated' : 'Not signed in'}
                  </div>
                </div>
              </div>
              <div className="panel-card__kv">
                {[
                  { label: 'Workspace', value: activeConnection?.active_workspace_name },
                  { label: 'Model', value: activeConnection?.active_semantic_model_name },
                ].map((r) => (
                  <div key={r.label} className="panel-card__kv-row">
                    <div className="panel-card__kv-label">{r.label}</div>
                    <div className="panel-card__kv-value" style={{ color: r.value ? undefined : 'var(--muted-light)', fontStyle: r.value ? 'normal' : 'italic' }}>
                      {r.value || 'Not selected'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Center: Bootstrap config */}
        <div>
          <div className="section-label">Azure AD Defaults</div>
          <div className="card card--md">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div
                  style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: 'linear-gradient(135deg,#2563eb,#60a5fa)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff',
                  }}
                >
                  <RefreshCw size={16} />
                </div>
                <div>
                  <div className="card-title">Bootstrap Configuration</div>
                  <div className="card-meta">Environment defaults — read-only</div>
                </div>
              </div>
            </div>
            <div className="config-kv-list">
              {configRows.map((row) => (
                <div key={row.key} className="config-kv-row">
                  <div className="config-kv-key">{row.key}</div>
                  <div className={`config-kv-value${row.value ? '' : ' config-kv-value--empty'}`}>
                    {row.value || 'Not configured'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Connection management */}
          <div className="section-label" style={{ marginTop: 20 }}>Connection Management</div>
          <div className="card card--md">
            <div className="card-body">
              <div style={{ fontSize: '0.87rem', color: 'var(--text-2)', marginBottom: 16, lineHeight: 1.6 }}>
                Use the dedicated Connections page for creating, editing, and authorizing Power BI
                profiles. Each profile stores its own Entra credentials and workspace selection.
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={() => navigate('/connections')}
                >
                  <Cable size={15} />
                  Open Connections
                </button>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => navigate('/projects')}
                >
                  Back to Projects
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Tips */}
        <div className="sticky-panel">
          <div className="section-label">Guidance &amp; Tips</div>
          {TIPS.map((tip) => {
            const Icon = tip.icon;
            return (
              <div key={tip.title} className="panel-card" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <div
                    style={{
                      width: 30, height: 30, borderRadius: 8,
                      background: 'var(--purple-light)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'var(--purple)',
                    }}
                  >
                    <Icon size={14} />
                  </div>
                  <div className="panel-card__title" style={{ margin: 0 }}>{tip.title}</div>
                </div>
                <div className="panel-card__body">{tip.body}</div>
              </div>
            );
          })}

          {/* Info callout */}
          <div
            style={{
              background: 'var(--blue-light)',
              border: '1px solid rgba(37,99,235,0.15)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 16px',
              display: 'flex',
              gap: 10,
              alignItems: 'flex-start',
            }}
          >
            <Info size={16} style={{ color: 'var(--blue)', flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: '0.82rem', color: '#1e40af', lineHeight: 1.55 }}>
              These environment defaults are read at application startup. To change them,
              update your backend <code>.env</code> file and restart the server.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
