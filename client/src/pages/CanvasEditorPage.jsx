import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import CanvasGrid from '../components/Canvas/CanvasGrid';
import FieldBrowser from '../components/Canvas/FieldBrowser';
import PageTabs from '../components/Canvas/PageTabs';
import PropertiesPanel from '../components/Canvas/PropertiesPanel';
import VisualPalette from '../components/Canvas/VisualPalette';
import { getTemplateSlots } from '../components/Canvas/templateSlots';
import {
  compileProject,
  createProjectPage,
  createProjectVisual,
  deleteProjectPage,
  deleteProjectVisual,
  downloadBlob,
  getProject,
  getProjectFields,
  listProjectVisualTemplates,
  updateProject,
  updateProjectPage,
  updateProjectVisual,
  validateProject,
} from '../services/projectApi';
import { useCanvasStore } from '../stores/canvasStore';

function normalizeField(field) {
  if (typeof field === 'string') {
    const [table = 'Unknown', name = ''] = field.split('.');
    return {
      table,
      name,
      kind: 'column',
      data_type: null,
      label: field,
    };
  }
  const name = field.name || field.field || field.column || '';
  const kind = field.kind || field.field_type || field.type || 'column';
  return {
    table: field.table || field.table_name || 'Unknown',
    name,
    kind,
    data_type: field.data_type || field.dataType || null,
    label: field.label || `${field.table || field.table_name || 'Unknown'}.${name}`,
  };
}

function normalizeBindingField(field) {
  const normalized = normalizeField(field);
  return {
    table: normalized.table,
    name: normalized.name,
    kind: normalized.kind,
    data_type: normalized.data_type,
    label: normalized.label,
  };
}

function buildTemplateMap(templates) {
  const map = new Map();
  (templates || []).forEach((template) => {
    const keys = [template.id, String(template.id), template.template_key, template.visual_type]
      .filter(Boolean)
      .flatMap((key) => [key, String(key).toLowerCase(), String(key).toUpperCase()]);
    keys.forEach((key) => map.set(key, template));
  });
  return map;
}

function resolveTemplateFromMap(templateMap, templateKey) {
  if (templateKey === null || templateKey === undefined) {
    return null;
  }
  return (
    templateMap.get(templateKey) ||
    templateMap.get(String(templateKey)) ||
    templateMap.get(String(templateKey).toLowerCase()) ||
    templateMap.get(String(templateKey).toUpperCase()) ||
    null
  );
}

function slotSupportsField(slot, field) {
  const slotType = slot.field_type || 'any';
  if (slotType === 'any') {
    return true;
  }
  if (slotType === 'measure') {
    return field.kind === 'measure';
  }
  if (slotType === 'column') {
    return field.kind !== 'measure';
  }
  return true;
}

function orderedSlots(template) {
  const slots = getTemplateSlots(template);
  return [...slots.filter((slot) => slot.required), ...slots.filter((slot) => !slot.required)];
}

export default function CanvasEditorPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const numericProjectId = Number(projectId);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [compiling, setCompiling] = useState(false);
  const hasHydratedRef = useRef(false);

  const {
    reportName,
    settings,
    pages,
    activePageId,
    selectedVisualId,
    templates,
    fields,
    hydrateReport,
    setTemplates,
    setFields,
    setActivePageId,
    setSelectedVisualId,
    setReportName,
    updatePageLocal,
    reorderPagesLocal,
    removePageLocal,
    addPage,
    addVisualLocal,
    updateVisualLocal,
    removeVisualLocal,
  } = useCanvasStore();

  const projectQuery = useQuery({
    queryKey: ['project', numericProjectId],
    queryFn: () => getProject(numericProjectId),
    enabled: Number.isFinite(numericProjectId),
  });

  useEffect(() => {
    hasHydratedRef.current = false;
  }, [numericProjectId]);

  const templatesQuery = useQuery({
    queryKey: ['project-visual-templates'],
    queryFn: listProjectVisualTemplates,
  });

  const fieldsQuery = useQuery({
    queryKey: ['project-fields', numericProjectId],
    queryFn: () => getProjectFields(numericProjectId),
    enabled: Number.isFinite(numericProjectId),
  });

  useEffect(() => {
    if (!projectQuery.data || hasHydratedRef.current) {
      return;
    }

    hydrateReport(projectQuery.data);
    hasHydratedRef.current = true;
  }, [hydrateReport, projectQuery.data]);

  useEffect(() => {
    if (templatesQuery.data) {
      setTemplates(templatesQuery.data);
    }
  }, [setTemplates, templatesQuery.data]);

  useEffect(() => {
    if (fieldsQuery.data) {
      const nextFields = fieldsQuery.data.fields || [];
      if (nextFields.length) {
        setFields(nextFields);
      }
    }
  }, [fieldsQuery.data, setFields]);

  const templateMap = useMemo(() => buildTemplateMap(templates), [templates]);

  const activePage = useMemo(
    () => pages.find((page) => page.id === activePageId) || pages[0] || null,
    [activePageId, pages],
  );

  const selectedVisual = useMemo(() => {
    if (!activePage || !selectedVisualId) {
      return null;
    }
    return (activePage.visuals || []).find((visual) => visual.id === selectedVisualId) || null;
  }, [activePage, selectedVisualId]);

  const selectedTemplate = useMemo(() => {
    if (!selectedVisual) {
      return null;
    }
    return (
      resolveTemplateFromMap(templateMap, selectedVisual.visual_template_id) ||
      resolveTemplateFromMap(templateMap, selectedVisual.template_key) ||
      null
    );
  }, [selectedVisual, templateMap]);

  const createPageMutation = useMutation({
    mutationFn: (payload) => createProjectPage(numericProjectId, payload),
    onSuccess: async (created) => {
      const createdPages = created?.pages || [];
      const newestPage =
        createdPages.find((page) => page.id && String(page.page_order) === String(createdPages.length - 1)) ||
        createdPages[createdPages.length - 1] ||
        null;

      if (!hasHydratedRef.current && createdPages.length) {
        hydrateReport(created);
        hasHydratedRef.current = true;
        if (newestPage?.id) {
          setActivePageId(newestPage.id);
        }
      } else if (created?.id) {
        addPage({
          ...created,
          visuals: created.visuals || [],
        });
      }
      setNotice(`Created ${created.display_name || created.name || 'page'}.`);
    },
    onError: (requestError) => setError(requestError.message || 'Failed to create page.'),
  });

  const createVisualMutation = useMutation({
    mutationFn: ({ pageId, templateRef, x, y }) => {
      const template = templateMap.get(templateRef) || templateMap.get(String(templateRef));
      const width = Number.isFinite(Number(template?.default_width)) ? template.default_width : 3;
      const height = Number.isFinite(Number(template?.default_height)) ? template.default_height : 2;
      return createProjectVisual(numericProjectId, pageId, {
        template_key: template?.template_key || String(templateRef),
        name: `${template?.name || template?.visual_type || 'Visual'} ${uuidv4().slice(0, 4)}`,
        x,
        y,
        w: width,
        h: height,
        bindings: {},
        config: {},
        raw: {},
      });
    },
    onSuccess: async (created, variables) => {
      if (!hasHydratedRef.current && created?.pages?.length) {
        hydrateReport(created);
        hasHydratedRef.current = true;
        setActivePageId(variables.pageId);
      } else {
        const template = templateMap.get(variables.templateRef) || templateMap.get(String(variables.templateRef));
        addVisualLocal(variables.pageId, {
          ...created,
          template_key: created.template_key || template?.template_key || String(variables.templateRef),
          name: created.visual_name || created.name,
          visual_name: created.visual_name || created.name,
          x: Number(created.x ?? created.grid_position?.col ?? 0),
          y: Number(created.y ?? created.grid_position?.row ?? 0),
          w: Number(created.w ?? created.grid_position?.w ?? template?.default_width ?? 3),
          h: Number(created.h ?? created.grid_position?.h ?? template?.default_height ?? 2),
          bindings: created.bindings || created.field_bindings || {},
          config: created.config || created.format_config || {},
        });
      }
    },
    onError: (requestError) => setError(requestError.message || 'Failed to add visual.'),
  });

  const deletePageMutation = useMutation({
    mutationFn: (pageId) => deleteProjectPage(numericProjectId, pageId),
    onSuccess: async (_result, pageId) => {
      if (!hasHydratedRef.current && _result?.pages?.length) {
        hydrateReport(_result);
        hasHydratedRef.current = true;
      } else {
        removePageLocal(pageId);
      }
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete page.'),
  });

  const deleteVisualMutation = useMutation({
    mutationFn: ({ pageId, visualId }) => deleteProjectVisual(numericProjectId, pageId, visualId),
    onSuccess: async (_result, variables) => {
      if (!hasHydratedRef.current && _result?.pages?.length) {
        hydrateReport(_result);
        hasHydratedRef.current = true;
        setActivePageId(variables.pageId);
      } else {
        removeVisualLocal(variables.pageId, variables.visualId);
      }
    },
    onError: (requestError) => setError(requestError.message || 'Failed to delete visual.'),
  });

  const validateMutation = useMutation({
    mutationFn: () => validateProject(numericProjectId),
  });

  const handleAddBlankPage = () => {
    const pageName = `page_${pages.length + 1}`;
    createPageMutation.mutate({
      name: pageName,
      page_name: pageName,
      display_name: `Page ${pages.length + 1}`,
      page_order: pages.length,
      width: Number(settings.canvas_width) || 1280,
      height: Number(settings.canvas_height) || 720,
      visuals: [],
      raw: {},
    });
  };

  const handleRenamePage = (pageId, nextDisplayName) => {
    updatePageLocal(pageId, { display_name: nextDisplayName });
  };

  const handleMovePage = (pageId, direction) => {
    const nextPages = [...pages];
    const index = nextPages.findIndex((page) => page.id === pageId);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= nextPages.length) {
      return;
    }
    const [page] = nextPages.splice(index, 1);
    nextPages.splice(targetIndex, 0, page);
    reorderPagesLocal(nextPages.map((item, nextIndex) => ({ ...item, page_order: nextIndex })));
  };

  const handleDeletePage = (pageId) => {
    if (!window.confirm('Delete this page?')) {
      return;
    }
    deletePageMutation.mutate(pageId);
  };

  const handleLayoutChange = (layout) => {
    if (!activePage) {
      return;
    }
    layout.forEach((item) => {
      const visualId = Number(item.i);
      updateVisualLocal(activePage.id, visualId, {
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
      });
    });
  };

  const handleDropTemplate = (templateRef, x, y) => {
    if (!activePage) {
      return;
    }
    createVisualMutation.mutate({ pageId: activePage.id, templateRef, x, y });
  };

  const handleDeleteVisual = (visualId) => {
    if (!activePage || !window.confirm('Delete this visual?')) {
      return;
    }
    deleteVisualMutation.mutate({ pageId: activePage.id, visualId });
  };

  const handleUpdateVisual = (visualId, patch) => {
    if (!activePage) {
      return;
    }
    updateVisualLocal(activePage.id, visualId, patch);
  };

  const handleAssignField = (field) => {
    if (!activePage || !selectedVisual || !selectedTemplate) {
      setNotice('Select a visual before assigning a field.');
      return;
    }

    const normalizedField = normalizeBindingField(field);
    const currentBindings = { ...(selectedVisual.bindings || {}) };
    const candidateSlots = orderedSlots(selectedTemplate).filter((slot) => slotSupportsField(slot, normalizedField));

    if (!candidateSlots.length) {
      setError(`No available slot on ${selectedTemplate.name || selectedTemplate.template_key} can accept ${normalizedField.label}.`);
      return;
    }

    const targetSlot =
      candidateSlots.find((slot) => !currentBindings[slot.role] || (slot.multi && (!Array.isArray(currentBindings[slot.role]) || currentBindings[slot.role].length === 0))) ||
      candidateSlots[0];

    if (targetSlot.multi) {
      const existing = Array.isArray(currentBindings[targetSlot.role])
        ? currentBindings[targetSlot.role]
        : currentBindings[targetSlot.role]
          ? [currentBindings[targetSlot.role]]
          : [];
      const exists = existing.some(
        (binding) =>
          (binding.table || binding.table_name) === normalizedField.table &&
          (binding.name || binding.field || binding.column) === normalizedField.name &&
          (binding.kind || binding.field_type || binding.type || 'column') === normalizedField.kind,
      );
      if (exists) {
        setNotice(`${normalizedField.label} is already assigned.`);
        return;
      }
      currentBindings[targetSlot.role] = [...existing, normalizedField];
    } else {
      currentBindings[targetSlot.role] = normalizedField;
    }

    updateVisualLocal(activePage.id, selectedVisual.id, { bindings: currentBindings });
    setNotice(`${normalizedField.label} assigned to ${targetSlot.name || targetSlot.role}.`);
  };

  const flushToServer = async () => {
    await updateProject(numericProjectId, {
      name: reportName,
      canvas_settings: {
        width: Number(settings.canvas_width) || 1280,
        height: Number(settings.canvas_height) || 720,
      },
      report_settings: {
        themeName: settings.theme_name || 'BIFoundryTheme',
        themeColor: settings.theme_color || '#154360',
      },
    });

    await Promise.all(
      pages.map((page, index) =>
        updateProjectPage(numericProjectId, page.id, {
          name: page.page_name || page.name,
          display_name: page.display_name || page.name,
          width: page.width,
          height: page.height,
          page_order: page.page_order ?? index,
          raw: page.raw || {},
        }),
      ),
    );

    const allVisuals = pages.flatMap((page) =>
      (page.visuals || []).map((visual, index) => ({ pageId: page.id, visual, index })),
    );

    await Promise.all(
      allVisuals.map(({ pageId, visual, index }) =>
        updateProjectVisual(numericProjectId, pageId, visual.id, {
          template_key: visual.template_key,
          name: visual.visual_name || visual.name,
          x: Number(visual.x) || 0,
          y: Number(visual.y) || 0,
          w: Number(visual.w) || 3,
          h: Number(visual.h) || 2,
          bindings: visual.bindings || {},
          config: visual.config || {},
          raw: visual.raw || {},
          visual_order: visual.visual_order ?? index,
        }),
      ),
    );
  };

  const handleCompile = async () => {
    setCompiling(true);
    setError('');
    try {
      await flushToServer();
      const validation = await validateMutation.mutateAsync();
      if (!validation.valid) {
        setError(validation.errors.map((item) => item.message).join(' | '));
        return;
      }
      const blob = await compileProject(numericProjectId);
      downloadBlob(blob, `${reportName || 'project'}.zip`);
      setNotice('Compilation complete.');
    } catch (requestError) {
      setError(requestError.message || 'Failed to compile project.');
    } finally {
      setCompiling(false);
    }
  };

  if (!Number.isFinite(numericProjectId)) {
    return <div className="app-shell">Invalid project id.</div>;
  }

  const fieldCount = fields.length;
  const statusText = projectQuery.isLoading
    ? 'Loading...'
    : compiling
      ? 'Compiling...'
      : reportName || 'Canvas builder';

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__content">
          <div className="eyebrow">BIFoundry</div>
          <h1>Canvas report builder</h1>
          <p>
            Drag a starter visual onto the canvas, or pick a template from the gallery and bind semantic fields from the browser.
            The project stays saved in the PBIP-ready `projects` flow.
          </p>
          <div className="canvas-toolbar">
            <input
              className="input"
              value={reportName}
              onChange={(event) => setReportName(event.target.value)}
              placeholder="Project name"
            />
            <button className="button" type="button" onClick={() => navigate('/projects')}>
              Back
            </button>
            <button className="button" type="button" onClick={handleAddBlankPage}>
              Add blank page
            </button>
            <button className="button" type="button" onClick={handleCompile} disabled={compiling}>
              {compiling ? 'Compiling...' : 'Validate & Compile'}
            </button>
          </div>
        </div>
        <div className="hero__status">
          <div className="status-chip">{statusText}</div>
          <div className="status-chip status-chip--muted">{activePage ? `${activePage.visuals?.length || 0} visuals` : 'No page selected'}</div>
          <div className="status-chip status-chip--muted">{pages.length} pages</div>
          <div className="status-chip status-chip--muted">{fieldCount} fields</div>
        </div>
      </header>

      {error ? <div className="status-banner status-banner--error">{error}</div> : null}
      {notice ? <div className="status-banner status-banner--success">{notice}</div> : null}

      <main className="workspace page-grid page-grid--builder">
        <div className="page-column page-column--left">
          <VisualPalette
            templates={templates}
            onDragStart={(event, template) => {
              event.dataTransfer.setData('templateId', String(template.id));
              event.dataTransfer.setData('application/x-bifoundry-template', template.template_key);
              event.dataTransfer.setData('text/plain', `template:${template.template_key}`);
              event.dataTransfer.effectAllowed = 'copy';
            }}
          />

          <FieldBrowser fields={fields} selectedVisualId={selectedVisualId} onAssignField={handleAssignField} />

        </div>

        <div className="page-column page-column--center">
          <div className="canvas-shell">
            <PageTabs
              pages={pages}
              activePageId={activePageId}
              onAddPage={handleAddBlankPage}
              onSelectPage={setActivePageId}
              onRenamePage={handleRenamePage}
              onMovePage={handleMovePage}
              onDeletePage={handleDeletePage}
            />
            <CanvasGrid
              activePage={activePage}
              templates={templates}
              onLayoutChange={handleLayoutChange}
              onDropTemplate={handleDropTemplate}
              onSelectVisual={setSelectedVisualId}
              onDeleteVisual={handleDeleteVisual}
              selectedVisualId={selectedVisualId}
            />
          </div>
        </div>

        <div className="page-column page-column--right">
          <PropertiesPanel
            report={{
              id: numericProjectId,
              name: reportName,
              settings,
              pages,
            }}
            selectedVisual={selectedVisual}
            templates={templates}
            fields={fields}
            onUpdateReport={() => {}}
            onUpdateVisual={handleUpdateVisual}
            onDeleteVisual={handleDeleteVisual}
            onCompile={handleCompile}
            compiling={compiling}
            mode="builder"
          />
        </div>
      </main>
    </div>
  );
}
