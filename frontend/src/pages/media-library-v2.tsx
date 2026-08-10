import { MediaLibraryPage as MediaLibraryCore } from './media-library';
import { MediaQuestionMappingWorkbench } from '../components/MediaQuestionMappingWorkbench';
import { MediaVideoSupportWorkbench } from '../components/MediaVideoSupportWorkbench';

/**
 * Phase 5 composed admin surface.
 *
 * The existing media-library implementation remains untouched. Additive
 * workbenches handle controlled question mapping and resilient video support
 * configuration independently from upload/review workflows.
 */
export function MediaLibraryPage() {
  return (
    <>
      <MediaLibraryCore />
      <MediaQuestionMappingWorkbench />
      <MediaVideoSupportWorkbench />
    </>
  );
}
