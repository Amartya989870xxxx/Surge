import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { InvestigationSummaryOut } from '../../types/api';
import { listInvestigations, createInvestigation } from '../../lib/api/investigations';
import { getProfile, type ProfileOut } from '../../lib/api/auth';
import { SourceIcon } from '../ui/SourceIcon';
import { StatusDot } from '../ui/StatusDot';
import { Button } from '../ui/Button';
import {
  ArrowUp,
  Paperclip,
  TrendingDown,
  AlertTriangle,
  Layers,
  FileSpreadsheet,
  GitBranch,
  MessageSquare,
  Search,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  FileText,
  FileCode,
  Presentation,
  Image as ImageIcon,
  File,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface DashboardScreenProps {
  onSelectInvestigation: (id: string, isTerminal: boolean) => void;
  onOpenConnectors?: () => void;
  onOpenEvaluations?: () => void;
  onOpenProfile?: () => void;
  onSignOut?: () => void;
}

interface UploadedMediaFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
}

export const DashboardScreen: React.FC<DashboardScreenProps> = ({
  onSelectInvestigation,
  onOpenProfile = () => { window.location.hash = '#/profile'; },
}) => {
  const [prompt, setPrompt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  // File upload state supporting all document & media formats
  const [attachedFiles, setAttachedFiles] = useState<UploadedMediaFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // History sidebar state
  const [historyItems, setHistoryItems] = useState<InvestigationSummaryOut[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  // User Profile
  const [profile, setProfile] = useState<ProfileOut | null>(null);

  // Auto-resize textarea ref
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback((reset?: boolean) => {
    const el = textareaRef.current;
    if (!el) return;
    if (reset) {
      el.style.height = '52px';
      return;
    }
    el.style.height = '52px';
    const newHeight = Math.max(52, Math.min(el.scrollHeight, 180));
    el.style.height = `${newHeight}px`;
  }, []);

  const fetchHistory = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await listInvestigations({ limit: 30 });
      setHistoryItems(res.items || []);
    } catch (err: any) {
      console.error('Failed to load investigation history:', err);
      setHistoryError(err.message || 'Unable to load history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadProfile = async () => {
    try {
      const p = await getProfile();
      setProfile(p);
    } catch {
      // Unauthenticated or demo mode
    }
  };

  useEffect(() => {
    fetchHistory();
    loadProfile();
  }, []);

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  // Get appropriate icon for document/media extension
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    if (['pdf'].includes(ext)) return <FileText className="w-3.5 h-3.5 text-rose-400 shrink-0" />;
    if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
    if (['pptx', 'ppt'].includes(ext)) return <Presentation className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
    if (['png', 'jpg', 'jpeg', 'heic', 'webp'].includes(ext)) return <ImageIcon className="w-3.5 h-3.5 text-cyan-400 shrink-0" />;
    if (['md', 'txt', 'html', 'doc', 'docx'].includes(ext)) return <FileCode className="w-3.5 h-3.5 text-blue-400 shrink-0" />;
    return <File className="w-3.5 h-3.5 text-neutral-400 shrink-0" />;
  };

  const handleFilesSelected = (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const newItems: UploadedMediaFile[] = fileArray.map((f) => ({
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      file: f,
      name: f.name,
      size: f.size,
      type: f.type,
    }));
    setAttachedFiles((prev) => [...prev, ...newItems]);
  };

  const removeFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if ((!prompt.trim() && attachedFiles.length === 0) || submitting) return;

    setSubmitting(true);
    setError(null);

    const fileSummary = attachedFiles.length > 0
      ? `\n\n[Uploaded Artifacts: ${attachedFiles.map((f) => `${f.name} (${formatFileSize(f.size)})`).join(', ')}]`
      : '';
    const fullRequest = (prompt.trim() || 'Analyze the uploaded documents and correlate with incident signals') + fileSummary;

    try {
      const res = await createInvestigation({
        request: fullRequest,
      });
      setAttachedFiles([]);
      // Immediately navigate to Screen 7 (Agent Console)
      onSelectInvestigation(res.id, false);
    } catch (err: any) {
      setError(err.message || 'Failed to start investigation');
      setSubmitting(false);
    }
  };

  const handleLaunchPreset = async (presetText: string, scenarioId?: string) => {
    setPrompt(presetText);
    adjustHeight();
    setSubmitting(true);
    setError(null);
    try {
      const res = await createInvestigation({
        request: presetText,
        scenario_id: scenarioId,
      });
      onSelectInvestigation(res.id, false);
    } catch (err: any) {
      setError(err.message || 'Failed to start investigation');
      setSubmitting(false);
    }
  };

  const primaryScenarios = [
    {
      icon: <TrendingDown className="w-3.5 h-3.5 text-indigo-400" />,
      text: "Conversion dropped after yesterday's release, investigate and coordinate the response.",
      scenario: 'checkout_regression_01',
    },
    {
      icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
      text: "Investigate checkout funnel drop off and error rate spike starting around 14:00 UTC.",
      scenario: 'checkout_regression_01',
    },
    {
      icon: <Layers className="w-3.5 h-3.5 text-cyan-400" />,
      text: "Correlate Google Sheets conversion drop with latest GitHub deployments and Slack chatter.",
      scenario: 'checkout_regression_01',
    },
  ];

  const quickTopicPills = [
    { icon: <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />, label: "Sheets Anomaly", text: "Analyze Google Sheets metric drop across checkout and conversion funnels." },
    { icon: <GitBranch className="w-3.5 h-3.5 text-purple-400" />, label: "GitHub Deployments", text: "Audit recent GitHub deployments and commit diffs for breaking changes." },
    { icon: <MessageSquare className="w-3.5 h-3.5 text-amber-400" />, label: "Slack Incident Discussion", text: "Scan Slack channels for customer reports and engineer incident chatter." },
    { icon: <Search className="w-3.5 h-3.5 text-blue-400" />, label: "Root Cause Diagnosis", text: "Formulate competing hypotheses and isolate root cause across connected telemetry." },
    { icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />, label: "Verify Actions", text: "Verify GitHub issue creation and Slack notifications against provider state." },
  ];

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-sans flex flex-col antialiased selection:bg-indigo-500/30 selection:text-white">
      {/* Floating Top-Right Profile Icon Button */}
      <div className="absolute top-5 right-6 z-30">
        <button
          type="button"
          onClick={onOpenProfile}
          title={profile?.display_name ? `Operator Profile (${profile.display_name})` : "Operator Profile (Amartya Majumder)"}
          className="flex items-center gap-2 p-1 rounded-full border border-white/20 bg-black/60 hover:bg-white/10 hover:border-indigo-400 backdrop-blur-2xl transition-all shadow-2xl hover:scale-105 cursor-pointer group"
        >
          {profile?.picture_url ? (
            <img
              src={profile.picture_url}
              alt={profile.display_name || 'Profile'}
              className="w-10 h-10 rounded-full object-cover border border-white/20 group-hover:border-indigo-400 transition-colors"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 text-white flex items-center justify-center text-sm font-bold border border-white/20 shadow-md">
              {profile?.display_name ? profile.display_name.charAt(0).toUpperCase() : 'A'}
            </div>
          )}
        </button>
      </div>

      {/* Main Layout with Collapsible Sidebar and Full-bleed Celestial Background */}
      <div
        className="flex-1 flex overflow-hidden relative bg-[#000000]"
        style={{
          backgroundImage: "url('/images/ruixen-moon.png'), url('https://cdn.21st.dev/assets/mirror/c3/c333918af688a4a8a3d004652e6c0ee219457a9d84d380eeb31f513d4b59a09f.png')",
          backgroundPosition: "center 70%",
          backgroundSize: "cover",
          backgroundRepeat: "no-repeat",
        }}
      >
        {/* Luminous Curved Celestial Moon Horizon Aura Spanning the entire workspace */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 bottom-10 top-1/4 flex items-center justify-center z-0"
        >
          <div className="w-[1300px] h-[580px] rounded-[100%] bg-gradient-to-t from-indigo-950/40 via-indigo-600/30 to-blue-500/15 blur-3xl opacity-80" />
          <div className="absolute w-[850px] h-[370px] rounded-[100%] bg-gradient-to-t from-purple-900/30 via-indigo-500/20 to-cyan-400/10 blur-2xl opacity-60" />
        </div>

        {/* Left History Sidebar - Transparent Blur Aesthetic matching Chat Area */}
        <aside
          className={cn(
            "border-r border-white/10 bg-black/25 backdrop-blur-2xl flex flex-col shrink-0 z-20 transition-all duration-300 ease-in-out relative",
            sidebarExpanded ? "w-72 sm:w-80" : "w-16"
          )}
        >
          {/* Header */}
          <div
            className={cn(
              "border-b border-white/10 flex items-center transition-all bg-white/[0.01]",
              sidebarExpanded ? "p-4 justify-between" : "p-3 justify-center"
            )}
          >
            {sidebarExpanded ? (
              <>
                <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  Investigation History
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={fetchHistory}
                    title="Refresh history"
                    className="text-neutral-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
                  >
                    <RefreshCw className={cn("w-3.5 h-3.5", historyLoading && "animate-spin text-indigo-400")} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setSidebarExpanded(false)}
                    title="Shrink sidebar"
                    className="text-neutral-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-all cursor-pointer"
                  >
                    <PanelLeftClose className="w-4 h-4 text-neutral-300 hover:text-white" />
                  </button>
                </div>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setSidebarExpanded(true)}
                title="Expand sidebar"
                className="text-neutral-400 hover:text-white p-2 rounded-xl hover:bg-white/10 transition-all cursor-pointer group"
              >
                <PanelLeftOpen className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
              </button>
            )}
          </div>

          {/* Body */}
          {sidebarExpanded ? (
            <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
              {historyLoading ? (
                <div className="p-6 text-center text-neutral-500 text-xs">
                  Loading investigations...
                </div>
              ) : historyError ? (
                <div className="p-4 text-center text-red-400 text-xs bg-red-950/20 border border-red-900/30 rounded-xl backdrop-blur-md">
                  {historyError}
                </div>
              ) : historyItems.length === 0 ? (
                <div className="p-6 text-center text-neutral-500 text-xs leading-relaxed">
                  No past investigations yet.
                  <br />
                  Submit a query to launch your first run.
                </div>
              ) : (
                historyItems.map((item) => {
                  const isCompleted =
                    item.status === 'COMPLETED' ||
                    item.status === 'FAILED' ||
                    item.status === 'CANCELLED' ||
                    item.status === 'PARTIAL';
                  const hasPendingApproval = item.pending_approval;

                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelectInvestigation(item.id, isCompleted)}
                      className="w-full text-left p-3 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.08] hover:border-indigo-500/40 transition-all cursor-pointer group backdrop-blur-md shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <span className="text-xs font-medium text-neutral-200 group-hover:text-white line-clamp-2 leading-snug">
                          {item.title || item.request}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-neutral-400 mt-2.5">
                        <div className="flex items-center gap-1.5">
                          {hasPendingApproval ? (
                            <span className="text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                              <StatusDot status="warning" size="sm" pulse /> Approval
                            </span>
                          ) : isCompleted ? (
                            <span className="text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <StatusDot status="success" size="sm" /> {item.status}
                            </span>
                          ) : (
                            <span className="text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <StatusDot status="info" size="sm" pulse /> {item.status}
                            </span>
                          )}
                          {item.confidence !== null && item.confidence !== undefined && (
                            <span className="text-neutral-400 font-mono text-[10px]">
                              · {Math.round(item.confidence * 100)}%
                            </span>
                          )}
                        </div>

                        <span className="text-neutral-500 text-[10px]">
                          {new Date(item.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto py-3 px-2 space-y-2.5 custom-scrollbar flex flex-col items-center">
              {historyItems.map((item) => {
                const isCompleted =
                  item.status === 'COMPLETED' ||
                  item.status === 'FAILED' ||
                  item.status === 'CANCELLED' ||
                  item.status === 'PARTIAL';
                const statusType = item.pending_approval
                  ? 'warning'
                  : isCompleted
                  ? 'success'
                  : 'info';

                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectInvestigation(item.id, isCompleted)}
                    title={`${item.title || item.request} (${item.status})`}
                    className="w-10 h-10 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.08] hover:border-indigo-500/50 flex items-center justify-center transition-all cursor-pointer relative group backdrop-blur-md"
                  >
                    <StatusDot status={statusType} size="sm" pulse={statusType !== 'success'} />
                    <div className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-neutral-900/95 border border-white/15 text-xs text-white shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50 max-w-xs truncate backdrop-blur-xl">
                      {item.title || item.request}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        {/* Center Canvas / Ruixen Moon Celestial Chat Interface */}
        <main className="flex-1 flex flex-col justify-between items-center px-6 py-10 overflow-y-auto overflow-x-hidden relative bg-transparent z-10">
          {/* Centered Heading Section - Subtitle & Evidence Pill removed per user instruction */}
          <div className="w-full flex-1 flex flex-col items-center justify-center pt-8 pb-4 text-center z-10 max-w-2xl mx-auto">
            {/* Headline with Caacupé One font */}
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight text-white mb-2 font-caacupe drop-shadow-md">
              What would you like Surge to investigate?
            </h1>
          </div>

          {/* Input Box Section - Ruixen Moon Chat Glass Container */}
          <div className="w-full max-w-3xl mb-8 sm:mb-12 z-10">
            {/* Hidden File Input for All Media Formats */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.md,.doc,.docx,.pptx,.xlsx,.xls,.csv,.txt,.html,.png,.jpeg,.jpg,.heic,.webp"
              className="hidden"
              onChange={(e) => {
                if (e.target.files) handleFilesSelected(e.target.files);
                e.target.value = '';
              }}
            />

            <form
              onSubmit={handleSubmit}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={cn(
                "relative bg-black/40 backdrop-blur-2xl rounded-2xl border border-white/15 shadow-2xl shadow-black/80 transition-all focus-within:border-white/25",
                isDragging && "border-indigo-400/80 bg-indigo-950/20"
              )}
            >
              {/* Attached Media/Document Chips */}
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 px-4 pt-3 pb-1 border-b border-white/10">
                  {attachedFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.12] border border-white/10 text-xs text-neutral-200 transition-all group backdrop-blur-sm"
                    >
                      {getFileIcon(file.name)}
                      <span className="font-medium truncate max-w-[150px]" title={file.name}>
                        {file.name}
                      </span>
                      <span className="text-[10px] text-neutral-400 font-mono">
                        ({formatFileSize(file.size)})
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFile(file.id)}
                        className="ml-1 p-0.5 text-neutral-400 hover:text-white rounded hover:bg-white/10 transition-colors cursor-pointer"
                        title="Remove attachment"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded hover:bg-white/5 cursor-pointer transition-colors"
                  >
                    + Add more
                  </button>
                </div>
              )}

              {/* Clean Native Textarea - Absolutely No Inner Purple Box / Ring Overlay */}
              <textarea
                ref={textareaRef}
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  adjustHeight();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Describe what changed : e.g. 'Conversion dropped after yesterday's release, investigate and coordinate the response.'"
                className="w-full px-5 py-4 resize-none border-0 border-transparent bg-transparent text-white text-sm font-sans placeholder:text-neutral-400 min-h-[52px] leading-relaxed outline-none focus:outline-none focus:ring-0 focus:border-0 shadow-none"
                style={{ overflow: 'hidden', outline: 'none', boxShadow: 'none', border: 'none' }}
              />

              {error && (
                <div className="mx-4 mb-3 p-2.5 bg-red-950/60 border border-red-800/60 rounded-xl text-red-300 text-xs">
                  {error}
                </div>
              )}

              {/* Bottom bar inside chatbox */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/10">
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => fileInputRef.current?.click()}
                    className={cn(
                      "text-neutral-400 hover:text-white hover:bg-white/10 rounded-xl size-9 transition-colors cursor-pointer",
                      attachedFiles.length > 0 && "text-indigo-400 bg-indigo-500/10 border border-indigo-500/20"
                    )}
                    title="Upload documents or media (PDF, MD, DOC, PPTX, XLSX, TXT, HTML, PNG, JPEG, HEIC, etc.)"
                  >
                    <Paperclip className="w-4 h-4" />
                  </Button>

                  {/* Connected Signal Source Indicators */}
                  <div className="hidden sm:flex items-center gap-1.5 pl-1 text-xs text-neutral-400">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-neutral-300 text-[11px]">
                      <SourceIcon app="sheets" size={13} /> Sheets
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-neutral-300 text-[11px]">
                      <SourceIcon app="github" size={13} /> GitHub
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-neutral-300 text-[11px]">
                      <SourceIcon app="slack" size={13} /> Slack
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="submit"
                    disabled={(!prompt.trim() && attachedFiles.length === 0) || submitting}
                    className={cn(
                      "size-9 p-0 rounded-xl flex items-center justify-center transition-all",
                      (prompt.trim() || attachedFiles.length > 0) && !submitting
                        ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 cursor-pointer"
                        : "bg-neutral-800/80 text-neutral-500 cursor-not-allowed border border-white/10"
                    )}
                    title="Start Investigation (Enter)"
                  >
                    {submitting ? (
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <ArrowUp className="w-4 h-4" />
                    )}
                    <span className="sr-only">Start Investigation</span>
                  </Button>
                </div>
              </div>
            </form>

            {/* Quick Action Pills Under the Chatbox - Matching Image 2 */}
            <div className="mt-6 flex flex-col items-center gap-2.5">
              {/* Primary Scenarios as Ruixen Pill Action Buttons */}
              <div className="flex items-center justify-center flex-wrap gap-2.5 w-full">
                {primaryScenarios.map((s, idx) => (
                  <Button
                    key={idx}
                    type="button"
                    variant="outline"
                    onClick={() => handleLaunchPreset(s.text, s.scenario)}
                    className="flex items-center gap-2 rounded-full border border-neutral-700/80 bg-black/60 text-neutral-300 hover:text-white hover:bg-neutral-800/90 hover:border-neutral-600 transition-all backdrop-blur-md px-4 py-2 h-auto text-xs shadow-sm cursor-pointer group text-left"
                  >
                    {s.icon}
                    <span className="text-xs font-medium max-w-[320px] sm:max-w-none truncate sm:whitespace-normal">
                      "{s.text}"
                    </span>
                  </Button>
                ))}
              </div>

              {/* Quick Topic Scope Pills */}
              <div className="flex items-center justify-center flex-wrap gap-2 pt-1">
                {quickTopicPills.map((p, idx) => (
                  <Button
                    key={idx}
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setPrompt(p.text);
                      adjustHeight();
                    }}
                    className="flex items-center gap-1.5 rounded-full border border-neutral-800/80 bg-black/40 text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/60 hover:border-neutral-700 transition-all backdrop-blur-md px-3 py-1.5 h-auto text-[11px] shadow-sm cursor-pointer"
                  >
                    {p.icon}
                    <span>{p.label}</span>
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
