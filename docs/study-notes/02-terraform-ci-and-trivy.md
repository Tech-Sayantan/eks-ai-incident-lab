# 02 — Terraform CI and Trivy

## Current checkpoint

The first GitHub Actions Terraform run reached all four checks. Formatting, provider initialization without a backend, and Terraform validation passed. Trivy's IaC scan failed with one HIGH finding: `AWS-0132` on the bootstrap state bucket's SSE-S3 (`AES256`) encryption.

**Verified 27 October 2026:** Trunks added the documented inline exception only above the affected encryption resource at Tan's request. Local Terraform validation passed, and a read-only plan returned no changes. [The rerun](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/40397586589) passed every step, including Trivy. The change did not modify any AWS resource.

The workflow is intentionally credential-free. It does not read the live S3 state, calculate an AWS plan, or apply resources. The OIDC smoke role is not used by this workflow.

## What each check proves

| Check | Proves | Does not prove |
|---|---|---|
| `terraform fmt -check` | Code follows Terraform formatting | Configuration validity or security |
| `terraform init -backend=false` | Required provider can be installed using the lockfile | Remote state is reachable |
| `terraform validate` | Terraform syntax and provider schema are valid | AWS permissions or real-world feasibility |
| `trivy config` | Declared IaC matches or violates Trivy policies | Runtime AWS configuration or complete security |
| `terraform plan` (later) | Proposed changes against state and observed resources | That an apply or application deployment succeeded |

## The SSE-S3 finding and decision

Trivy recommends a customer-managed KMS key for greater control over key access, rotation, and auditability. The lab bucket uses S3-managed SSE-S3. AWS confirms SSE-S3 encrypts new S3 objects at no additional encryption charge. Customer-managed SSE-KMS adds KMS charges and requires the backend, human operator, and CI roles to have suitable KMS access.

For this short-lived, single-account POC, we keep SSE-S3 plus the existing private access, public-access blocks, TLS-only policy, versioning, and state locking. An **inline ignore for `AVD-AWS-0132` sits immediately above this bucket-encryption resource**, with a short reason. This scopes the exception to one resource; it does not turn off Trivy or ignore future findings on other resources. A production team with customer-managed-key requirements should implement SSE-KMS and test its key policy and recovery procedure.

This is a risk decision, not a claim that SSE-S3 and customer-managed SSE-KMS provide identical controls.

The passing run emitted a nonblocking notice that `actions/checkout@v4` targets Node.js 20 and was forced to run on Node.js 24. The workflow succeeded; review an action-version update in a later CI maintenance checkpoint rather than mixing it into this encryption decision.

**Next hands-on checkpoint:** write our own compact VPC/network Terraform module. Explain CIDR planning, two Availability Zones, public/private subnets, route tables, Internet Gateway, NAT and its cost tradeoff, and EKS subnet needs before any paid apply.

## Real-world troubleshooting

| Symptom | Cause | Response |
|---|---|---|
| Formatting step fails | A developer did not format HCL | Run `terraform fmt` locally, inspect the diff, push |
| Provider install fails | Network/registry issue or lockfile mismatch | Inspect exact error and pinned versions; retry only if transient |
| Validation passes but plan fails | Missing credentials, permissions, inputs, or existing-resource conflict | Verify identity, variables, provider account guard, and actual AWS state |
| Trivy fails on a real issue | A security control is absent | Fix the resource, rerun, and record the control |
| Trivy finding is outside lab requirements | A deliberate, reviewed tradeoff | Use a resource-scoped exception with rationale, then keep the gate enabled |

## Interview practice

1. **Why run static checks without AWS credentials?** PRs can contain untrusted code; formatting, schema validation, and IaC scanning do not need cloud access.
2. **Why is a Trivy report with exit code zero insufficient as a gate?** It displays findings but still marks the job successful. A blocking severity policy must return a failing exit code.
3. **Would you always ignore a HIGH finding?** No. Investigate the rule, data sensitivity, policy requirements, cost, and compensating controls; record a narrow exception only when justified.
4. **How would KMS change this backend?** Configure a customer-managed key and grant every authorized state reader/writer required KMS actions; test plan, apply, recovery, and cost.

## References

- [Trivy inline misconfiguration ignores](https://trivy.dev/docs/latest/scanner/misconfiguration/config/config/)
- [Amazon S3 default encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html)
- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3)
