# 20 — Argo CD bootstrap, architecture, operations and interview reasoning

## Checkpoint status

**Installation and UI login verified.** All six Argo Deployments and the application-controller StatefulSet report ready instances. All seven Argo Pods are Running, Ready, and have zero restarts at verification. Services are internal ClusterIP Services. Tan confirmed UI login after copying the exact password. No Argo Applications exist yet, and `orders-lab` is absent; the first app deployment remains to be completed.

Pre-install evidence: PR #24 merged as `c58517c`, placing the application manifests on `main`. Trunks verified the named AWS profile as `arn:aws:iam::923988301700:user/eks-lab-admin`, the EKS node as Ready, and four healthy system Pods. The node allows 17 Pods. Kubelet statistics showed 3433 MiB available node memory at that preflight; this was a snapshot, not a capacity guarantee.

The reviewed Argo CD v3.6.1 non-HA install contains six single-replica Deployments and one single-replica StatefulSet. Four system Pods plus seven Argo Pods plus two future app Pods gives 13 steady-state Pods; rollouts may need additional slots. The upstream containers do not set CPU/memory requests or limits. Production sizing must measure actual use and set resource policy; a successful scheduling attempt alone does not establish memory safety.

## How each lesson will work

Every topic starts with a brief purpose and a small hands-on action, then observes its result before expanding into architecture, failure diagnosis, production tradeoffs and interview reasoning. For Argo, first open its UI, connect the app, and observe a sync. The deeper reference material below supports that experience. Supply complete user-typed commands and explain the fields at the point of use. Avoid introducing scenario questions before the tool's basic use is understood.

## Why add a continuous delivery controller?

Our CI already tests the code and publishes scanned images to ECR. An image being available does not select which version an environment should run. That choice belongs in an environment's desired configuration. Argo CD watches that configuration, compares it with Kubernetes, and can synchronize the selected resources.

For this lab, Terraform owns AWS infrastructure and IAM, CI builds/scans/publishes artifacts, Git selects the application image/configuration, and Argo manages the application Kubernetes resources. Later Helm will render the chart into those same kinds of objects. Avoid giving several independent systems conflicting desired state for the same Deployment.

The delivery controller is not on the normal HTTP request path. Java calls the payment Service and its selected Pods; it does not ask Argo to process an order. Kubernetes workload controllers and kubelet still perform their own workload recovery.

## Architecture: explain each running component

| Component | Responsibility | Example incident evidence |
| --- | --- | --- |
| Application controller | Watches Applications, compares desired/live resources, performs sync and assesses health | Application conditions, operation state, controller logs, Kubernetes authorization errors |
| Repo server | Fetches/checks out Git content and generates manifests; later renders Helm | Repo/path/revision errors, Git reachability/authentication, rendering errors, repo-server logs |
| Argo server | UI/API, normal user authentication and Argo authorization | UI/API reachability, TLS/SSO configuration, server logs; its failure alone does not prove the controller stopped |
| Redis | Caches data used by Argo components | Cache connectivity and Argo component errors; cache is not the authoritative application desired state |
| Dex | Supports external identity-provider integration | SSO/identity-provider errors; the lab has not configured enterprise SSO |
| ApplicationSet controller | Generates Applications from declared templates/generators | ApplicationSet status and generator/controller errors; our first single Application does not need a generator |
| Notifications controller | Sends notifications when configured triggers/subscriptions fire | Notification settings, subscriptions, provider credentials and controller logs; installation alone sends nothing |

## Follow along: install and verify the controller platform

Work from the local checkout outside the synced Documents folder:

```bash
cd /Users/sayantanchowdhury/Developer/eks-ai-incident-lab
git status -sb
aws sts get-caller-identity --profile eks-ai-incident-lab
kubectl config current-context
kubectl get nodes
```

Expect account `923988301700`, the `eks-lab-admin` user, context `eks-ai-incident-lab`, and a Ready node. Authentication establishes identity; Kubernetes authorization establishes allowed actions. The preflight confirmed permission for the CRD, ClusterRole and Deployment operations required here.

```bash
kubectl create namespace argocd

kubectl apply --server-side -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.6.1/manifests/install.yaml

kubectl -n argocd wait deployment --all \
  --for=condition=Available --timeout=300s

kubectl -n argocd rollout status \
  statefulset/argocd-application-controller --timeout=300s

kubectl -n argocd get deploy,sts,pods,svc
```

The first command creates the namespace. If a retry says AlreadyExists, inspect the existing namespace/resources and continue appropriately; do not delete it just to repeat the command.

The pinned HTTPS URL selects an exact reviewed release instead of a moving stable branch. The manifest installs CRDs, ConfigMaps, Secrets, RBAC, Services and controller workloads. It gives its components broad cluster access for same-cluster management. This is a lab bootstrap permission choice, not a complete production tenant-security design.

CRDs extend the Kubernetes API with types such as Application and AppProject. A CRD gives the API server the schema; a running Argo controller gives those objects operational behavior. Merely storing an Application object cannot deploy anything if its controller cannot reconcile it.

`--server-side` selects Server-Side Apply and API-side field management. This command is a real write: there is no dry-run flag. Argo's large CRDs can exceed the annotation size used by ordinary client-side apply, so SSA is appropriate. We omit blanket force-conflict behavior for this fresh install; a real ownership conflict should be investigated rather than overridden without review.

`-n argocd` selects the namespace used by the official RoleBinding references. Cluster-scoped objects such as CRDs and ClusterRoles remain cluster-scoped even when the command specifies a namespace.

`kubectl wait` waits for the Deployment availability condition. The separate StatefulSet rollout command checks the application controller's rollout. A timeout ends the wait; it does not uninstall the resources. `kubectl rollout status` in this installed client has no `--all` flag, so the guide uses `wait deployment --all` and an explicit StatefulSet name.

Expected evidence: six Deployments available, one application-controller StatefulSet ready, and all seven Argo Pods reporting ready containers. This establishes the controller installation. It does not establish a configured Application or running Orders API.

The installed local Argo CLI is v2.12.3, substantially older than server v3.6.1. This checkpoint uses kubectl. Align CLI/server versions before teaching commands that rely on that CLI; no password or generated admin secret needs to be printed for this installation check.

## Reading desired state, sync state and health

### First UI login: avoid copying the shell marker

The local `8081:443` port forward was verified against the healthy Argo server. After the UI reported invalid credentials, Trunks tested `admin` with the stored initial password against `/api/v1/session`: HTTP 200, with neither password nor returned token printed or saved. The stored credential is valid. A likely copy issue is the zsh end-of-line `%` marker shown after a command prints text without a trailing newline. Copy the exact credential directly to the Mac clipboard instead:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 --decode | pbcopy
```

On `https://localhost:8081`, enter username `admin` and paste the clipboard value into the password field. This does not change the password. Avoid repeated failed attempts; Argo has failed-login protection. Successful API authentication and a successful UI login are separate observations; Tan subsequently confirmed the UI login succeeded.

An Application declares a source repository/revision/path and a destination cluster/namespace. Our next file will live outside `gitops/apps`, so the app's first watched directory does not include its own bootstrap definition. The public repository needs no Git read credential. Same-cluster deployment needs no separate `argocd cluster add` step.

We will use a dedicated AppProject to allow this source repository, the intended destination and permitted resource kinds. Project rules complement the controller's Kubernetes RBAC; they do not reduce the permissions of its cluster-admin ServiceAccount. Protect who can change AppProjects and Application definitions.

For the first deployment, automated sync, self-heal and pruning stay absent while Tan performs an intentional sync. Manual sync requests the Argo controller to perform the deployment. It is not evidence of an independent reviewer approval by itself.

- **Synced:** Argo's desired/live comparison has converged for the managed resources under its comparison rules.
- **Healthy:** the resources satisfy Argo's health assessment.
- **Successful order:** the actual business request path worked.

Our payment timeout fixture can leave both Deployments healthy while orders return 504. These are three distinct checks, and all should appear in a real delivery verification plan.

## Troubleshoot this installation from evidence

```bash
kubectl -n argocd get pods -o wide
kubectl -n argocd get events --sort-by=.metadata.creationTimestamp
kubectl -n argocd describe pod POD_NAME
kubectl -n argocd logs POD_NAME --tail=100
kubectl -n argocd logs POD_NAME --previous --tail=100
```

Replace POD_NAME with the actual failing Pod. Previous logs require a prior container instance in that Pod; they do not recover logs from deleted Pods. Keep tokens, generated passwords and private repository credentials out of pasted output and public study notes.

| Symptom | First evidence | Reasoned response |
| --- | --- | --- |
| Expired AWS session / Unauthorized | Named profile STS identity, kubeconfig context and token source | Refresh the intended IAM session; a valid AWS identity still needs Kubernetes authorization. |
| Forbidden during install | Denied API verb, resource, scope and authenticated identity | Bootstrap includes cluster-scoped CRDs/RBAC; namespace-only access cannot install everything. |
| SSA conflict or old install exists | Error's field manager/resource, live state, prior install ownership | Decide the intended owner and reconcile; do not begin with force-conflicts or namespace deletion. |
| Pending | Scheduler events, Pod slots, taints, requests and node conditions | Solve the actual placement constraint. With upstream requests unset, actual memory usage still needs observation. |
| ImagePullBackOff | Exact image registry/tag, node connectivity, Pod events | Official Argo images come from their own registries; ECR pull permission alone does not prove those pulls will work. |
| CrashLoopBackOff / OOMKilled | Logs, previous logs, termination reason, node pressure | Diagnose app/config/memory failure; adjust capacity/policy based on evidence. |
| Application later shows comparison error | Conditions, repo URL/path/revision, repo-server logs | Separate Git/render failures from Kubernetes sync failures. |
| Synced but Degraded/Progressing | Deployment/Pod events, probes and readiness | Desired state can match while the workload cannot become available. |

## Day-to-day DevOps requests

"Onboard this service" means wiring an approved repo/path, environment values, deployment identity and resource policy, then verifying health and the real request path. It is more than adding an image to a YAML file.

"Promote release X" means identifying a tested artifact digest, changing the environment desired state, passing approval/check gates, and verifying the selected version in that environment. A generic CI success is not the environment promotion record.

"The UI is down" means checking which Argo component and which failure domain are affected. UI/API failure differs from controller failure, and both differ from an EKS worker outage.

"My config keeps changing back" means inspecting Git, Application policy, field ownership, autoscalers and other controllers. Identify the competing owners before repeatedly editing live resources.

"Team A needs deployment access" means restricting source, destination, resource kinds and human privileges. A permissive project plus cluster-admin controller is not complete team isolation.

## Senior interview scenarios with reasoning

### 1. Argo says Synced and Healthy but checkout returns 504

I establish the affected operation, reproduce it with a request ID and inspect recent changes. Synced establishes desired/live convergence; Healthy establishes configured resource health. Neither automatically exercises an order. I correlate caller/payment logs and check EndpointSlices/readiness and actual latency. In this fixture, Java times out after 1500 ms while payment delays 3000 ms, so readiness can remain green. I fix the evidenced cause, then verify the same transaction path. Increasing timeouts requires latency/concurrency analysis; restarting callers cannot repair a slow provider. A real payment timeout also needs provider idempotency and reconciliation because the provider may finish later.

### 2. A kubectl rollback worked, then the broken version returned

I inspect the Application's actual policy and Git digest. Self-heal is opt-in: it can restore a Git-selected broken image after a live rollback. My durable recovery selects a known compatible digest/configuration in Git, then synchronizes and checks the request path. I assess schema compatibility and data effects before choosing an older binary. A genuine emergency live action needs coordinated break-glass handling and a subsequent Git reconciliation. Argo's built-in rollback is unavailable while automated sync is enabled, so understand the active policy before choosing a recovery mechanism.

### 3. CI publishes automatically; where is production approval?

Publication makes a tested artifact available. Promotion selects the artifact for a particular environment. A production promotion PR can change the environment image digest or Helm values; the required reviewer sees the diff and checks before the watched Git change merges. Then Argo may synchronize automatically. A manual sync is another possible gate with an explicitly designed authorization model. I verify who can change the branch, Application, project and sync policy. Our one-owner lab demonstrates the flow but does not prove an independent reviewer separation of duties.

### 4. Terraform, Helm and Argo all manage the Deployment

I establish one intended owner per resource or managed field. Terraform owns AWS, CI owns artifact publication, Git records desired app configuration, Helm renders manifests and Argo manages their Kubernetes lifecycle. Conflicting independent owners can overwrite each other. Field-level ownership also matters: for example an HPA and a fixed Git replica count can fight. Emergency operational edits must become an auditable desired-state recovery rather than a hidden second configuration source.

### 5. Argo is down: are the apps down? How do you secure it?

I distinguish the failed component from the serving path. An API/UI outage does not prove the application controller stopped. A controller outage may stop deployment and drift correction while already healthy app containers keep serving; Kubernetes still performs its own normal recovery. In this one-node lab, a node failure can stop Argo and both apps together. I check node health, affected namespaces, component availability, repo access and cluster connectivity. Production controls include scoped AppProjects, protected project/Application administration, least-privilege cluster access, identity/RBAC, admission policy and appropriate availability. AppProject restrictions are useful authorization controls, not complete tenant isolation.

## Sources and next evidence

- [Pinned release](https://github.com/argoproj/argo-cd/releases/tag/v3.6.1), [tested Kubernetes versions](https://argo-cd.readthedocs.io/en/stable/operator-manual/tested-kubernetes-versions/)
- [Installation](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/), [getting started](https://argo-cd.readthedocs.io/en/stable/getting_started/), [architecture](https://argo-cd.readthedocs.io/en/stable/operator-manual/architecture/)
- [Projects](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/), [resource health](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/), [automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Sync with kubectl](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-kubectl/), [Argo CD with Helm](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)

After Tan returns installation evidence, append the actual workload state. Next: type a scoped AppProject and Application, perform the first sync, and verify a successful order before the controlled timeout exercise. Helm conversion follows the working app; these same Kubernetes concepts remain underneath the chart.
