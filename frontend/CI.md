# Frontend and Render CI gate

The permanent `.github/workflows/frontend-build-pr-ci.yml` workflow is the fast, observable pull-request gate for the national application.

It protects frontend dependency security, TypeScript, production build and critical browser regressions. When the Render deployment fingerprint feature is present, the same gate also runs the backend health/fingerprint tests and validates that the backend, backup cron and frontend deploy only after CI checks pass.

Runtime deployment identity is still verified separately after rollout by the manual `Verify Render Deployment` workflow; CI success alone is not treated as proof that a given Git SHA is already running on Render.
