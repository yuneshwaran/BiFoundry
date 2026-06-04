import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import ReportSidebar from '../components/ReportList/ReportSidebar';
import {
  createCanvasReport,
  deleteCanvasReport,
  importVisualTemplates,
  importSemanticModel,
  listCanvasReports,
  listSemanticModels,
  listVisualTemplates,
} from '../services/canvasApi';

export default function ReportListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newReportName, setNewReportName] = useState('Untitled Canvas');
  const [newReportProjectId, setNewReportProjectId] = useState('');
  const [templateImportFile, setTemplateImportFile] = useState(null);
  const [semanticImportFile, setSemanticImportFile] = useState(null);
  const [importName, setImportName] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const reportsQuery = useQuery({
    queryKey: ['canvas-reports'],
    queryFn: listCanvasReports,
  });

  const modelsQuery = useQuery({
    queryKey: ['semantic-models'],
    queryFn: listSemanticModels,
  });

  const templatesQuery = useQuery({
    queryKey: ['visual-templates'],
    queryFn: listVisualTemplates,
  });

  const createMutation = useMutation({
    mutationFn: createCanvasReport,
    onSuccess: async (created) => {
      setNotice(`Created ${created.name}.`);
      await queryClient.invalidateQueries({ queryKey: ['canvas-reports'] });
      navigate(`/canvas/${created.id}`);
    },
    onError: (requestError) => setError(requestError.message || 'Failed to create canvas report.'),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCanvasReport,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['canvas-reports'] });
      setNotice('Report deleted.');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete canvas report.'),
  });

  const importTemplateMutation = useMutation({
    mutationFn: (file) => importVisualTemplates(file),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['visual-templates'] });
      setNotice('Imported PBIP template library.');
      setTemplateImportFile(null);
      setImportName('');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to import PBIP template.'),
  });

  const importSemanticMutation = useMutation({
    mutationFn: ({ file, name }) => importSemanticModel(file, name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['semantic-models'] });
      setNotice('Imported semantic model.');
      setSemanticImportFile(null);
      setImportName('');
    },
    onError: (requestError) => setError(requestError.message || 'Failed to import semantic model.'),
  });

  const handleCreateReport = () => {
    if (!newReportProjectId) {
      setError('Choose a semantic model before creating a report.');
      return;
    }
    createMutation.mutate({
      name: newReportName.trim() || 'Untitled Canvas',
      project_id: Number(newReportProjectId),
      settings: {
        theme_color: '#154360',
        canvas_width: 1280,
        canvas_height: 720,
      },
    });
  };

  const handleDeleteReport = (reportId) => {
    if (!window.confirm('Delete this canvas report?')) {
      return;
    }
    deleteMutation.mutate(reportId);
  };

  const handleImportTemplate = () => {
    if (!templateImportFile) {
      return;
    }
    importTemplateMutation.mutate(templateImportFile);
  };

  const handleImportSemantic = () => {
    if (!semanticImportFile) {
      return;
    }
    importSemanticMutation.mutate({ file: semanticImportFile, name: importName.trim() || undefined });
  };

  const reports = useMemo(() => reportsQuery.data || [], [reportsQuery.data]);
  const semanticModels = useMemo(() => modelsQuery.data || [], [modelsQuery.data]);
  const visualTemplates = useMemo(() => templatesQuery.data || [], [templatesQuery.data]);

  useEffect(() => {
    if (!newReportProjectId && semanticModels.length) {
      setNewReportProjectId(String(semanticModels[0].id));
    }
  }, [newReportProjectId, semanticModels]);

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BI Foundry</div>
          <h1>Canvas reports</h1>
          <p>Import PBIP templates into the DB-backed library, choose a datasource, then open the canvas editor to bind fields and generate a PBIP package.</p>
        </div>
        <div className="hero__status">
          <div className="status-chip">{reportsQuery.isLoading ? 'Loading...' : `${reports.length} reports`}</div>
          <div className="status-chip status-chip--muted">{semanticModels.length ? `${semanticModels.length} semantic models` : 'No semantic models'}</div>
          <div className="status-chip status-chip--muted">
            {templatesQuery.isLoading ? 'Loading templates...' : `${visualTemplates.length} templates`}
          </div>
        </div>
      </header>

      {error ? <div className="status-banner status-banner--error">{error}</div> : null}
      {notice ? <div className="status-banner status-banner--success">{notice}</div> : null}

      <main className="workspace page-grid page-grid--builder">
        <div className="page-column page-column--left">
          <ReportSidebar
            canvasReports={reports}
            selectedReportId={null}
            newReportName={newReportName}
            newReportSemanticModelId={newReportProjectId}
            onNewReportNameChange={setNewReportName}
            sourceModels={semanticModels}
            onNewReportSemanticModelChange={(value) => setNewReportProjectId(String(value))}
            onCreateReport={handleCreateReport}
            onSelectReport={(reportId) => navigate(`/canvas/${reportId}`)}
            onDeleteReport={handleDeleteReport}
            onCloneReport={() => {}}
            loading={createMutation.isPending || deleteMutation.isPending}
          />
        </div>

        <div className="page-column page-column--center">
          <section className="canvas-shell">
            <div className="canvas-shell__header">
              <div>
                <div className="section-title">Import semantic model</div>
                <div className="canvas-shell__subtitle">Upload a PBIP zip to seed the model picker that canvas reports connect to.</div>
              </div>
            </div>
            <div className="stack">
              <input className="input" type="file" accept=".zip" onChange={(event) => setSemanticImportFile(event.target.files?.[0] || null)} />
              <input
                className="input"
                type="text"
                value={importName}
                onChange={(event) => setImportName(event.target.value)}
                placeholder="Optional semantic model name"
              />
              <button className="button button--primary" type="button" onClick={handleImportSemantic} disabled={importSemanticMutation.isPending || !semanticImportFile}>
                Import semantic model
              </button>
            </div>
          </section>

          <section className="canvas-shell" style={{ marginTop: '1rem' }}>
            <div className="canvas-shell__header">
              <div>
                <div className="section-title">Import PBIP template</div>
                <div className="canvas-shell__subtitle">Upload a report PBIP to seed the visual template library.</div>
              </div>
            </div>
            <div className="stack">
              <input className="input" type="file" accept=".zip" onChange={(event) => setTemplateImportFile(event.target.files?.[0] || null)} />
              <button className="button button--primary" type="button" onClick={handleImportTemplate} disabled={importTemplateMutation.isPending || !templateImportFile}>
                Import PBIP template
              </button>
            </div>
          </section>
        </div>

        <div className="page-column page-column--right">
          <section className="properties-panel">
            <div className="section-title">Template Library</div>
            <div className="panel-card">
              <div className="panel-card__title">Database-backed visuals</div>
              <div className="helper-text">
                The canvas editor pulls these templates from the database. Uploading a PBIP here seeds the library without any hard-coded visual definitions.
              </div>
              <div className="mini-summary">
                <div>{visualTemplates.length} templates available</div>
                {visualTemplates.slice(0, 5).map((template) => (
                  <div key={template.id}>
                    {template.name} · {template.visual_type}
                  </div>
                ))}
              </div>
            </div>
            <div className="section-title">Getting Started</div>
            <div className="panel-card">
              <div className="panel-card__title">Workflow</div>
              <div className="helper-text">
                1. Import a PBIP template into the library.
                <br />
                2. Choose a datasource and create a canvas report.
                <br />
                3. Add pages and template visuals in the editor.
                <br />
                4. Validate and compile to PBIP.
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
