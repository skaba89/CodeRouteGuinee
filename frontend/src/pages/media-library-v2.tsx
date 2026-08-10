import { MediaLibraryPage as MediaLibraryCore } from './media-library';
import { MediaQuestionMappingWorkbench } from '../components/MediaQuestionMappingWorkbench';

/**
 * Phase 5 composed admin surface.
 *
 * The existing media-library implementation remains untouched. The mapping
 * workbench is appended as an additive migration tool so it can be removed or
 * iterated independently without destabilising upload/review workflows.
 */
export function MediaLibraryPage() {
  return (
    <>
      <MediaLibraryCore />
      <MediaQuestionMappingWorkbench />
    </>
  );
}
