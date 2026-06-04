import React from 'react';

export default function ReportSidebar({
  canvasReports,
  selectedReportId,
  newReportName,
  newReportSemanticModelId,
  onNewReportNameChange,
  sourceModels,
  onNewReportSemanticModelChange,
  onCreateReport,
  onSelectReport,
  onDeleteReport,
  onCloneReport,
  loading,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar__section">
        <div className="section-title">Canvas Reports</div>
        <div className="stack">
          <input
            className="input"
            type="text"
            value={newReportName}
            onChange={(event) => onNewReportNameChange(event.target.value)}
            placeholder="New report name"
          />
          <select
            className="input"
            value={newReportSemanticModelId}
            onChange={(event) => onNewReportSemanticModelChange(Number(event.target.value))}
          >
            <option value="">Choose datasource</option>
            {sourceModels.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
          <button
            className="button button--primary"
            onClick={onCreateReport}
            disabled={loading || !sourceModels.length}
          >
            Create Report
          </button>
        </div>
      </div>

      <div className="sidebar__section">
        <div className="section-title">Working Set</div>
        <div className="list">
          {canvasReports.map((report) => (
            <button
              key={report.id}
              className={`report-card ${selectedReportId === report.id ? 'report-card--active' : ''}`}
              onClick={() => onSelectReport(report.id)}
              type="button"
            >
              <div className="report-card__title">{report.name}</div>
              <div className="report-card__meta">
                Source: {report.source_semantic_model_name || 'Unknown'} | {report.page_count || 0} pages
              </div>
              <div className="report-card__actions">
                <span>{report.description || 'Canvas report'}</span>
                <span className="report-card__buttons">
                  <span
                    className="mini-button"
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      onCloneReport(report.id);
                    }}
                    onKeyDown={() => {}}
                  >
                    Clone
                  </span>
                  <span
                    className="mini-button mini-button--danger"
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      onDeleteReport(report.id);
                    }}
                    onKeyDown={() => {}}
                  >
                    Delete
                  </span>
                </span>
              </div>
            </button>
          ))}
          {!canvasReports.length ? <div className="empty-state">No canvas reports yet.</div> : null}
        </div>
      </div>
    </aside>
  );
}
