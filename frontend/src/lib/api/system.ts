import { request } from './client';
import type { SystemInfo } from '../../types/api';

export async function getHealth(): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>('/api/health');
}

export async function getSystem(): Promise<SystemInfo> {
  return request<SystemInfo>('/api/system');
}
