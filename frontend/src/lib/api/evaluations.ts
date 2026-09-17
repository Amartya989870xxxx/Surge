import { request } from './client';
import type {
  EvaluationSuiteOut,
  EvaluationSuiteSummaryOut,
} from '../../types/api';

export async function listEvaluations(): Promise<EvaluationSuiteSummaryOut[]> {
  return request<EvaluationSuiteSummaryOut[]>('/api/evaluations');
}

export async function getLatestEvaluation(): Promise<EvaluationSuiteOut> {
  return request<EvaluationSuiteOut>('/api/evaluations/latest');
}

export async function getEvaluation(id: string): Promise<EvaluationSuiteOut> {
  return request<EvaluationSuiteOut>(`/api/evaluations/${id}`);
}

export async function listScenarios(): Promise<any[]> {
  return request<any[]>('/api/evaluations/scenarios');
}

export async function runEvaluationSuite(options?: {
  reasoning?: string;
  scenario_ids?: string[];
}): Promise<{ id: string; status: string; report_url: string }> {
  return request('/api/evaluations/run', {
    method: 'POST',
    body: JSON.stringify(options || {}),
  });
}
