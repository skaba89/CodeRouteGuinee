# Matrice fonctionnelle — CodeRoute Guinée

> État au 25/10/2026, `main` @ `3b9318d`. Légende :
> **✅ Implémentée et testée** · **🟡 Partielle** · **❌ Absente** · **❔ Non vérifiée** (code présent, comportement réel non démontré).

## 1. Parcours candidat

| Fonctionnalité | État | Preuve (code / test) |
|---|---|---|
| Inscription publique + compte | ✅ | `routers/registration.py`, `test_e2e_registration.py` |
| Dépôt et validation d'identité (`verified`) | ✅ | `routers/candidate_identity.py`, `test_candidate_exam_eligibility.py` |
| Réservation de session (capacité, fenêtres) | ✅ | `booking_service.py`, `test_e2e_candidate_booking.py` |
| Clôture des inscriptions la veille | ❌ | aucune règle trouvée |
| Tarification serveur | ✅ | `tarifs.py`, `routers/payment_quote.py` |
| Paiement Mobile Money (Orange, MTN, Wave, Moov) | 🟡 | dispatcher fail-closed, webhooks signés (`payment_webhook_security.py`) ; **❔ fournisseurs réels** |
| Paiement en espèces (import officiel) | ✅ | `/payments/admin/import-official`, `test_e2e_pilote_journee_reelle.py` |
| Remboursements à quatre yeux | ✅ | `routers/payment_refunds.py` (`REFUND_SELF_DECISION_FORBIDDEN`) |
| Convocation PDF | ✅ | `convocation_service.py`, `routers/documents.py` |
| Notifications e-mail, SMS, WhatsApp | ❔ | `email_service.py`, `orange_sms.py`, `whatsapp_service.py` ; pas de file de réessai |
| Recours candidat | 🟡 | `routers/candidate_submissions.py` ; pas de gel du résultat |
| Attestation PDF + QR de vérification | ✅ | `pdf_service.py`, `certificate-verify.tsx`, `test_exam_certificate_verification.py` |
| Durée de validité de l'attestation | ❌ | aucune expiration |
| Délai avant nouvelle tentative | ❌ | `attempt_count` incrémenté mais jamais contrôlé |

## 2. Épreuve

| Fonctionnalité | État | Preuve |
|---|---|---|
| Contrôle d'entrée physique (check-in) | ✅ | `entry_service.py`, `test_e2e_exam_center_gate.py` |
| Fenêtres d'entrée (−60/+30 min) et de démarrage (−10/+45 min) | ✅ | `exam_center_gate.py` |
| Restriction aux postes enregistrés | ✅ | `models_center_station.py`, `test_e2e_center_stations_registry.py` |
| Tirage par catégorie (répartition 10/6/5/5/4/4/3/3) | ✅ | `exam_engine.select_exam_questions`, `test_exam_engine.py` |
| Examen **personnalisé** (questions différentes par candidat) | ❌ | le pool officiel est égal à la répartition (40/40) |
| Trace de la tentative (ids, hash de la banque, hash de la sélection) | ✅ | `models_exam_question_trace.py`, `test_e2e_exam_question_trace.py` |
| Bonnes réponses jamais envoyées au navigateur (officiel) | ✅ | `ExamQuestionItem` sans clé, `test_exam_bank_confidentiality.py` |
| Bonnes réponses dans le bundle frontend | 🟡 | `examQuestions.ts` : 40 questions de démo avec réponses, dont 2 identiques à la banque officielle |
| QCM à réponse unique | ✅ | `score_answers` |
| QCM à plusieurs bonnes réponses | ❌ | `correct_answer: String` |
| Questions image | 🟡 | contrat média complet ; 0 question officielle illustrée |
| Questions vidéo | 🟡 | `ExamMediaPremium.tsx`, `mediaVideoApi.ts` ; vidéo de démo tronquée |
| Questions audio (énoncé en langue nationale) | 🟡 | champ `translations[lang].audio_url` ; 0 fichier audio |
| Chronomètre serveur visible | ✅ | `GET /exams/{id}/status`, `exam.tsx:763-793` |
| Progression visible (n / 40) | ✅ | `exam.tsx:786` |
| Navigation libre, marquage et relecture des questions | ❌ | navigation séquentielle uniquement (`exam-sequential-navigation.spec.ts`) |
| Autosauvegarde serveur | ✅ | `routers/exam_runtime.py`, `test_exam_runtime_recovery.py` |
| Reprise après rafraîchissement ou changement de poste | ✅ | `start-from-booking` → `exam.attempt_resumed` |
| Pause du chrono en cas d'incident | ❌ | horloge murale (`_deadline`) |
| Finalisation automatique à l'échéance (client) | ✅ | `timeout-submit` |
| Finalisation automatique serveur (tâche planifiée) | ❌ | aucun planificateur |
| Soumission complète obligatoire | ✅ | `exam_submit_completion_guard.py` |
| Idempotence de la soumission | ✅ | `exam.replay_submission` |
| Mode hors-ligne du centre (edge) | ❔ | `edge_agent/` (2 753 lignes + tests) ; pas d'essai sur le terrain |
| Familiarisation (examen blanc, entraînement) | ✅ | `training.tsx`, `routers/training.py` (banque d'entraînement séparée) |
| Tutoriel guidé de l'interface officielle | ❌ | — |
| Accessibilité : clavier, ARIA | 🟡 | touches 1-4, `aria-label` ; pas d'audit WCAG |
| Accessibilité : temps majoré | ❌ | — |

## 3. Résultats

| Fonctionnalité | État | Preuve |
|---|---|---|
| Notation automatique | ✅ | `score_answers`, `test_exam_flow.py` |
| Score et fautes par thème sans bonnes réponses | ✅ | `routers/exams.py:771-850` (PR #254) |
| Correction détaillée réservée à l'administration | ✅ | `detail_level=full` pour `admin`/`super_admin` |
| Publication différée ou contrôlée | ❌ | publication immédiate + notification |
| Validation et signature du PV de session | ❌ | — |
| Résultat signé ou scellé | 🟡 | audit HMAC chaîné (`exam.submitted`) ; pas de signature du résultat lui-même |

## 4. Banque de questions

| Fonctionnalité | État | Preuve |
|---|---|---|
| Workflow draft → submitted → approved/rejected | ✅ | `routers/question_governance.py`, `test_e2e_question_validation.py` |
| Séparation banque officielle / entraînement | ✅ | `filter_official_exam_pool`, `TRAINING_BANK` |
| Import officiel (CSV) | ✅ | `importOfficialQuestions` |
| Versionnement immuable des questions | ❌ | `version: int` sans historique |
| Banque confidentielle (hors dépôt public) | ❌ | `question_bank_gn.py` public |
| Taille suffisante pour personnaliser | ❌ | 40 questions officielles |
| Statistiques par question (taux de réussite, discrimination) | ❌ | — |
| Gouvernance des médias (licence, HTTPS, alt, revue) | ✅ | `media_policy.py`, `official_media_readiness.py`, `routers/media_reviews.py` |

## 5. Centres, auto-écoles, supervision

| Fonctionnalité | État | Preuve |
|---|---|---|
| Gestion des centres et agréments | ✅ | `routers/centers.py`, `routers/institutional_authorizations.py` |
| Périmètre de l'agent limité à son centre | ✅ | `CENTER_SCOPE_MISMATCH`, `test_entries_coverage.py` |
| Postes et équipements | ✅ | `center_stations.py`, `device_sessions.py` |
| Incidents de centre + rattrapage | ✅ | `routers/center_incidents.py`, `test_e2e_center_incident_recovery.py` |
| Espace auto-école | 🟡 | `driving-school.tsx` ; peu de routes dédiées |
| Tableau national et régional (8 régions) | ✅ | `territory.py`, `routers/dashboard.py` |
| Anomalies statistiques par centre | ✅ | `center_anomalies.py`, `GET /dashboard/center-anomalies` |
| Exports CSV et PDF | ✅ | `routers/dashboard.py`, `routers/exams.py:521` |

## 6. Sécurité, traçabilité, exploitation

| Fonctionnalité | État | Preuve |
|---|---|---|
| JWT + refresh, bcrypt, limitation des connexions, CSRF | ✅ | `routers/auth.py`, `csrf.py` |
| 2FA TOTP | 🟡 | optionnelle (`two_factor.py`) |
| Révocation de session | ❌ | — |
| Journal d'audit HMAC chaîné + vérification | ✅ | `audit_chain.py`, `test_dr_readiness.py` |
| RGPD : pseudonymisation, purge | 🟡 | `rgpd.py`, `soc_privacy.py` ; durées de conservation à fixer |
| Secrets refusés s'ils sont faibles en production | ✅ | `core/config.py:118-170`, `test_production_secrets.py` |
| Sauvegardes, PITR, HA | 🟡 | `backup.yml`, workflows P10 ; restauration réelle non démontrée ici |
| SOC, métriques Prometheus, Sentry | ❔ | `soc_*.py`, `metrics.py` |
| Chaîne d'approvisionnement des releases edge | ✅ | `center_edge_supply_chain.py`, `edge-release-supply-chain.yml` |

## 7. Synthèse chiffrée

| État | Nombre |
|---|---|
| ✅ Implémentée et testée | 41 |
| 🟡 Partielle | 12 |
| ❌ Absente | 17 |
| ❔ Non vérifiée | 3 |
| **Total** | **73** |
