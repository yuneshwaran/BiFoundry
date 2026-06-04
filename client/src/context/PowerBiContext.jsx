import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import {
  getPowerBiConfig,
  listPowerBiConnections,
  selectPowerBiConnection,
} from '../services/projectApi';

const PowerBiContext = createContext(null);

export function PowerBiProvider({ children }) {
  const queryClient = useQueryClient();
  const location = useLocation();
  const [notice, setNotice] = useState('');

  const configQuery = useQuery({
    queryKey: ['powerbi-config'],
    queryFn: getPowerBiConfig,
  });

  const connectionsQuery = useQuery({
    queryKey: ['powerbi-connections'],
    queryFn: listPowerBiConnections,
  });

  const selectConnectionMutation = useMutation({
    mutationFn: selectPowerBiConnection,
    onSuccess: async (_selected, connectionId) => {
      queryClient.setQueryData(['powerbi-connections'], (current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          active_connection_id: connectionId,
          connections: (current.connections || []).map((connection) => ({
            ...connection,
            is_active: connection.id === connectionId,
          })),
        };
      });
      await queryClient.invalidateQueries({ queryKey: ['powerbi-connections'] });
    },
  });

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const connectionId = searchParams.get('powerbi_connection');
    const sessionId = searchParams.get('powerbi_session');
    if (connectionId || sessionId) {
      setNotice(`Power BI connection ${connectionId || sessionId} is ready.`);
      window.history.replaceState({}, '', location.pathname);
      queryClient.invalidateQueries({ queryKey: ['powerbi-connections'] });
    }
  }, [location.pathname, location.search, queryClient]);

  const value = useMemo(() => {
    const connections = connectionsQuery.data?.connections || [];
    const activeConnectionId = connectionsQuery.data?.active_connection_id || connections.find((connection) => connection.is_active)?.id || connections[0]?.id || null;
    const activeConnection = connections.find((connection) => connection.id === activeConnectionId) || null;
    return {
      config: configQuery.data || {},
      connections,
      activeConnectionId,
      activeConnection,
      isLoading: connectionsQuery.isLoading || configQuery.isLoading,
      isFetching: connectionsQuery.isFetching || configQuery.isFetching,
      notice,
      setNotice,
      clearNotice: () => setNotice(''),
      selectConnection: (connectionId) => selectConnectionMutation.mutate(connectionId),
      selectConnectionPending: selectConnectionMutation.isPending,
      refreshConnections: () => queryClient.invalidateQueries({ queryKey: ['powerbi-connections'] }),
    };
  }, [
    configQuery.data,
    configQuery.isLoading,
    configQuery.isFetching,
    connectionsQuery.data,
    connectionsQuery.isLoading,
    connectionsQuery.isFetching,
    notice,
    queryClient,
    selectConnectionMutation.isPending,
  ]);

  return <PowerBiContext.Provider value={value}>{children}</PowerBiContext.Provider>;
}

export function usePowerBi() {
  const context = useContext(PowerBiContext);
  if (!context) {
    throw new Error('usePowerBi must be used within a PowerBiProvider.');
  }
  return context;
}
