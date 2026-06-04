import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './App.css';
import AppShell from './components/Shell/AppShell';
import { PowerBiProvider } from './context/PowerBiContext';
import CanvasEditorPage from './pages/CanvasEditorPage';
import ConnectionsPage from './pages/ConnectionsPage';
import HomePage from './pages/HomePage';
import ProjectsPage from './pages/ProjectHubPage';
import SettingsPage from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <PowerBiProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<HomePage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="projects/:projectId" element={<CanvasEditorPage />} />
              <Route path="connections" element={<ConnectionsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PowerBiProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
