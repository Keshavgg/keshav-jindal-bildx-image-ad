import React from 'react';
import { GenerationStatus, GenerationStatusResponse } from '../types';
import { Clock, RefreshCw, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

interface StatusTrackerProps {
  statusData: GenerationStatusResponse | null;
  onRetry: () => void;
}

export const StatusTracker: React.FC<StatusTrackerProps> = ({ statusData, onRetry }) => {
  if (!statusData) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 text-center text-slate-500 text-xs">
        <Info className="w-5 h-5 mx-auto mb-2 opacity-60" />
        <span>No generation task in progress. Fill in the product details and click Generate.</span>
      </div>
    );
  }

  const { status, task_id, retry_count, error_message, metadata } = statusData;

  const renderBadge = () => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
            <Clock className="w-3.5 h-3.5 animate-pulse" />
            <span>Pending In Queue</span>
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Processing Generation</span>
          </span>
        );
      case 'retrying':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Retrying Temporary Failure (Attempt #{retry_count})</span>
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Completed Successfully</span>
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
            <XCircle className="w-3.5 h-3.5" />
            <span>Generation Failed</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
            Task Execution Status
          </span>
          <div className="flex items-center gap-2">
            {renderBadge()}
            {retry_count > 0 && status !== 'retrying' && (
              <span className="text-xs text-purple-400/90 font-mono">({retry_count} retries)</span>
            )}
          </div>
        </div>

        <div className="text-right">
          <span className="text-[10px] text-slate-500 block">Stable Task ID</span>
          <span className="text-xs font-mono text-slate-400" title={task_id}>
            {task_id.substring(0, 13)}...
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {status === 'failed' && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-300 space-y-2">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold block text-rose-200">Execution Error:</span>
              <p className="mt-0.5 text-rose-300/90 font-mono text-[11px] break-all">{error_message}</p>
            </div>
          </div>
          <button
            onClick={onRetry}
            className="w-full py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Generation</span>
          </button>
        </div>
      )}

      {/* Metadata Audit Strip */}
      {metadata && (
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
          <span>Model: <span className="text-slate-400 font-mono">{metadata.model}</span></span>
          <span>Prompt: <span className="text-slate-400 font-mono">{metadata.prompt_version}</span></span>
          {metadata.duration_ms && (
            <span>Latency: <span className="text-slate-300 font-mono font-medium">{(metadata.duration_ms / 1000).toFixed(2)}s</span></span>
          )}
        </div>
      )}
    </div>
  );
};
