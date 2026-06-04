import { create } from 'zustand';

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function toNumber(value, fallback) {
  const nextValue = Number(value);
  return Number.isFinite(nextValue) ? nextValue : fallback;
}

function normalizeVisual(visual, fallback = {}) {
  const merged = {
    ...fallback,
    ...visual,
  };
  return {
    ...merged,
    x: toNumber(merged.x ?? merged.grid_position?.col, 0),
    y: toNumber(merged.y ?? merged.grid_position?.row, 0),
    w: toNumber(merged.w ?? merged.grid_position?.w, 3),
    h: toNumber(merged.h ?? merged.grid_position?.h, 2),
    bindings: merged.bindings || merged.field_bindings || {},
    config: merged.config || merged.format_config || {},
  };
}

function normalizeSettings(report = {}) {
  const canvasSettings = report.canvas_settings || report.canvasSettings || {};
  const reportSettings = report.report_settings || report.reportSettings || {};
  const legacySettings = report.settings || {};

  return {
    canvas_width: toNumber(legacySettings.canvas_width ?? canvasSettings.width, 1280),
    canvas_height: toNumber(legacySettings.canvas_height ?? canvasSettings.height, 720),
    theme_name: legacySettings.theme_name || reportSettings.themeName || 'BIFoundryTheme',
    theme_color: legacySettings.theme_color || reportSettings.themeColor || '#154360',
  };
}

function normalizePages(pages) {
  return (pages || []).map((page) => {
    const visuals = (page.visuals || []).map((visual) => normalizeVisual(visual));
    return {
      ...page,
      visuals,
    };
  });
}

export const useCanvasStore = create((set, get) => ({
  reportId: null,
  reportName: '',
  settings: {},
  pages: [],
  activePageId: null,
  visuals: {},
  selectedVisualId: null,
  templates: [],
  fields: [],
  isDirty: false,

  hydrateReport: (report) =>
    set(() => {
      const pages = normalizePages(report.pages || []);
      return {
        reportId: report.id,
        reportName: report.name || '',
        settings: normalizeSettings(report),
        pages,
        activePageId: pages[0]?.id || null,
        visuals: Object.fromEntries(pages.map((page) => [page.id, clone(page.visuals || []).map((visual) => normalizeVisual(visual))])),
        selectedVisualId: pages[0]?.visuals?.[0]?.id || null,
        isDirty: false,
      };
    }),

  setTemplates: (templates) => set({ templates: templates || [] }),
  setFields: (fields) => set({ fields: fields || [] }),

  setReportName: (reportName) => set({ reportName, isDirty: true }),
  setSettings: (settings) => set((state) => ({ settings: { ...(state.settings || {}), ...(settings || {}) }, isDirty: true })),

  setActivePageId: (activePageId) => set({ activePageId, selectedVisualId: null }),
  setSelectedVisualId: (selectedVisualId) => set({ selectedVisualId }),

  addPage: (page) =>
    set((state) => {
      const normalizedPage = {
        ...page,
        visuals: (page.visuals || []).map((visual) => normalizeVisual(visual)),
      };
      const pages = [...state.pages, normalizedPage];
      return {
        pages,
        visuals: { ...state.visuals, [page.id]: clone(normalizedPage.visuals || []) },
        activePageId: page.id,
        selectedVisualId: normalizedPage.visuals?.[0]?.id || null,
        isDirty: true,
      };
    }),

  updatePageLocal: (pageId, patch) =>
    set((state) => ({
      pages: state.pages.map((page) => (page.id === pageId ? { ...page, ...patch } : page)),
      isDirty: true,
    })),

  reorderPagesLocal: (pages) =>
    set(() => ({
      pages,
      isDirty: true,
    })),

  removePageLocal: (pageId) =>
    set((state) => {
      const pages = state.pages.filter((page) => page.id !== pageId);
      const visuals = { ...state.visuals };
      delete visuals[pageId];
      return {
        pages,
        visuals,
        activePageId: state.activePageId === pageId ? pages[0]?.id || null : state.activePageId,
        selectedVisualId: state.activePageId === pageId ? null : state.selectedVisualId,
        isDirty: true,
      };
    }),

  addVisualLocal: (pageId, visual) =>
    set((state) => {
      const nextVisual = normalizeVisual(visual);
      const nextPageVisuals = [...(state.visuals[pageId] || []), nextVisual];
      return {
        visuals: { ...state.visuals, [pageId]: nextPageVisuals },
        pages: state.pages.map((page) => (page.id === pageId ? { ...page, visuals: nextPageVisuals } : page)),
        selectedVisualId: nextVisual.id,
        isDirty: true,
      };
    }),

  updateVisualLocal: (pageId, visualId, patch) =>
    set((state) => {
      const nextVisuals = (state.visuals[pageId] || []).map((visual) =>
        visual.id === visualId ? normalizeVisual({ ...visual, ...patch }, visual) : visual,
      );
      return {
        visuals: { ...state.visuals, [pageId]: nextVisuals },
        pages: state.pages.map((page) => (page.id === pageId ? { ...page, visuals: nextVisuals } : page)),
        isDirty: true,
      };
    }),

  removeVisualLocal: (pageId, visualId) =>
    set((state) => {
      const nextVisuals = (state.visuals[pageId] || []).filter((visual) => visual.id !== visualId);
      return {
        visuals: { ...state.visuals, [pageId]: nextVisuals },
        pages: state.pages.map((page) => (page.id === pageId ? { ...page, visuals: nextVisuals } : page)),
        selectedVisualId: state.selectedVisualId === visualId ? null : state.selectedVisualId,
        isDirty: true,
      };
    }),

  clearDirty: () => set({ isDirty: false }),
}));
