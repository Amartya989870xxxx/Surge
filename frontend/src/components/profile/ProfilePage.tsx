import React, { useState, useEffect } from 'react';
import { getProfile, updateProfile, type ProfileOut } from '../../lib/api/auth';
import { listConnectors } from '../../lib/api/connectors';
import type { ConnectorInfo } from '../../types/api';
import { getLocalSession } from '../../lib/auth/sessionState';
import { signOutUser } from '../../lib/auth/firebase';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { WorkspaceFaviconButton } from '../ui/WorkspaceFaviconButton';
import {
  User,
  Mail,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  LogOut,
  Save,
  KeyRound,
  FileSpreadsheet,
  GitBranch,
  MessageSquare,
} from 'lucide-react';

interface ProfilePageProps {
  onBack: () => void;
  onSignOut: () => void;
  onManageConnectors?: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  onBack,
  onSignOut,
  onManageConnectors,
}) => {
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);

  useEffect(() => {
    listConnectors()
      .then((res) => setConnectors(res.connectors))
      .catch(() => setConnectors([]));
  }, []);

  const connectorFor = (app: string) => connectors.find((c) => c.app === app);
  const isLiveConnector = (app: string) => {
    const c = connectorFor(app);
    return c?.status === 'connected' || c?.status === 'demo';
  };

  // Editable fields
  const [displayName, setDisplayName] = useState('Amartya Majumder');
  const [email, setEmail] = useState('amartya.dev2006@gmail.com');
  const [persona, setPersona] = useState('engineer');
  const [personaLabel, setPersonaLabel] = useState('Lead Incident Engineer');
  const [goal, setGoal] = useState(
    'Correlate multi-source telemetry, isolate root causes with 100% evidence grounding, and execute verified actions.'
  );

  useEffect(() => {
    getProfile()
      .then((p) => {
        if (p) {
          setProfile(p);
          if (p.display_name) setDisplayName(p.display_name);
          if (p.email) setEmail(p.email);
          if (p.persona) setPersona(p.persona);
          if (p.persona_label) setPersonaLabel(p.persona_label);
          if (p.goal) setGoal(p.goal);
        }
      })
      .catch(() => {
        // Fallback to local session if available
        const session = getLocalSession();
        if (session && session.sessionName) {
          setDisplayName(session.sessionName);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateProfile({
        persona,
        persona_label: personaLabel,
        goal,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update profile:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = async () => {
    try {
      await signOutUser();
    } finally {
      onSignOut();
    }
  };

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-sans flex flex-col antialiased selection:bg-indigo-500/30 selection:text-white">
      {/* Top Left Workspace Favicon Link */}
      <WorkspaceFaviconButton onNavigateWorkspace={onBack} />

      {/* Top Right Floating Controls */}
      <div className="fixed top-4 right-6 z-30 flex items-center gap-3">
        <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1.5 rounded-full text-xs flex items-center gap-1.5 shadow-lg backdrop-blur-xl bg-black/60">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Active Session
        </Badge>
        <Button
          type="button"
          variant="ghost"
          onClick={handleLogout}
          className="text-neutral-400 hover:text-red-400 hover:bg-red-500/10 rounded-full px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors border border-white/10 shadow-lg backdrop-blur-xl bg-black/60 cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </Button>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-6 py-10 pt-16 relative">
        {/* Subtle Ambient Cosmic Background Glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-gradient-to-b from-indigo-600/15 via-blue-500/5 to-transparent blur-3xl opacity-50"
        />

        {loading ? (
          <div className="flex items-center justify-center h-64 text-neutral-400 text-xs">
            <div className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mr-3" />
            Loading operator profile...
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-8 relative z-10">
            {/* Header Section */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl">
            {profile?.picture_url ? (
              <img
                src={profile.picture_url}
                alt={displayName}
                className="w-20 h-20 rounded-full border-2 border-indigo-500/60 shadow-xl object-cover"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 text-white flex items-center justify-center text-2xl font-bold border-2 border-white/20 shadow-xl">
                {displayName.charAt(0).toUpperCase()}
              </div>
            )}

            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-bold text-white tracking-tight">{displayName}</h1>
                <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium">
                  {personaLabel || 'Engineer Mode'}
                </span>
              </div>
              <p className="text-sm text-neutral-400 flex items-center gap-2">
                <Mail className="w-3.5 h-3.5 text-neutral-500" />
                {email}
              </p>
              <p className="text-xs text-neutral-500 pt-1">
                Member since September 2026 · Surge Evidence-First Workspace
              </p>
            </div>
          </div>

          {/* Profile Form */}
          <form onSubmit={handleSave} className="space-y-6">
            <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl space-y-5">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <User className="w-4 h-4 text-indigo-400" />
                Operator Preferences
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-400">Display Name</label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-black/50 text-sm text-white focus:outline-none focus:border-indigo-500/70"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-400">Account Email</label>
                  <input
                    type="email"
                    value={email}
                    disabled
                    className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-black/30 text-sm text-neutral-400 cursor-not-allowed"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-400">Investigation Role</label>
                  <select
                    value={persona}
                    onChange={(e) => {
                      setPersona(e.target.value);
                      if (e.target.value === 'engineer') setPersonaLabel('Lead Incident Engineer');
                      else if (e.target.value === 'sre') setPersonaLabel('Site Reliability Engineer');
                      else if (e.target.value === 'manager') setPersonaLabel('Incident Commander');
                    }}
                    className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-black/50 text-sm text-white focus:outline-none focus:border-indigo-500/70 cursor-pointer"
                  >
                    <option value="engineer">Lead Incident Engineer</option>
                    <option value="sre">Site Reliability Engineer (SRE)</option>
                    <option value="manager">Incident Commander</option>
                    <option value="other">Custom Operator Mode</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-400">Persona Badge Label</label>
                  <input
                    type="text"
                    value={personaLabel}
                    onChange={(e) => setPersonaLabel(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-black/50 text-sm text-white focus:outline-none focus:border-indigo-500/70"
                  />
                </div>
              </div>

              <div className="space-y-1.5 pt-1">
                <label className="text-xs font-medium text-neutral-400">Operational Mission & Goal</label>
                <textarea
                  rows={3}
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-white/10 bg-black/50 text-sm text-white focus:outline-none focus:border-indigo-500/70 leading-relaxed resize-none"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                {savedSuccess ? (
                  <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Preferences updated successfully
                  </span>
                ) : (
                  <span className="text-xs text-neutral-500">
                    Changes apply immediately to your active workspace session.
                  </span>
                )}

                <Button
                  type="submit"
                  disabled={saving}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-4 py-2 rounded-xl flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/30"
                >
                  <Save className="w-3.5 h-3.5" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </div>
          </form>

          {/* Connected Signals Overview */}
          <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Connected Signal Integrations
              </h2>
              {onManageConnectors && (
                <button
                  type="button"
                  onClick={onManageConnectors}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer transition-colors"
                >
                  Manage Connectors <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {([
                { app: 'sheets', title: 'Google Sheets', icon: <FileSpreadsheet className="w-4 h-4" />, iconWrap: 'bg-emerald-950/60 border-emerald-800/40 text-emerald-400', defaultDesc: 'Read-only conversion funnel telemetry' },
                { app: 'github', title: 'GitHub', icon: <GitBranch className="w-4 h-4" />, iconWrap: 'bg-neutral-900 border-neutral-700 text-white', defaultDesc: 'Commits & deployments' },
                { app: 'slack', title: 'Slack', icon: <MessageSquare className="w-4 h-4" />, iconWrap: 'bg-amber-950/50 border-amber-800/40 text-amber-400', defaultDesc: 'Channel history & chatter' },
              ] as const).map(({ app, title, icon, iconWrap, defaultDesc }) => {
                const conn = connectorFor(app);
                const live = isLiveConnector(app);
                return (
                  <div key={app} className="p-3.5 rounded-xl border border-white/10 bg-black/40 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg border ${iconWrap}`}>{icon}</div>
                      <div>
                        <div className="text-xs font-semibold text-white">{title}</div>
                        <div className="text-[11px] text-neutral-400">
                          {live && conn?.account_label ? conn.account_label : defaultDesc}
                        </div>
                      </div>
                    </div>
                    <Badge
                      className={
                        live
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]'
                          : 'bg-neutral-800/60 text-neutral-400 border border-neutral-700 text-[10px]'
                      }
                    >
                      {live ? 'Connected' : 'Not connected'}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Security & System Policy */}
          <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl space-y-4">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-purple-400" />
              Security & Verification Policies
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-xl border border-white/10 bg-black/40">
                <span className="text-neutral-500 block mb-1">Evidence Threshold</span>
                <span className="text-white font-mono font-bold">70% Support</span>
              </div>
              <div className="p-3 rounded-xl border border-white/10 bg-black/40">
                <span className="text-neutral-500 block mb-1">Human-in-the-Loop</span>
                <span className="text-emerald-400 font-mono font-bold">Always Enforced</span>
              </div>
              <div className="p-3 rounded-xl border border-white/10 bg-black/40">
                <span className="text-neutral-500 block mb-1">Action Verification</span>
                <span className="text-cyan-400 font-mono font-bold">Independent Read-Back</span>
              </div>
            </div>
          </div>
        </div>
      )}
      </main>
    </div>
  );
};
