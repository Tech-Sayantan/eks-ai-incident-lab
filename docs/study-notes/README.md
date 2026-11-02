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
| [10 — EKS pipeline IAM bootstrap apply](10-eks-iam-bootstrap-apply.md) | Saved-plan guard, scoped GitHub roles, state evidence, failure diagnosis |
| [11 — EKS API access for the POC](11-eks-api-access-for-poc.md) | Public endpoint, IAM versus network access, dynamic IPs, production alternatives |
| [12 — Partial EKS apply recovery](12-eks-partial-apply-recovery.md) | Service-linked roles, partial state, exact recovery plan, cost and retry checks |
| [13 — Application foundations](13-application-foundations.md) | Java/Maven, Node.js, Dockerfiles, idempotency, timeouts, probes, failure scenarios |
| [14 — Docker images](14-docker-images.md) | Image stages, build context/cache, image versus runtime size, Kubernetes resources, CI build and troubleshooting |

The lab code is typed and run by Tan. Notes are maintained by Trunks from observed output. No Terraform state, variable values, access keys, or saved plans belong in Git.

Current status: S3 bootstrap, GitHub OIDC, and Terraform format/validate/Trivy CI are verified. `main` requires a PR and passing `check`, `java`, `node`, and `images` jobs. The lab state contains the VPC, two public subnets, and all 13 EKS module resources. After a narrowly scoped IAM repair and guarded retry, EKS 1.36, the single managed node, and all three add-ons are `ACTIVE`; `kubectl` shows the node `Ready` and the system pods running. The live EKS cluster and node incur charges until teardown. The Java Orders API and Node.js payment simulator pass local tests and an HTTP smoke test. [PR #15](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/15) verified application CI and both image builds on GitHub-hosted runners without local Docker Desktop. ECR publishing and Kubernetes deployment are later checkpoints. The Python AI investigator comes later.
