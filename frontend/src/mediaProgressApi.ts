import { getPrivateJson } from './api';

export type MediaMigrationProgress = {
  total_questions: number;
  normalized_primary: number;
  normalized_percent: number;
  publishable_premium: number;
  publishable_percent: number;
  normalized_blocked: number;
  generated_or_legacy_primary: number;
  legacy_only: number;
  no_media: number;
  by_primary_type: {
    image: number;
    video: number;
  };
  blocked_question_ids_sample: string[];
  definition: Record<string, string>;
  institutional_validation_inferred: boolean;
};

export function getMediaMigrationProgress(): Promise<MediaMigrationProgress> {
  return getPrivateJson<MediaMigrationProgress>('/api/v1/media-library/migration-progress');
}
