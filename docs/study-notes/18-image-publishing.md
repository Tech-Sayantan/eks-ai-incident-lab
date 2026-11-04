# 18 — Scanned image publishing to ECR

## Verified evidence

Tan typed `.github/workflows/app-publish.yml`. [PR #23](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/23) passed `check`, `java`, `node`, and `images`, then merged. That main-branch push automatically started [publish run 41903033391](https://github.com/Tech-Sayantan/eks-ai-incident-lab/actions/runs/41903033391), which completed successfully: both images built, both Trivy scans passed, the dedicated OIDC publisher role was assumed, ECR login succeeded, both images were pushed, and their digests were recorded.

Independent ECR API read-back confirmed both images under tag `838f3d9b5f920d90edd73aa7e0e09a652fc13e84-41903033391-1`:

| Repository | Digest | ECR size in bytes |
| --- | --- | --- |
| `eks-ai-incident-lab/orders-api` | `sha256:2bbe7bfbe73f14885f18f18c0e8f4d7aa84f22548953b2b09eee5850c78fc5fd` | 122097338 |
| `eks-ai-incident-lab/payment-simulator` | `sha256:d84619c025f0a89226daf4a4c31e5b46bf6ec0f1012fad76e7e6543242cc5738` | 81444865 |

The EKS node is `Ready` and its IAM role has `AmazonEC2ContainerRegistryPullOnly`. Applications are **not deployed yet**. Publishing proves artifact availability; Pod readiness and HTTP behavior require separate runtime verification.

## How the delivery path works

`PR → tests/build checks → merge main → image build → Trivy → OIDC → ECR push → digest → reviewed GitOps change → Argo CD → Kubernetes`

The publish workflow triggers for main-branch changes in `apps/**` or its own workflow file. A manual main-branch run is also possible. PR code cannot assume this publisher role because its AWS trust policy accepts only the main-branch subject. No local Docker Desktop is involved: GitHub's Linux runner builds the images.

The scan policy blocks **fixable CRITICAL** findings (`severity: CRITICAL`, `ignore-unfixed: true`, `exit-code: 1`). A green scan is evidence for that threshold and the scanner database at run time, not a claim that no vulnerabilities exist. A team chooses severity thresholds, tracks exceptions with expiry dates, and rescans artifacts as vulnerability information changes.

The tag includes commit SHA, run ID, and run attempt so an immutable repository accepts a rerun without overwriting an older tag. A digest identifies exact image content; GitOps will deploy `repository@sha256:...`. Build runners need push permission; EKS nodes need pull permission. The application Pods do not need GitHub's publisher credentials.

ECR reports compressed image storage size. It does not tell us runtime RAM or CPU usage. Kubernetes requests influence scheduling; limits constrain runtime resources. We will measure actual usage and tune later.

## Failures and interview answers

| Symptom | First check |
| --- | --- |
| Trivy stops publication | Read CVE, affected package, fixed version, and base image; update and rescan before considering a documented exception. |
| OIDC assumption denied | Check main branch, audience, subject, and exact publisher role ARN. |
| Push denied | Check repository ARN and publisher upload actions; node pull permissions do not authorize the CI runner. |
| Tag already exists | Use a unique run/attempt tag or deliberately reuse the existing digest. |
| Later `ImagePullBackOff` | Check digest existence, full registry URI, node role, network path, and Pod events. |

**Why publish automatically but deploy through a reviewed Git change?** Image publication produces an artifact. Promotion chooses which artifact an environment should run. Separating those events allows review, rollback, and an auditable deployment history.

**Why pin a digest?** Tags can be reassigned in mutable registries. A digest selects the exact content that was built and scanned.

**Next:** Tan types the two Deployments, two internal Services, a namespace, and application configuration. Argo CD will become their writer in Kubernetes.
