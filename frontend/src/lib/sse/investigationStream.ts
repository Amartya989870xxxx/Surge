import type { EventOut } from '../../types/api';

export type StreamStatus = 'connecting' | 'connected' | 'reconnecting' | 'ended' | 'error';

export interface StreamHandlers {
  onEvent: (event: EventOut) => void;
  onStatusChange?: (status: StreamStatus, detail?: string) => void;
  onError?: (err: any) => void;
}

export class InvestigationStream {
  private investigationId: string;
  private handlers: StreamHandlers;
  private eventSource: EventSource | null = null;
  private lastSequence: number = 0;
  private isClosed: boolean = false;
  private reconnectTimer: any = null;
  private reconnectAttempts: number = 0;

  constructor(investigationId: string, handlers: StreamHandlers, initialSequence: number = 0) {
    this.investigationId = investigationId;
    this.handlers = handlers;
    this.lastSequence = initialSequence;
    this.connect();
  }

  public connect(): void {
    if (this.isClosed) return;

    this.handlers.onStatusChange?.(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');

    const url = `/api/investigations/${this.investigationId}/stream?after=${this.lastSequence}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      this.handlers.onStatusChange?.('connected');
    };

    this.eventSource.onerror = (err) => {
      if (this.isClosed) return;
      this.eventSource?.close();
      this.eventSource = null;
      
      this.handlers.onStatusChange?.('reconnecting', 'Connection lost, retrying...');
      this.handlers.onError?.(err);

      // Reconnect with exponential backoff capped at 5s
      const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 5000);
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    };

    // Standard message or custom event listener
    this.eventSource.onmessage = (e) => {
      this.handleRawMessage(e);
    };

    // Specific terminal event sent by Surge backend: "event: end"
    this.eventSource.addEventListener('end', () => {
      this.handlers.onStatusChange?.('ended');
      this.close();
    });

    // Listen to named events. This list must match app/enums.py EventType exactly -
    // EventSource.addEventListener only fires for the literal event name the server sent; any
    // real backend event type missing here is silently dropped, never reaching onEvent at all.
    const namedEvents = [
      'INVESTIGATION_CREATED',
      'STATUS_CHANGED',
      'PLAN',
      'TOOL_CALL_STARTED',
      'TOOL_CALL_SUCCEEDED',
      'TOOL_CALL_FAILED',
      'TOOL_RETRY',
      'EVIDENCE',
      'NOT_APPLICABLE',
      'ANOMALY',
      'HYPOTHESES_GENERATED',
      'HYPOTHESIS_UPDATED',
      'SUFFICIENCY_CHECK',
      'DEGRADED',
      'SYNTHESIS',
      'POLICY',
      'ACTION_PROPOSED',
      'APPROVAL_REQUIRED',
      'ACTION_APPROVED',
      'ACTION_REJECTED',
      'ACTION_BLOCKED',
      'ACTION_EXECUTING',
      'ACTION_EXECUTED',
      'ACTION_AMBIGUOUS',
      'ACTION_FAILED',
      'IDEMPOTENT_REPLAY',
      'VERIFICATION',
      'LLM_FALLBACK',
      'COMPLETED',
      'FAILED',
      'CANCELLED',
    ];

    namedEvents.forEach((eventType) => {
      this.eventSource?.addEventListener(eventType, (e: MessageEvent) => {
        this.handleRawMessage(e);
      });
    });
  }

  private handleRawMessage(e: MessageEvent): void {
    try {
      if (!e.data || e.data.trim() === '{}') return;
      const parsed: EventOut = JSON.parse(e.data);
      if (parsed && typeof parsed.sequence === 'number') {
        if (parsed.sequence > this.lastSequence) {
          this.lastSequence = parsed.sequence;
        }
        this.handlers.onEvent(parsed);
      }
    } catch (err) {
      console.error('Failed to parse SSE event data:', e.data, err);
    }
  }

  public updateSequence(seq: number): void {
    if (seq > this.lastSequence) {
      this.lastSequence = seq;
    }
  }

  public close(): void {
    this.isClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
