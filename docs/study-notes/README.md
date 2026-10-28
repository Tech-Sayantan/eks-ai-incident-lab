# EKS AI Incident Lab — Study Notes

These notes grow after each hands-on checkpoint. They distinguish verified lab results from the production practices discussed for interviews.

| Note | Topics |
|---|---|
| [01 — Terraform bootstrap and GitHub OIDC](01-terraform-bootstrap-and-oidc.md) | State, backend, provider, locking, IAM roles, trust, temporary credentials |
| [02 — Terraform CI and Trivy](02-terraform-ci-and-trivy.md) | GitHub Actions checks, static validation, IaC scanning, finding triage |
| [03 — VPC networking foundations](03-vpc-networking-foundations.md) | Region/AZ scope, routes, security groups versus NACLs, network plan, delivery path |
| [04 — PR, CI, CD and approvals](04-pr-ci-cd-and-approvals.md) | Git commands, checks versus reviews, merge versus deployment, lab and application flows |
| [05 — GitHub OIDC plan role](05-oidc-plan-role.md) | Trust versus permissions, state access, PR-to-apply order, failure diagnosis |

The lab code is typed and run by Tan. Notes are maintained by Trunks from observed output. No Terraform state, variable values, access keys, or saved plans belong in Git.

Current status: S3 bootstrap, GitHub OIDC smoke test, and Terraform format/validate/Trivy CI are verified. The network module's plan shows 8 additions, 0 changes, 0 deletions. Network PR #1 passed CI and was merged into `main` on 28 October 2026. The GitHub Actions plan role has been validated and planned locally (2 additions), but not applied. The lab network has not been applied; no EKS cluster is running yet.
