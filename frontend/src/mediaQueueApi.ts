import { getPrivateJson } from './api';

export type MediaMigrationQueueState =
  | 'needs_action'
  | 'all'
  | 'publishable'
  | 'normalized_blocked'
  | 'legacy_only'
  | 'no_media';

export type MediaMigrationPrimary = {
  id: string;
  media_type: string;
  theme?: string | null;
  source_type: string;
  quality_status: string;
  regulatory_status: string;
};

export type MediaMigrationQueueItem = {
  question_id: string;
  category: string;
  text: string;
  validation_status: string;
  is_active: boolean;
  queue_state: Exclude<MediaMigrationQueueState, 'needs_action' | 'all'>;
  priority: 'official_first' | 'normal' | string;
  legacy_media_present: boolean;
  legacy_media_type?: string | null;
  primary_media?: MediaMigrationPrimary | null;
  blocker_codes: string[];
  blocker_details: string[];
  next_action: string;
};

export type MediaMigrationQueueResponse = {
  items: MediaMigrationQueueItem[];
  total: number;
  matched_questions: number;
  limit: number;
  offset: number;
  state_filter: MediaMigrationQueueState;
  counts_by_state: {
    publishable: number;
    normalized_blocked: number;
    legacy_only: number;
    no_media: number;
  };
  institutional_validation_inferred: boolean;
};

export function getMediaMigrationQueue(filters: {
  state_filter?: MediaMigrationQueueState;
  category?: string;
  question_status?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<MediaMigrationQueueResponse> {
  const query = new URLSearchParams();
  query.set('state_filter', filters.state_filter ?? 'needs_action');
  if (filters.category) query.set('category', filters.category);
  if (filters.question_status) query.set('question_status', filters.question_status);
  if (filters.search) query.set('search', filters.search);
  query.set('limit', String(filters.limit ?? 50));
  query.set('offset', String(filters.offset ?? 0));
  return getPrivateJson<MediaMigrationQueueResponse>(`/api/v1/media-library/migration-queue?${query.toString()}`);
}
