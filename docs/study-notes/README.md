# EKS AI Incident Lab — Study Notes

These notes grow after each hands-on checkpoint. They distinguish verified lab results from the production practices discussed for interviews.

| Note | Topics |
|---|---|
| [01 — Terraform bootstrap and GitHub OIDC](01-terraform-bootstrap-and-oidc.md) | State, backend, provider, locking, IAM roles, trust, temporary credentials |
| [02 — Terraform CI and Trivy](02-terraform-ci-and-trivy.md) | GitHub Actions checks, static validation, IaC scanning, finding triage |
| [03 — VPC networking foundations](03-vpc-networking-foundations.md) | Region/AZ scope, routes, security groups versus NACLs, network plan, delivery path |
| [04 — PR, CI, CD and approvals](04-pr-ci-cd-and-approvals.md) | Git commands, checks versus reviews, merge versus deployment, lab and application flows |
| [05 — GitHub OIDC plan role](05-oidc-plan-role.md) | Trust versus permissions, state access, PR-to-apply order, failure diagnosis |
| [06 — First AWS network plan and Git](06-network-cloud-plan-and-git.md) | Verified cloud plan, staging, conflicts, cherry-pick, next apply checkpoint |
| [07 — Protected PR gate and network apply role](07-apply-role-and-merge-gates.md) | PR checks, reviews, merge, deployment gate, applied IAM role |
| [08 — Network apply and verification](08-network-apply-and-verification.md) | Manual deployment, saved-plan guard, VPC/subnet/route verification, failure diagnosis |
| [09 — EKS add-ons](09-eks-addons.md) | VPC CNI, kube-proxy, CoreDNS, managed ownership, dependency order, troubleshooting |

The lab code is typed and run by Tan. Notes are maintained by Trunks from observed output. No Terraform state, variable values, access keys, or saved plans belong in Git.

Current status: S3 bootstrap, GitHub OIDC, and Terraform format/validate/Trivy CI are verified. `main` requires a PR and the passing `check` job. The network apply IAM role is live. PR #7 merged and its manual apply workflow succeeded; AWS read-back confirmed the lab VPC, two public subnets across AZs, and an Internet Gateway route. Terraform state contains the eight managed network resources. No EKS cluster has been deployed in this checkpoint.
