# Couverture fonctionnelle réelle

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

Statuts : implémenté = code et tests identifiés, sans garantie d’exploitation réelle ; partiel = composant présent avec limites ; absent du chemin audité = non trouvé, sans présumer un service externe.

| Domaine | État vérifié | Code / tests | Limites bloquantes ou preuve restante |
|---|---|---|---|
| Comptes et rôles | Implémenté, partiel sécurité | security.py, routers/auth.py ; test_auth_security_invariants.py | Révocation, refresh, MFA imposée, e-mail vérifié |
| Dossiers candidats et identité | Implémenté | routers/registration.py, candidate_identity.py ; test_candidate_exam_eligibility.py | Fallback e-mail dangereux ; recette identité réelle |
| Auto-écoles | Implémenté partiel | registration.school-candidate/my-candidates ; test_candidate_self_service_authorization.py | Recette métier complète par organisation |
| Centres, sessions, réservation et entrée | Implémenté | booking_rules.py, resource_access.py, routers/entries.py ; test_multicenter_business_invariants.py | Concurrence réelle de capacité et doubles entrées à compléter |
| Examen : sélection, autosave, submit, timeout | Implémenté partiel | exam_engine.py, exam_runtime.py ; test_official_exam_runtime_e2e.py | Snapshot immuable absent ; finalisation autonome non identifiée |
| Confidentialité correction candidat/centre | Garde implémenté | exam_media_guard.py, routers/exams.py ; test_exam_attempt_access.py | Banque publique démo inutilisable comme banque confidentielle |
| Banque et homologation | Workflow implémenté partiel | routers/questions.py, official_media_readiness.py ; test_official_media_bank_gate.py | Import modifie une question approuvée en place ; banque privée homologuée non inspectée |
| Réponses multiples / règles historisées | Absentes du modèle audité | Question.correct_answer:string ; ExamAttempt | Besoin à faire valider DNTT avant développement métier |
| Médias et langues | Infrastructure implémentée, contenu partiel | media_runtime_resolver.py, question_i18n.py, frontend/public/audio | Production et homologation des audios non démontrées ; pas 19600 questions prouvées |
| Paiement tarif serveur et replay | Implémenté partiel | payment_create_guard.py, payment_rules.py ; test_payment_idempotency_lifecycle.py | Mode sandbox en production ; crash externe/commit |
| Webhooks et rapprochement | Implémenté partiel | payment_webhook_security.py, payment_reconciliation.py ; test_payment_security_invariants.py | Réconciliation principalement locale ; contrats fournisseurs à certifier |
| Remboursement à quatre yeux | Implémenté | payment_refunds.py ; test_payment_refund_workflow.py | Completion avec preuve externe déclarée, pas preuve d’un virement réellement exécuté |
| Relevés PDF et QR vérifiable | Implémenté partiel | pdf_service.py, exams.certificate/verify ; test_e2e_exam_certificate.py | Ne vaut pas titre de permis signé ; révocation/version immuable non prouvées |
| Résultats et recours | Implémenté partiel | exam_reviews.py, candidate_submissions.py ; test_general_candidate_appeals.py | Publication immédiate ; règle institutionnelle à confirmer |
| Supervision et antifraude | Implémenté partiel | exam_monitoring.py, center_anomalies.py | Production d’événements navigateur et validation en salle à compléter |
| Hors ligne centre | Implémenté, non homologué terrain | edge_agent/, center_edge_station_guard.py ; tests Edge | Trois tests de confiance rouges ; crash/coupure réelle non testés ici |
| Audit HMAC / SOC / télémétrie | Implémenté | audit_chain.py, soc_telemetry.py, ops/prometheus | Collecte externe, alertes et astreinte effectives non vérifiées |
| Sauvegardes / PRA / PITR | Outils et CI présents | postgres_backup.py, backup.yml, p10-pitr-pr-ci.yml | Restore isolé de sauvegarde réelle et RPO/RTO non attestés |
| Interface React / PWA | Source complète, build réussi | frontend/src/pages/, vite.config.ts ; 21 fichiers spec | Navigateur local bloqué ; aucune conformité WCAG déduite du build |
| Application mobile native | Ébauche | mobile/package.json, stores/auth.ts, stores/offline.ts | Pas de parcours écran natif complet identifié |
| CI/CD | Implémenté partiel | 20 workflows ; fullstack-business-e2e.yml | Dette UI exclue en CI, promotion automatique Blueprint, runtime non prêt |

Les résultats chiffrés et tests effectivement passés sont dans evidence/RESULTS.md. Les noms de tests de ce tableau identifient des preuves exécutables ; ils ne signifient pas que tous les parcours de production ont été réalisés.
