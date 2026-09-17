import React from 'react';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';
import { StatusDot } from '../ui/StatusDot';
import { Button } from '../ui/Button';
import { getLocalSession } from '../../lib/auth/sessionState';

interface WorkspaceLayoutProps {
  currentRoute: string;
  onNavigate: (route: string) => void;
  onOpenNewInvestigation: () => void;
  children: React.ReactNode;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({
  currentRoute,
  onNavigate,
  onOpenNewInvestigation,
  children,
}) => {
  const session = getLocalSession();

  const navItems = [
    { id: '/app', label: 'Overview', icon: '◎' },
    { id: '/app/evaluations', label: 'Evaluations', icon: '📊' },
    { id: '/app/integrations', label: 'Integrations', icon: '⚡' },
    { id: '/app/settings', label: 'System & Policy', icon: '⚙' },
  ];

  return (
    <div className="flex h-screen bg-[#050505] text-[#F5F5F5] overflow-hidden font-sans">
      {/* Persistent Dark Sidebar */}
      <aside className="w-56 bg-[#0B0B0D] border-r border-[#1A1A1F] flex flex-col justify-between shrink-0 font-mono text-xs">
        <div>
          {/* Brand Header */}
          <div
            onClick={() => onNavigate('/')}
            className="p-4 border-b border-[#1A1A1F] flex items-center gap-2.5 cursor-pointer hover:bg-[#111114] transition-colors"
          >
            <SourceIcon app="surge" size={18} />
            <span className="font-bold text-sm tracking-widest text-[#F5F5F5]">SURGE</span>
            <span className="text-[10px] bg-[#17171C] text-[#71717A] px-1 py-0.2 rounded border border-[#24242B] ml-auto">
              v0.2.0
            </span>
          </div>

          {/* Navigation Links */}
          <div className="p-3">
            <div className="text-[10px] uppercase font-bold text-[#71717A] tracking-wider px-2 mb-2">
              Workspace
            </div>
            <nav className="space-y-1">
              {navItems.map((item) => {
                const isActive =
                  item.id === '/app'
                    ? currentRoute === '/app' || currentRoute.startsWith('/app/investigations')
                    : currentRoute === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    className={`w-full flex items-center gap-2 px-2.5 py-1.8 rounded transition-colors text-left cursor-pointer ${
                      isActive
                        ? 'bg-indigo-950/60 text-indigo-300 font-bold border border-indigo-800/60'
                        : 'text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#111114]'
                    }`}
                  >
                    <span className="text-sm">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Connected App Signals */}
          <div className="p-3 pt-2 border-t border-[#1A1A1F]">
            <div className="text-[10px] uppercase font-bold text-[#71717A] tracking-wider px-2 mb-2 flex items-center justify-between">
              <span>Connected Signals</span>
              <span className="text-[9px] text-zinc-500">DEMO</span>
            </div>
            <div className="space-y-1.5 px-2 text-[11px] text-[#A1A1AA]">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <SourceIcon app="sheets" size={12} /> Google Sheets
                </span>
                <StatusDot status="success" size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <SourceIcon app="github" size={12} /> GitHub
                </span>
                <StatusDot status="success" size="sm" />
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <SourceIcon app="slack" size={12} /> Slack
                </span>
                <StatusDot status="success" size="sm" />
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Footer with Honest Local Session Disclosure */}
        <div className="p-3 border-t border-[#1A1A1F] bg-[#0E0E11]">
          <div className="p-2 bg-[#050505] rounded border border-[#1A1A1F] text-[10px] text-[#71717A] leading-tight">
            <div className="text-zinc-400 font-bold uppercase mb-1 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
              Local Session Mode
            </div>
            <span>No backend tenant auth. ID: {session?.sessionId?.substring(0, 12) || 'anonymous'}</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-12 bg-[#0B0B0D] border-b border-[#1A1A1F] px-6 flex items-center justify-between shrink-0 font-mono text-xs">
          <div className="flex items-center gap-3">
            <span className="font-bold text-[#F5F5F5] uppercase">
              {currentRoute === '/app'
                ? 'Investigation Control Room'
                : currentRoute.startsWith('/app/investigations')
                ? 'Investigation Detail'
                : currentRoute === '/app/evaluations'
                ? 'Reliability & Evaluations'
                : currentRoute === '/app/integrations'
                ? 'Connector Integrations'
                : 'System Configuration'}
            </span>
            <Badge variant="demo">SEEDED DEMO WORLD</Badge>
          </div>

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="primary"
              onClick={onOpenNewInvestigation}
              className="text-xs font-mono"
            >
              + New Investigation
            </Button>
          </div>
        </header>

        {/* Page View Container */}
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
};
