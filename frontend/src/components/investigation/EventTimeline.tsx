import React, { useState, useRef, useEffect } from 'react';
import type { EventOut } from '../../types/api';
import { SourceIcon } from '../ui/SourceIcon';
import { StatusDot } from '../ui/StatusDot';

interface EventTimelineProps {
  events: EventOut[];
  streamStatus?: string;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ events, streamStatus }) => {
  const [filter, setFilter] = useState<string>('ALL');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  const categories = ['ALL', 'EVIDENCE', 'HYPOTHESIS', 'ACTION', 'VERIFICATION', 'TOOL', 'ERROR'];

  const filteredEvents = events.filter((ev) => {
    if (filter === 'ALL') return true;
    const cat = ev.category.toUpperCase();
    if (filter === 'TOOL') return cat === 'TOOL' || ev.tool_name != null;
    if (filter === 'ERROR') return cat === 'ERROR' || ev.error_code != null || ev.status === 'failed';
    return cat.includes(filter);
  });

  const getCategoryColor = (category: string, status?: string | null) => {
    const norm = category.toUpperCase();
    if (norm === 'VERIFICATION') return 'text-emerald-400 border-emerald-800/60 bg-emerald-950/40';
    if (norm === 'ACTION') return 'text-amber-400 border-amber-800/60 bg-amber-950/40';
    if (norm === 'HYPOTHESIS' || norm === 'SYNTHESIS')
      return 'text-indigo-400 border-indigo-800/60 bg-indigo-950/40';
    if (norm === 'EVIDENCE' || norm === 'ANOMALY')
      return 'text-sky-400 border-sky-800/60 bg-sky-950/40';
    if (norm === 'ERROR' || status === 'failed')
      return 'text-red-400 border-red-800/60 bg-red-950/40';
    if (norm === 'RECOVERY') return 'text-emerald-400 border-emerald-800/60 bg-emerald-950/40';
    return 'text-zinc-400 border-zinc-800 bg-zinc-900/40';
  };

  return (
    <div className="flex flex-col h-full bg-[#0B0B0D] border border-[#1A1A1F] rounded overflow-hidden">
      {/* Timeline Header */}
      <div className="p-3 border-b border-[#1A1A1F] bg-[#111114]/80 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-[#F5F5F5] uppercase tracking-wider">
            Event Stream
          </span>
          <span className="text-[11px] font-mono text-[#71717A] bg-[#17171C] px-1.5 py-0.5 rounded border border-[#24242B]">
            {events.length} events
          </span>
          {streamStatus && (
            <span className="flex items-center gap-1 text-[11px] font-mono text-[#71717A]">
              <StatusDot
                status={
                  streamStatus === 'connected'
                    ? 'success'
                    : streamStatus === 'reconnecting'
                    ? 'warning'
                    : streamStatus === 'ended'
                    ? 'neutral'
                    : 'danger'
                }
                pulse={streamStatus === 'connected' || streamStatus === 'reconnecting'}
                size="sm"
              />
              <span className="capitalize">{streamStatus}</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-[11px] font-mono text-[#71717A] cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="accent-indigo-500 rounded cursor-pointer"
            />
            <span>Auto-scroll</span>
          </label>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="px-3 py-1.5 border-b border-[#1A1A1F] bg-[#0E0E11] flex items-center gap-1.5 overflow-x-auto">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`text-[11px] font-mono px-2 py-0.5 rounded transition-colors cursor-pointer shrink-0 ${
              filter === cat
                ? 'bg-indigo-950/60 text-indigo-300 border border-indigo-800/60'
                : 'text-[#71717A] hover:text-[#A1A1AA] hover:bg-[#17171C]'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs">
        {filteredEvents.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-xs text-[#71717A]">
            No events recorded yet.
          </div>
        ) : (
          filteredEvents.map((ev) => {
            const time = ev.timestamp ? ev.timestamp.substring(11, 19) : '--:--:--';
            const catClass = getCategoryColor(ev.category, ev.status);

            return (
              <div
                key={ev.id || ev.sequence}
                className="p-2.5 bg-[#111114] border border-[#1A1A1F] hover:border-[#24242B] rounded transition-colors"
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#71717A] font-bold">#{ev.sequence}</span>
                    <span className="text-[11px] text-[#A1A1AA]">{time}</span>
                    <span
                      className={`text-[10px] uppercase font-bold px-1.5 py-0.2 rounded border ${catClass}`}
                    >
                      {ev.category}
                    </span>
                    {ev.external_app && (
                      <span className="flex items-center gap-1 text-[11px] text-[#71717A]">
                        <SourceIcon app={ev.external_app} size={12} />
                        <span className="uppercase">{ev.external_app}</span>
                      </span>
                    )}
                  </div>

                  {ev.duration_ms != null && (
                    <span className="text-[10px] text-[#71717A]">{ev.duration_ms}ms</span>
                  )}
                </div>

                <div className="text-[#F5F5F5] font-medium leading-relaxed mb-1">
                  {ev.title}
                </div>

                {ev.summary && (
                  <div className="text-[11px] text-[#A1A1AA] leading-normal mb-1">
                    {ev.summary}
                  </div>
                )}

                {ev.tool_name && (
                  <div className="text-[11px] text-[#71717A] flex items-center gap-1.5 mt-1">
                    <span className="text-[#A1A1AA]">tool:</span>
                    <code className="bg-[#17171C] px-1 py-0.5 rounded text-[#818CF8]">
                      {ev.tool_name}
                    </code>
                    {ev.status && (
                      <span
                        className={`text-[10px] font-bold uppercase ${
                          ev.status === 'succeeded' ? 'text-emerald-400' : 'text-amber-400'
                        }`}
                      >
                        [{ev.status}]
                      </span>
                    )}
                  </div>
                )}

                {ev.error_code && (
                  <div className="text-[11px] text-red-400 bg-red-950/30 border border-red-900/50 p-1.5 rounded mt-1.5">
                    Error ({ev.error_code}): {ev.summary || 'Operation failed'}
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
