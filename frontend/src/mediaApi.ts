import { getPrivateJson, postPrivateJson } from './api';

export type MediaType = 'image' | 'video' | 'audio';
export type MediaUsageType = 'exam' | 'course' | 'explanation' | 'thumbnail';
export type MediaQualityStatus = 'draft' | 'review_required' | 'validated' | 'rejected';
export type MediaRegulatoryStatus = 'not_reviewed' | 'under_review' | 'validated' | 'rejected';
export type MediaSourceType = 'original' | 'licensed' | 'partner' | 'public_domain' | 'internal' | 'generated' | 'legacy';

export type MediaAsset = {
  id: string; uuid: string; media_type: MediaType; usage_type: MediaUsageType;
  storage_provider?: string | null; storage_key?: string | null; public_url?: string | null; secure_url?: string | null;
  mime_type?: string | null; width?: number | null; height?: number | null; duration_seconds?: number | null;
  file_size_bytes?: number | null; checksum_sha256?: string | null; poster_media_id?: string | null; fallback_media_id?: string | null;
  theme?: string | null; subtheme?: string | null; country_code: string; regulatory_scope?: string | null;
  source_type: MediaSourceType; source_reference?: string | null; license_type?: string | null; license_reference?: string | null;
  license_expiration_date?: string | null; copyright_owner?: string | null; quality_status: MediaQualityStatus;
  regulatory_status: MediaRegulatoryStatus; regulatory_authority_reference?: string | null; validated_by?: string | null;
  validated_at?: string | null; created_by?: string | null; created_at: string; updated_at: string; archived_at?: string | null;
};

export type MediaAssetList = { items: MediaAsset[]; total: number; limit: number; offset: number };
export type MediaQualityCheck = { code: string; passed: boolean; detail: string; points: number; max_points: number };
export type MediaQualityGate = {
  media_id: string; passed: boolean; score: number; checks: MediaQualityCheck[]; blockers: string[];
  human_review_required: boolean; institutional_validation_inferred: boolean;
};
export type UploadTarget = {
  provider: string; method: 'POST' | 'PUT'; upload_url: string; storage_key?: string | null; delivery_url?: string | null;
  expires_in_seconds?: number | null; fields: Record<string, string | number>; headers: Record<string, string>; policy: Record<string, unknown>;
};
export type CreateMediaAssetPayload = {
  media_type: MediaType; usage_type: MediaUsageType; storage_provider?: string | null; storage_key?: string | null;
  public_url?: string | null; secure_url?: string | null; mime_type?: string | null; width?: number | null; height?: number | null;
  duration_seconds?: number | null; file_size_bytes?: number | null; checksum_sha256?: string | null; theme?: string | null;
  subtheme?: string | null; country_code?: string; regulatory_scope?: string | null; source_type: MediaSourceType;
  source_reference?: string | null; license_type?: string | null; license_reference?: string | null;
  license_expiration_date?: string | null; copyright_owner?: string | null;
};

function queryString(values: Record<string, string | number | boolean | undefined | null>): string {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : '';
}

export function listMediaAssets(filters: {
  limit?: number; offset?: number; media_type?: string; usage_type?: string; quality_status?: string;
  regulatory_status?: string; source_type?: string; theme?: string; search?: string; include_archived?: boolean;
} = {}): Promise<MediaAssetList> {
  return getPrivateJson<MediaAssetList>(`/api/v1/media-library/assets${queryString(filters)}`);
}
export function getMediaQualityGate(mediaId: string): Promise<MediaQualityGate> {
  return getPrivateJson<MediaQualityGate>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/quality-gate`);
}
export function createMediaAsset(payload: CreateMediaAssetPayload): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>('/api/v1/media-library/assets', payload);
}
export function getMediaUploadTarget(mediaType: MediaType, filename: string, contentType: string, provider?: string): Promise<UploadTarget> {
  const suffix = provider ? `?provider=${encodeURIComponent(provider)}` : '';
  return postPrivateJson<UploadTarget>(`/api/v1/media-library/upload-target${suffix}`, { media_type: mediaType, filename, content_type: contentType });
}
export function archiveMediaAsset(mediaId: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/archive`, {});
}
export function submitMediaQuality(mediaId: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/quality/submit`, { reason });
}
export function approveMediaQuality(mediaId: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/quality/approve`, { reason });
}
export function rejectMediaQuality(mediaId: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/quality/reject`, { reason });
}
export function submitMediaRegulatory(mediaId: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/regulatory/submit`, { reason });
}
export function approveMediaRegulatory(mediaId: string, authorityReference: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/regulatory/approve`, { authority_reference: authorityReference, reason });
}
export function rejectMediaRegulatory(mediaId: string, reason: string): Promise<MediaAsset> {
  return postPrivateJson<MediaAsset>(`/api/v1/media-library/assets/${encodeURIComponent(mediaId)}/regulatory/reject`, { reason });
}

export async function sha256File(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest)).map(value => value.toString(16).padStart(2, '0')).join('');
}

export async function inspectMediaFile(file: File, mediaType: MediaType): Promise<{ width?: number; height?: number; duration_seconds?: number }> {
  if (mediaType === 'image') {
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve(); image.onerror = () => reject(new Error('Image illisible')); image.src = url;
      });
      return { width: image.naturalWidth, height: image.naturalHeight };
    } finally { URL.revokeObjectURL(url); }
  }
  if (mediaType === 'video' || mediaType === 'audio') {
    const url = URL.createObjectURL(file);
    try {
      const media = document.createElement(mediaType === 'video' ? 'video' : 'audio');
      media.preload = 'metadata';
      await new Promise<void>((resolve, reject) => {
        media.onloadedmetadata = () => resolve(); media.onerror = () => reject(new Error('Média illisible')); media.src = url;
      });
      return {
        width: mediaType === 'video' ? (media as HTMLVideoElement).videoWidth : undefined,
        height: mediaType === 'video' ? (media as HTMLVideoElement).videoHeight : undefined,
        duration_seconds: Number.isFinite(media.duration) ? media.duration : undefined,
      };
    } finally { URL.revokeObjectURL(url); }
  }
  return {};
}

export async function uploadMediaFile(file: File, mediaType: MediaType, provider?: string): Promise<{
  provider: string; storageKey?: string | null; secureUrl: string;
}> {
  const target = await getMediaUploadTarget(mediaType, file.name, file.type, provider);
  if (target.method === 'POST') {
    const form = new FormData();
    Object.entries(target.fields).forEach(([key, value]) => form.append(key, String(value)));
    form.append('file', file);
    const response = await fetch(target.upload_url, { method: 'POST', body: form });
    if (!response.ok) throw new Error(`Upload ${target.provider} échoué (${response.status})`);
    const payload = await response.json() as { secure_url?: string; url?: string; public_id?: string };
    const secureUrl = payload.secure_url ?? payload.url;
    if (!secureUrl) throw new Error('Le provider n’a pas retourné d’URL de livraison');
    return { provider: target.provider, storageKey: payload.public_id ?? target.storage_key, secureUrl };
  }
  if (!target.delivery_url) throw new Error('Le provider S3-compatible n’a pas fourni d’URL de lecture durable');
  const response = await fetch(target.upload_url, { method: 'PUT', headers: target.headers, body: file });
  if (!response.ok) throw new Error(`Upload ${target.provider} échoué (${response.status})`);
  return { provider: target.provider, storageKey: target.storage_key, secureUrl: target.delivery_url };
}
