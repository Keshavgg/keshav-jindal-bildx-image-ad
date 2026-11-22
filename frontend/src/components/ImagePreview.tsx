import React, { useState } from 'react';
import { Image as ImageIcon, AlertCircle, ExternalLink } from 'lucide-react';

interface ImagePreviewProps {
  imageUrl: string;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({ imageUrl }) => {
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  if (!imageUrl.trim()) {
    return (
      <div className="h-44 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 flex flex-col items-center justify-center text-slate-500 text-xs p-4">
        <ImageIcon className="w-8 h-8 mb-2 stroke-1 text-slate-600" />
        <span>Enter a product image URL to preview source</span>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 overflow-hidden">
      <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
        <span className="font-medium">Source Product Preview</span>
        <a
          href={imageUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          <span>Open link</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <div className="relative h-44 rounded-lg bg-slate-950 flex items-center justify-center overflow-hidden border border-slate-800/80">
        {hasError ? (
          <div className="flex flex-col items-center justify-center text-rose-400 text-xs p-4 text-center">
            <AlertCircle className="w-6 h-6 mb-1.5" />
            <span>Could not load image preview from URL</span>
            <span className="text-[10px] text-slate-500 mt-1">Check URL accessibility or CORS headers</span>
          </div>
        ) : (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-950/80">
                <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            <img
              src={imageUrl}
              alt="Source product"
              className="max-h-full max-w-full object-contain transition-opacity duration-300"
              onLoad={() => setIsLoading(false)}
              onError={() => {
                setIsLoading(false);
                setHasError(true);
              }}
            />
          </>
        )}
      </div>
    </div>
  );
};
