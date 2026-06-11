import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  Cable,
  FileStack,
  LayoutTemplate,
  TrendingUp,
  Workflow,
  Zap,
} from 'lucide-react';
import { usePowerBi } from '../context/PowerBiContext';

const QUICK_LINKS = [
  {
    id: 'connections',
    label: 'Connections',
    description: 'Manage Azure AD profiles',
    icon: Cable,
    color: 'purple',
    path: '/connections',
  },
  {
    id: 'projects',
    label: 'Projects',
    description: 'Open or create report projects',
    icon: BarChart3,
    color: 'teal',
    path: '/projects',
  },
  {
    id: 'create',
    label: 'Create Report',
    description: 'Step-by-step report wizard',
    icon: FileStack,
    color: 'blue',
    path: '/create',
  },
  {
    id: 'templates',
    label: 'Templates',
    description: 'Browse & import PBIP templates',
    icon: LayoutTemplate,
    color: 'pink',
    path: '/templates',
  },
];

function ConnectionStatus({ connection }) {
  if (connection?.session?.is_authenticated) {
    return connection.session.user_email || connection.session.user_name || 'Authenticated';
  }
  return 'Create a connection profile and sign in to get started.';
}

export default function HomePage() {
  const navigate = useNavigate();
  const { activeConnection, connections } = usePowerBi();

  const isAuthenticated = activeConnection?.session?.is_authenticated;

  return (
    <div className="page-content">
      {/* Hero */}
      <div className="page-hero">
        <div>
          <div className="page-hero__eyebrow">
            <Zap size={12} />
            BI-Foundry Studio
          </div>
          <h1 className="page-hero__title">Power BI<br />Report Builder</h1>
          <p className="page-hero__subtitle">
            Connect to Azure AD, pick a semantic model, design report pages visually, and compile
            PBIP packages — all in one workspace.
          </p>
        </div>
        <div className="page-hero__chips">
          <div className="hero-chip">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: isAuthenticated ? '#10b981' : '#6b7280',
                display: 'inline-block',
                boxShadow: isAuthenticated ? '0 0 6px rgba(16,185,129,0.5)' : 'none',
              }}
            />
            {activeConnection?.label || 'No connection'}
          </div>
          <div className="hero-chip">
            <Workflow size={12} />
            {connections.length} profile{connections.length !== 1 ? 's' : ''}
          </div>
          <div className="hero-chip">
            <TrendingUp size={12} />
            {activeConnection?.active_workspace_name || 'No workspace'}
          </div>
        </div>
      </div>

      {/* Quick links grid */}
      <div>
        <div className="section-label">Quick Access</div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          {QUICK_LINKS.map((link) => {
            const Icon = link.icon;
            return (
              <button
                key={link.id}
                type="button"
                className={`cat-card cat-card--${link.color}`}
                onClick={() => navigate(link.path)}
                style={{ border: 'none', fontFamily: 'inherit', textAlign: 'left' }}
              >
                <div className="cat-card__bg-decoration" />
                <div className="cat-card__icon">
                  <Icon size={22} />
                </div>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '1rem', marginBottom: 2 }}>
                    {link.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', opacity: 0.82 }}>{link.description}</div>
                </div>
                <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'flex-end' }}>
                  <ArrowRight size={16} style={{ opacity: 0.7 }} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Status grid */}
      <div className="page-grid-3" style={{ alignItems: 'start' }}>
        {/* Active Profile */}
        <div className="card card--md">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: 'linear-gradient(135deg, #7c3aed, #9f5de8)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                }}
              >
                <Cable size={18} />
              </div>
              <div>
                <div className="card-title">Active Profile</div>
                <div className="card-meta">{activeConnection?.label || 'None selected'}</div>
              </div>
            </div>
          </div>
          <div className="card-body">
            <div className="panel-card__kv">
              {[
                { label: 'Tenant ID', value: activeConnection?.tenant_id },
                { label: 'Status', value: isAuthenticated ? '✓ Authenticated' : 'Not signed in' },
                { label: 'User', value: activeConnection?.session?.user_email || activeConnection?.owner_user_email },
              ].map((row) => (
                <div key={row.label} className="panel-card__kv-row">
                  <div className="panel-card__kv-label">{row.label}</div>
                  <div className="panel-card__kv-value" style={{ color: row.value ? undefined : '#94a3b8', fontStyle: row.value ? 'normal' : 'italic' }}>
                    {row.value || 'Not set'}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <button className="btn btn-primary btn-full" onClick={() => navigate('/connections')} type="button">
                <Cable size={15} />
                Manage Connections
              </button>
            </div>
          </div>
        </div>

        {/* Workspace Status */}
        <div className="card card--md">
          <div className="card-header">
            <div className="card-title">Workspace Status</div>
            <div className="card-meta">Active connection workspace &amp; model</div>
          </div>
          <div className="card-body">
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 12,
                marginBottom: 16,
              }}
            >
              {[
                { label: 'Workspace', value: activeConnection?.active_workspace_name || activeConnection?.active_workspace_id },
                { label: 'Semantic Model', value: activeConnection?.active_semantic_model_name || activeConnection?.active_semantic_model_id },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '12px',
                  }}
                >
                  <div className="panel-card__kv-label">{item.label}</div>
                  <div
                    style={{
                      fontSize: '0.84rem',
                      fontWeight: 600,
                      marginTop: 4,
                      color: item.value ? 'var(--text)' : 'var(--muted-light)',
                      fontStyle: item.value ? 'normal' : 'italic',
                    }}
                  >
                    {item.value || 'Not selected'}
                  </div>
                </div>
              ))}
            </div>
            <button className="btn btn-ghost btn-full" onClick={() => navigate('/projects')} type="button">
              <BarChart3 size={15} />
              Go to Projects
            </button>
          </div>
        </div>

        {/* Getting Started */}
        <div className="card card--md">
          <div className="card-header">
            <div className="card-title">Getting Started</div>
            <div className="card-meta">Follow these steps to build your first report</div>
          </div>
          <div className="card-body">
            {[
              { num: 1, text: 'Create a Power BI connection profile.' },
              { num: 2, text: 'Sign in with your Azure AD tenant credentials.' },
              { num: 3, text: 'Select a workspace and semantic model.' },
              { num: 4, text: 'Use the Create Report wizard to design pages.' },
              { num: 5, text: 'Compile and export the PBIP package.' },
            ].map((step) => (
              <div
                key={step.num}
                style={{
                  display: 'flex',
                  gap: 12,
                  alignItems: 'flex-start',
                  marginBottom: 14,
                }}
              >
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, var(--purple), #9f5de8)',
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    flexShrink: 0,
                  }}
                >
                  {step.num}
                </div>
                <div style={{ fontSize: '0.84rem', color: 'var(--text-2)', lineHeight: 1.5, paddingTop: 2 }}>
                  {step.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
