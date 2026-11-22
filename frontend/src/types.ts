export type GenerationStatus = 'idle' | 'pending' | 'processing' | 'retrying' | 'completed' | 'failed';

export interface GenerationRequest {
  image_url: string;
  product_name: string;
  product_description: string;
  target_audience: string;
  key_benefits: string[];
  tone: string;
}

export interface CreativeCopy {
  headline: string;
  supporting_text: string;
  cta: string;
  visual_direction: string;
}

export interface GenerationMetadata {
  model: string;
  prompt_version: string;
  source_url: string;
  created_at: string;
  completed_at?: string;
  duration_ms?: number;
  retry_count: number;
}

export interface GenerationStatusResponse {
  task_id: string;
  status: GenerationStatus;
  idempotency_key?: string;
  created_at: string;
  updated_at: string;
  retry_count: number;
  error_message?: string;
  creative_copy?: CreativeCopy;
  ad_image_url?: string;
  metadata?: GenerationMetadata;
}
