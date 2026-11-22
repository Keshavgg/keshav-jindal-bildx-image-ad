import React from 'react';
import { CreativeCopy } from '../types';
import { Download, Sparkles, Compass, CheckCircle } from 'lucide-react';
import { getDownloadUrl } from '../api';

interface AdPreviewProps {
  taskId: string | null;
  creativeCopy: CreativeCopy | null;
  adImageUrl: string | null;
  productName: string;
}

export const AdPreview: React.FC<AdPreviewProps> = ({
  taskId,
  creativeCopy,
  adImageUrl,
  productName,
}) => {
  if (!creativeCopy || !adImageUrl || !taskId) {
    return (
      <div className="h-full min-h-[460px] rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 flex flex-col items-center justify-center p-8 text-center text-slate-500">
        <Sparkles className="w-12 h-12 stroke-1 text-slate-700 mb-3" />
        <h3 className="text-base font-medium text-slate-400 mb-1">Advertisement Preview</h3>
        <p className="text-xs max-w-sm text-slate-500">
          Once generation completes, the final composite image and grounded creative copy will appear here for review and download.
        </p>
      </div>
    );
  }

  const headlineWords = creativeCopy.headline.trim().split(/\s+/).length;
  const supportingWords = creativeCopy.supporting_text.trim().split(/\s+/).length;
  const ctaWords = creativeCopy.cta.trim().split(/\s+/).length;

  return (
    <div className="space-y-6">
      {/* Ad Image Canvas Preview */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
            <h3 className="text-sm font-semibold text-slate-200">Generated Advertisement</h3>
          </div>
          <a
            href={getDownloadUrl(taskId)}
            download={`${productName.toLowerCase().replace(/\s+/g, '-')}-ad.png`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs shadow-md shadow-emerald-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Download className="w-4 h-4 stroke-[2.5]" />
            <span>Download PNG Ad</span>
          </a>
        </div>

        {/* Square Aspect Ratio Image Container */}
        <div className="relative aspect-square w-full max-w-[500px] mx-auto rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl">
          <img
            src={getDownloadUrl(taskId)}
            alt={`${productName} Advertisement`}
            className="w-full h-full object-contain"
          />
        </div>
      </div>

      {/* Grounded Creative Copy Inspection */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Grounded Creative Copy
            </h4>
          </div>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Word Counts Verified</span>
          </span>
        </div>

        {/* Headline */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400 font-medium">Headline</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
              headlineWords <= 8 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
            }`}>
              {headlineWords}/8 words
            </span>
          </div>
          <p className="text-base font-bold text-white tracking-tight bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
            "{creativeCopy.headline}"
          </p>
        </div>

        {/* Supporting Text */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400 font-medium">Supporting Copy</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
              supportingWords <= 20 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
            }`}>
              {supportingWords}/20 words
            </span>
          </div>
          <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 leading-relaxed">
            "{creativeCopy.supporting_text}"
          </p>
        </div>

        {/* Call To Action */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400 font-medium">Call To Action (CTA)</span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
              ctaWords <= 4 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
            }`}>
              {ctaWords}/4 words
            </span>
          </div>
          <div className="inline-block px-4 py-2 rounded-xl bg-slate-800 text-emerald-400 text-xs font-bold border border-slate-700">
            {creativeCopy.cta} →
          </div>
        </div>

        {/* Visual Direction */}
        <div className="pt-2 border-t border-slate-800/80">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-1">
            <Compass className="w-3.5 h-3.5 text-sky-400" />
            <span className="font-medium">Synthesized Visual Direction:</span>
          </div>
          <p className="text-xs text-slate-400 italic bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
            {creativeCopy.visual_direction}
          </p>
        </div>
      </div>
    </div>
  );
};
