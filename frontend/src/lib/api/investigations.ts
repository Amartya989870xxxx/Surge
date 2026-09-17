import { request } from './client';
import type {
  ActionOut,
  ApproveRequest,
  ClaimOut,
  CreateInvestigationRequest,
  EventOut,
  EvidenceOut,
  HypothesisOut,
  InvestigationCreated,
  InvestigationDetailOut,
  InvestigationListOut,
} from '../../types/api';

export async function createInvestigation(
  data: CreateInvestigationRequest
): Promise<InvestigationCreated> {
  return request<InvestigationCreated>('/api/investigations', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listInvestigations(params?: {
  status?: string;
  include_evaluation?: boolean;
  limit?: number;
}): Promise<InvestigationListOut> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.include_evaluation) query.set('include_evaluation', 'true');
  if (params?.limit) query.set('limit', String(params.limit));

  const qs = query.toString();
  return request<InvestigationListOut>(`/api/investigations${qs ? `?${qs}` : ''}`);
}

export async function getInvestigation(id: string): Promise<InvestigationDetailOut> {
  return request<InvestigationDetailOut>(`/api/investigations/${id}`);
}

export async function getInvestigationEvents(id: string, after: number = 0): Promise<EventOut[]> {
  return request<EventOut[]>(`/api/investigations/${id}/events?after=${after}`);
}

export async function getInvestigationEvidence(id: string): Promise<EvidenceOut[]> {
  return request<EvidenceOut[]>(`/api/investigations/${id}/evidence`);
}

export async function getInvestigationHypotheses(id: string): Promise<HypothesisOut[]> {
  return request<HypothesisOut[]>(`/api/investigations/${id}/hypotheses`);
}

export async function getInvestigationActions(id: string): Promise<ActionOut[]> {
  return request<ActionOut[]>(`/api/investigations/${id}/actions`);
}

export async function getInvestigationClaims(id: string): Promise<ClaimOut[]> {
  return request<ClaimOut[]>(`/api/investigations/${id}/claims`);
}

export async function approveAction(
  investigationId: string,
  data: ApproveRequest
): Promise<ActionOut> {
  return request<ActionOut>(`/api/investigations/${investigationId}/approve`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function cancelInvestigation(id: string): Promise<{ id: string; status: string }> {
  return request<{ id: string; status: string }>(`/api/investigations/${id}/cancel`, {
    method: 'POST',
  });
}

export async function rerunInvestigation(
  id: string,
  clearFaults: boolean = true
): Promise<InvestigationCreated> {
  return request<InvestigationCreated>(`/api/investigations/${id}/rerun`, {
    method: 'POST',
    body: JSON.stringify({ clear_faults: clearFaults }),
  });
}
