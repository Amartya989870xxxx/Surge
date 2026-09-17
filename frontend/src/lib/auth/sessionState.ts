import type { AppType } from '../../types/api';

export interface LocalSession {
  sessionId: string;
  sessionName: string;
  startedAt: string;
  isDemoSession: true; // Explicit flag: not real auth
  onboardingCompleted: boolean;
  selectedApps: AppType[];
  appPermissionsReviewed: Record<AppType, boolean>;
  connectorModePreference: 'DEMO' | 'REAL';
}

const STORAGE_KEY = 'surge_local_session_v1';

export const AUTH_DISCLAIMER =
  'Local Demo Session: Surge backend does not currently have a multi-tenant authentication service. This local session stores workspace preferences in browser storage and passes a session ID to API requests. It does not provide cryptographic authentication, tenant isolation, or server-enforced authorization.';

export function getLocalSession(): LocalSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function startLocalSession(name: string = 'Demo Operator', sessionId?: string): LocalSession {
  const existing = getLocalSession();
  const session: LocalSession = {
    sessionId: sessionId || existing?.sessionId || `session_${Math.random().toString(36).substring(2, 9)}`,
    sessionName: name.trim() || 'Demo Operator',
    startedAt: existing?.startedAt || new Date().toISOString(),
    isDemoSession: true,
    onboardingCompleted: existing?.onboardingCompleted ?? false,
    selectedApps: existing?.selectedApps || ['sheets', 'github', 'slack'],
    appPermissionsReviewed: existing?.appPermissionsReviewed || {
      sheets: false,
      github: false,
      slack: false,
    },
    connectorModePreference: existing?.connectorModePreference || 'DEMO',
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  return session;
}

export function updateLocalSession(updates: Partial<LocalSession>): LocalSession {
  const current = getLocalSession() || startLocalSession();
  const updated: LocalSession = {
    ...current,
    ...updates,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function clearLocalSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}
