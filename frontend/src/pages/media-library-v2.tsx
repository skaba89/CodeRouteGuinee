import { MediaLibraryPage as MediaLibraryCore } from './media-library';
import { MediaMigrationProgressPanel } from '../components/MediaMigrationProgressPanel';
import { MediaQuestionMappingWorkbench } from '../components/MediaQuestionMappingWorkbench';
import { MediaVideoSupportWorkbench } from '../components/MediaVideoSupportWorkbench';

/**
 * Phase 5 composed admin surface.
 *
 * The existing media-library implementation remains untouched. Additive
 * panels handle migration observability, controlled question mapping and
 * resilient video support independently from upload/review workflows.
 */
export function MediaLibraryPage() {
  return (
    <>
      <MediaLibraryCore />
      <MediaMigrationProgressPanel />
      <MediaQuestionMappingWorkbench />
      <MediaVideoSupportWorkbench />
    </>
  );
}
