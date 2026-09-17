import { request } from './client';
import type { ConnectorsOut } from '../../types/api';

export async function listConnectors(): Promise<ConnectorsOut> {
  return request<ConnectorsOut>('/api/connectors');
}

export async function startOAuth(app: string): Promise<{
  auth_url?: string;
  url?: string;
  state?: string;
  [key: string]: any;
}> {
  return request(`/api/connectors/${app}/start`, {
    method: 'POST',
  });
}

export async function disconnectConnector(app: string): Promise<{ app: string; disconnected: boolean }> {
  return request(`/api/connectors/${app}/disconnect`, {
    method: 'POST',
  });
}
