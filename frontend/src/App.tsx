import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { ProductForm } from './components/ProductForm';
import { ImagePreview } from './components/ImagePreview';
import { StatusTracker } from './components/StatusTracker';
import { AdPreview } from './components/AdPreview';
import { GenerationRequest, GenerationStatus, GenerationStatusResponse } from './types';
import { startGeneration, getTaskStatus } from './api';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [status, setStatus] = useState<GenerationStatus>('idle');
  const [statusData, setStatusData] = useState<GenerationStatusResponse | null>(null);
  const [currentRequest, setCurrentRequest] = useState<GenerationRequest | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string>('https://bildx.ai/samples/assets/roam-front.webp');

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clear polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleStartGeneration = async (request: GenerationRequest) => {
    setErrorMessage(null);
    setCurrentRequest(request);
    setPreviewImageUrl(request.image_url);

    try {
      // Generate client-side idempotency key for this submission attempt
      const idempotencyKey = `web-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const initialResponse = await startGeneration(request, idempotencyKey);

      setStatus(initialResponse.status);
      setStatusData(initialResponse);

      // Begin polling status endpoint until completed or failed
      startPolling(initialResponse.task_id);
    } catch (err: any) {
      setStatus('failed');
      setErrorMessage(err.message || 'Failed to submit generation request.');
    }
  };

  const startPolling = (taskId: string) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    pollTimerRef.current = setInterval(async () => {
      try {
        const update = await getTaskStatus(taskId);
        setStatus(update.status);
        setStatusData(update);

        if (update.status === 'completed' || update.status === 'failed') {
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    }, 500);
  };

  const handleRetry = () => {
    if (currentRequest) {
      handleStartGeneration(currentRequest);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {errorMessage && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <div className="flex-1">
              <span className="font-semibold">Request Error: </span>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-rose-400 hover:text-rose-200"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form & Source Image Preview (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
              <h2 className="text-base font-semibold text-white mb-4 flex items-center justify-between">
                <span>Product Context</span>
                <span className="text-[11px] font-normal text-slate-400">Step 1 of 2</span>
              </h2>
              <ProductForm onSubmit={handleStartGeneration} status={status} />
            </div>

            <ImagePreview imageUrl={previewImageUrl} />
          </div>

          {/* Right Column: Status Tracker & Output Preview (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <StatusTracker statusData={statusData} onRetry={handleRetry} />

            <AdPreview
              taskId={statusData?.task_id || null}
              creativeCopy={statusData?.creative_copy || null}
              adImageUrl={statusData?.ad_image_url || null}
              productName={currentRequest?.product_name || 'Product'}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800/80 bg-slate-900/40 py-6 text-center text-xs text-slate-500">
        <p>Bildx AI (Neurix UG) Practical Assignment — Built by Keshav Jindal</p>
      </footer>
    </div>
  );
};
