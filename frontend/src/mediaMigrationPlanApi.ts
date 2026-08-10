import { postPrivateJson } from './api';

export type MediaMigrationPlanMapping = {
  question_id: string;
  media_id: string;
};

export type MediaMigrationPlanItem = {
  question_id: string;
  media_id: string;
  question_status?: string;
  media_type?: string;
  media_theme?: string | null;
  status: 'ready_create' | 'ready_replace' | 'no_op' | 'blocked' | 'missing_question' | 'missing_media' | 'conflict_existing_primary' | string;
  ready: boolean;
  blocker_codes: string[];
  blocker_details: string[];
  existing_primary_media_id?: string | null;
};

export type MediaMigrationPlanResult = {
  dry_run: boolean;
  replace_existing: boolean;
  all_ready: boolean;
  applied: number;
  summary: Record<string, number>;
  items: MediaMigrationPlanItem[];
  institutional_validation_inferred: boolean;
};

export function runMediaMigrationPlan(payload: {
  dry_run: boolean;
  replace_existing: boolean;
  reason: string;
  mappings: MediaMigrationPlanMapping[];
}): Promise<MediaMigrationPlanResult> {
  return postPrivateJson<MediaMigrationPlanResult>('/api/v1/media-library/migration-plan', payload);
}
