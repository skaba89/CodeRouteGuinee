// API publique stable des composants d'examen.
// Les panneaux/scènes/timer/navigation restent inchangés dans le module legacy ;
// les médias réels image/vidéo utilisent le rendu premium.
export type { QData } from './shared-exam-components-legacy';
export { SignSvg, SceneSvg, Timer, QGrid } from './shared-exam-components-legacy';
export { MediaBlock, VideoPlayer } from '../components/ExamMediaPremium';
