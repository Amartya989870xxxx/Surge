import React from 'react';
import type { AppType } from '../../types/api';
import { Button } from '../ui/Button';
import { SourceIcon } from '../ui/SourceIcon';
import { Badge } from '../ui/Badge';

interface Step03PermissionsProps {
  selectedApps: AppType[];
  onNext: () => void;
  onBack: () => void;
}

export const Step03Permissions: React.FC<Step03PermissionsProps> = ({
  selectedApps,
  onNext,
  onBack,
}) => {
  return (
    <div className="max-w-2xl mx-auto py-8 font-mono">
      <div className="mb-6">
        <span className="text-xs text-[#818CF8] uppercase tracking-wider">Step 3 of 5</span>
        <h2 className="text-2xl font-bold text-[#F5F5F5] mt-1 mb-2">
          Review what Surge can access.
        </h2>
        <p className="text-xs text-[#A1A1AA] leading-relaxed">
          The permissions below reflect the actual backend connector configuration and OAuth contracts.
          Surge strictly distinguishes between read access and human-gated write operations.
        </p>
      </div>

      <div className="space-y-4 mb-8">
        {/* Google Sheets Card */}
        {selectedApps.includes('sheets') && (
          <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#1A1A1F]">
              <div className="flex items-center gap-2">
                <SourceIcon app="sheets" size={18} />
                <span className="text-sm font-bold text-[#F5F5F5]">Google Sheets</span>
              </div>
              <Badge variant="verified">READ-ONLY ACCESS</Badge>
            </div>

            <div className="text-[11px] text-[#71717A] mb-3">
              Backend OAuth Scope:{' '}
              <code className="text-[#818CF8] bg-[#111114] px-1 py-0.5 rounded">
                https://www.googleapis.com/auth/spreadsheets.readonly
              </code>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-emerald-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✓ What Surge Reads
                </div>
                <ul className="space-y-1 text-[#A1A1AA] text-[11px]">
                  <li>• Read spreadsheet metadata</li>
                  <li>• Read metric rows & time-series</li>
                  <li>• Compare checkout funnel stats</li>
                </ul>
              </div>

              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-zinc-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✕ What Surge Does Not Touch
                </div>
                <ul className="space-y-1 text-[#71717A] text-[11px]">
                  <li>• No write access granted</li>
                  <li>• Cannot delete or edit files</li>
                  <li>• Cannot access Gmail or Drive files</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* GitHub Card */}
        {selectedApps.includes('github') && (
          <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#1A1A1F]">
              <div className="flex items-center gap-2">
                <SourceIcon app="github" size={18} />
                <span className="text-sm font-bold text-[#F5F5F5]">GitHub</span>
              </div>
              <Badge variant="warning">READ + APPROVED WRITE</Badge>
            </div>

            <div className="text-[11px] text-[#71717A] mb-2">
              Backend OAuth Scope:{' '}
              <code className="text-[#818CF8] bg-[#111114] px-1 py-0.5 rounded">repo</code>
            </div>

            {/* Scope Honesty Transparency Box */}
            <div className="p-2 bg-amber-950/20 border border-amber-800/40 rounded text-[11px] text-amber-300/90 mb-3 leading-relaxed">
              <strong>Scope Disclosure:</strong> GitHub OAuth v2 scope <code className="bg-amber-950/50 px-1 py-0.2 rounded">repo</code> grants repository access. Surge requires write capability specifically to file approved incident issues, but will never push commits, alter code branches, or delete repositories.
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-emerald-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✓ What Surge Reads & Writes
                </div>
                <ul className="space-y-1 text-[#A1A1AA] text-[11px]">
                  <li>• Inspect recent deployment tags</li>
                  <li>• Read commit diffs & summaries</li>
                  <li>• Read existing open issues</li>
                  <li>• <strong className="text-amber-300">Write:</strong> Create issue (requires approval)</li>
                </ul>
              </div>

              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-zinc-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✕ What Surge Does Not Touch
                </div>
                <ul className="space-y-1 text-[#71717A] text-[11px]">
                  <li>• Cannot push code to branches</li>
                  <li>• Cannot merge pull requests</li>
                  <li>• Cannot delete repositories or org data</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Slack Card */}
        {selectedApps.includes('slack') && (
          <div className="p-4 bg-[#0B0B0D] border border-[#1A1A1F] rounded-lg">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#1A1A1F]">
              <div className="flex items-center gap-2">
                <SourceIcon app="slack" size={18} />
                <span className="text-sm font-bold text-[#F5F5F5]">Slack</span>
              </div>
              <Badge variant="verified">SEARCH & REPORT CONTEXT</Badge>
            </div>

            <div className="text-[11px] text-[#71717A] mb-3">
              Backend OAuth Scopes:{' '}
              <code className="text-[#818CF8] bg-[#111114] px-1 py-0.5 rounded">
                channels:history, channels:read, chat:write, search:read
              </code>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-emerald-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✓ What Surge Reads
                </div>
                <ul className="space-y-1 text-[#A1A1AA] text-[11px]">
                  <li>• Search public channel incident reports</li>
                  <li>• Read support channel feedback</li>
                  <li>• Corroborate onset timestamps</li>
                </ul>
              </div>

              <div className="p-2.5 bg-[#111114] rounded border border-[#1A1A1F]">
                <div className="text-zinc-400 font-bold mb-1.5 uppercase text-[10px]">
                  ✕ What Surge Does Not Touch
                </div>
                <ul className="space-y-1 text-[#71717A] text-[11px]">
                  <li>• Cannot read private direct messages (DMs)</li>
                  <li>• Cannot modify workspace members</li>
                  <li>• Cannot alter channel settings</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-[#1A1A1F]">
        <Button size="md" variant="ghost" onClick={onBack} className="text-xs">
          ← Back to App Selection
        </Button>

        <Button size="md" variant="primary" onClick={onNext} className="text-xs">
          Connect Selected Apps →
        </Button>
      </div>
    </div>
  );
};
