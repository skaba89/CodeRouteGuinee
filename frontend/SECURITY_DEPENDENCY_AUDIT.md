# Frontend dependency security audit

## 2026-08-09 remediation

The production/CI install previously reported four high-severity npm findings on the locked frontend dependency tree. The findings were transitive dependencies, not application source-code imports.

Compatible `npm audit fix --package-lock-only` resolution used with Node 24 / npm 11:

| Package | Previous lock | Remediated lock |
| --- | ---: | ---: |
| `brace-expansion` | `5.0.6` | `5.0.9` |
| `brace-expansion` (nested under `filelist`) | `2.1.1` | `2.1.4` |
| `fast-uri` | `3.1.2` | `3.1.5` |
| `nanoid` | `3.3.12` | `3.3.18` |
| `postcss` | `8.5.15` | `8.5.26` |

After the lock-only refresh, `npm audit --package-lock-only --audit-level=high` reported `found 0 vulnerabilities`.

## Permanent guard

`npm run audit:security` is part of the frontend CI and rejects a pull request when npm reports a high or critical vulnerability. Dependency remediation must remain minimal and compatible: do not use `npm audit fix --force` without an explicit reviewed migration.

This audit gate complements, but does not replace, source-code security review, secret scanning, SAST/DAST, browser E2E regression checks, or an institutional security assessment.
