import { request } from './client';

export interface ProfileOut {
  id: string;
  email: string | null;
  display_name: string | null;
  picture_url: string | null;
  persona: string | null;
  persona_label: string | null;
  goal: string | null;
  goal_template: string | null;
  answers: Record<string, any>;
  onboarding_completed: boolean;
}

export interface ProfileUpdate {
  persona?: string | null;
  persona_label?: string | null;
  goal?: string | null;
  goal_template?: string | null;
  answers?: Record<string, any>;
  onboarding_completed?: boolean;
}

export async function getProfile(): Promise<ProfileOut> {
  return request<ProfileOut>('/api/auth/me');
}

export async function updateProfile(updates: ProfileUpdate): Promise<ProfileOut> {
  return request<ProfileOut>('/api/auth/profile', {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}
