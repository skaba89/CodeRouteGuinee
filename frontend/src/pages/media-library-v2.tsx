import { useState } from 'react';
import { MediaLibraryPage as MediaLibraryCore } from './media-library';
import { MediaMigrationProgressPanel } from '../components/MediaMigrationProgressPanel';
import { MediaMigrationQueuePanel, type MediaQueueQuestionRef } from '../components/MediaMigrationQueuePanel';
import { MediaBatchMigrationWorkbench } from '../components/MediaBatchMigrationWorkbench';
import { MediaQuestionMappingWorkbench, type MediaMappingQuestionRef } from '../components/MediaQuestionMappingWorkbench';
import { MediaVideoSupportWorkbench } from '../components/MediaVideoSupportWorkbench';

/**
 * Phase 5 composed admin surface.
 *
 * The existing media-library implementation remains untouched. Additive
 * panels handle migration observability, actionable migration, controlled
 * batch/manual question mapping and resilient video support independently from
 * upload/review workflows.
 */
export function MediaLibraryPage() {
  const [focusedQuestion, setFocusedQuestion] = useState<MediaMappingQuestionRef | null>(null);

  function focusQuestion(question: MediaQueueQuestionRef) {
    setFocusedQuestion({ id: question.question_id, text: question.text, category: question.category });
  }

  return (
    <>
      <MediaLibraryCore />
      <MediaMigrationProgressPanel />
      <MediaMigrationQueuePanel onMapQuestion={focusQuestion} />
      <MediaBatchMigrationWorkbench />
      <MediaQuestionMappingWorkbench focusQuestion={focusedQuestion} />
      <MediaVideoSupportWorkbench />
    </>
  );
}
