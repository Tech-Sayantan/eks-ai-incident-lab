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
| [15 — ECR repositories and IAM](15-ecr-repositories-and-iam.md) | Separate Terraform states and roles, scoped ECR permissions, delivery order, failures and interview answers |
| [16 — Guarded ECR apply](16-guarded-ecr-apply.md) | Saved-plan guard, OIDC apply, AWS read-back, PR versus deployment, troubleshooting and interview answers |
| [17 — Image publisher OIDC](17-image-publisher-oidc.md) | Dedicated CI role, trust versus permissions, scoped ECR push, synced-folder failure and interview answers |
| [18 — Image publishing](18-image-publishing.md) | Verified Trivy/OIDC/ECR publication, digests, CI versus promotion, pull permissions and troubleshooting |
| [19 — Kubernetes resources and dry run](19-kubernetes-resources-and-dry-run.md) | Client/API model, dry-run limits, controllers, Services/DNS, configuration, resources, probes, incident diagnosis and Helm progression |
| [20 — Argo CD bootstrap and interviews](20-argocd-bootstrap-and-interview-guide.md) | User-run installation, architecture, RBAC, sync/health, daily operations, troubleshooting and senior scenario answers |
| [21 — First Argo sync and HTTP](21-first-argo-sync-and-http.md) | Verified sync and internal routing, Prune/Dry Run/Force, ownership of health checks, first-order exercise |

The lab code is typed and run by Tan. Notes are maintained by Trunks from observed output. No Terraform state, variable values, access keys, or saved plans belong in Git.

Teaching standard: each topic explains the problem, actual configuration, interacting components, identities, expected evidence, production tradeoffs, failure diagnosis, day-to-day requests and scenario-based interview answers. Prepared commands and verified runtime results are labelled separately.

Current status: S3 bootstrap, GitHub OIDC, and Terraform format/validate/Trivy CI are verified. `main` requires a PR and passing `check`, `java`, `node`, and `images` jobs. The lab state contains the VPC, two public subnets, all 13 EKS module resources, and two ECR repositories. The bootstrap state also owns the dedicated GitHub image publisher role, applied and verified after [PR #21](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/21). EKS 1.36, the single managed node, and all three add-ons are `ACTIVE`; `kubectl` shows the node `Ready` and the system pods running. The live EKS cluster and node incur charges until teardown. The Java Orders API and Node.js payment simulator pass local tests and an HTTP smoke test. [PR #15](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/15) verified application CI and both image builds on GitHub-hosted runners without local Docker Desktop. [ECR apply run #41887631235](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41887631235) created and verified the two repositories. Both app images are now published and verified by digest after [publish run 41903033391](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41903033391). Argo CD is installed, and the first orders-lab sync is verified Synced/Healthy with both app Pods ready and internal health requests returning HTTP 200. The first user-run order is confirmed in both service logs; independent replay and GET return HTTP 200 for the same order, with one payment authorization. The controlled failure exercise, Helm conversion and Python AI investigator are later checkpoints.
