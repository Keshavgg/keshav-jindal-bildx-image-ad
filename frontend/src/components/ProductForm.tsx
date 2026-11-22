import React, { useState } from 'react';
import { GenerationRequest, GenerationStatus } from '../types';
import { Sparkles, Plus, X, Wand2, RefreshCw } from 'lucide-react';

interface ProductFormProps {
  onSubmit: (data: GenerationRequest) => void;
  status: GenerationStatus;
}

const PRESETS: Array<{ label: string; data: GenerationRequest }> = [
  {
    label: 'ROAM Lock 750 (PDF Sample)',
    data: {
      image_url: 'https://bildx.ai/samples/assets/roam-front.webp',
      product_name: 'ROAM Lock 750',
      product_description: 'A 750 ml insulated steel tumbler with a locking sip lid.',
      target_audience: 'Commuters, gym users and day hikers',
      key_benefits: ['Up to 12 hours cold', 'Carry loop', 'Locking lid'],
      tone: 'Adventurous and practical',
    },
  },
  {
    label: 'AURA Glow Serum (Skincare)',
    data: {
      image_url: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=600&q=80',
      product_name: 'AURA Radiance Serum',
      product_description: 'Pure 15% Vitamin C and dual-weight hyaluronic acid daily facial booster.',
      target_audience: 'Skincare enthusiasts and professionals seeking natural daily glow',
      key_benefits: ['All-day moisture barrier', '15% stabilized Vitamin C', 'Silky non-greasy finish'],
      tone: 'Luxe and gentle',
    },
  },
  {
    label: 'NOVA Soundbar (Home Tech)',
    data: {
      image_url: 'https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=600&q=80',
      product_name: 'NOVA Soundbar 2.1',
      product_description: 'Ultra-slim cinematic TV soundbar with wireless high-excursion subwoofer.',
      target_audience: 'Movie enthusiasts and apartment dwellers wanting immersive audio',
      key_benefits: ['Dolby Audio decoding', 'Wireless subwoofer connection', 'Single cable HDMI eARC'],
      tone: 'Cinematic and modern',
    },
  },
];

export const ProductForm: React.FC<ProductFormProps> = ({ onSubmit, status }) => {
  const [formData, setFormData] = useState<GenerationRequest>(PRESETS[0].data);
  const [newBenefit, setNewBenefit] = useState('');

  const isWorking = status === 'pending' || status === 'processing' || status === 'retrying';

  const handleApplyPreset = (preset: GenerationRequest) => {
    setFormData({ ...preset, key_benefits: [...preset.key_benefits] });
  };

  const handleAddBenefit = () => {
    if (newBenefit.trim() && formData.key_benefits.length < 10) {
      setFormData({
        ...formData,
        key_benefits: [...formData.key_benefits, newBenefit.trim()],
      });
      setNewBenefit('');
    }
  };

  const handleRemoveBenefit = (index: number) => {
    setFormData({
      ...formData,
      key_benefits: formData.key_benefits.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isWorking) return;
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Quick Presets */}
      <div>
        <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-2">
          Quick Sample Presets
        </label>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(p.data)}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700 transition-colors flex items-center gap-1.5 font-medium"
            >
              <Wand2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Image URL */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Public Product Image URL <span className="text-emerald-400">*</span>
        </label>
        <input
          type="url"
          required
          value={formData.image_url}
          onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
          placeholder="https://example.com/product.webp"
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all font-mono text-xs"
        />
        <p className="text-[11px] text-slate-500 mt-1">
          Supports PNG, JPEG, and WebP (up to 10MB). SSRF protected.
        </p>
      </div>

      {/* Product Name */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Product Name <span className="text-emerald-400">*</span>
        </label>
        <input
          type="text"
          required
          maxLength={100}
          value={formData.product_name}
          onChange={(e) => setFormData({ ...formData, product_name: e.target.value })}
          placeholder="e.g. ROAM Lock 750"
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all font-medium"
        />
      </div>

      {/* Product Description */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Factual Product Description <span className="text-emerald-400">*</span>
        </label>
        <textarea
          required
          rows={3}
          maxLength={500}
          value={formData.product_description}
          onChange={(e) => setFormData({ ...formData, product_description: e.target.value })}
          placeholder="A 750 ml insulated steel tumbler with a locking sip lid."
          className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all resize-none"
        />
        <div className="flex justify-between text-[11px] text-slate-500 mt-1">
          <span>Grounded facts only. Never hallucinate specs.</span>
          <span>{formData.product_description.length}/500</span>
        </div>
      </div>

      {/* Target Audience */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Target Audience <span className="text-emerald-400">*</span>
        </label>
        <input
          type="text"
          required
          maxLength={200}
          value={formData.target_audience}
          onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
          placeholder="e.g. Commuters, gym users and day hikers"
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
        />
      </div>

      {/* Key Benefits */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Key Benefits <span className="text-emerald-400">*</span>
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {formData.key_benefits.map((benefit, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium"
            >
              <span>{benefit}</span>
              <button
                type="button"
                onClick={() => handleRemoveBenefit(i)}
                className="hover:text-rose-400 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={newBenefit}
            onChange={(e) => setNewBenefit(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAddBenefit();
              }
            }}
            placeholder="Add key benefit (e.g. Up to 12 hours cold)"
            className="flex-1 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
          />
          <button
            type="button"
            onClick={handleAddBenefit}
            disabled={!newBenefit.trim() || formData.key_benefits.length >= 10}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add</span>
          </button>
        </div>
      </div>

      {/* Desired Tone */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Desired Tone <span className="text-emerald-400">*</span>
        </label>
        <input
          type="text"
          required
          maxLength={100}
          value={formData.tone}
          onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
          placeholder="e.g. Adventurous and practical"
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
        />
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isWorking}
        className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-slate-950 font-semibold shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all transform active:scale-[0.99]"
      >
        {isWorking ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
            <span>Generating Advertisement...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 text-slate-950" />
            <span>Generate Grounded Ad</span>
          </>
        )}
      </button>
    </form>
  );
};
