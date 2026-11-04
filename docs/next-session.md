# Next session — Argo CD and the first EKS application deployment

Prepared on 5 November 2026 for the next session. This is a plan; Argo CD installation and application deployment have not been executed.

## Goal

See the Java Orders API call the Node payment simulator on EKS, with Argo CD managing the application resources from Git. Explain every command and configuration through its purpose, component interactions, failure evidence, production tradeoffs, and scenario interview answers.

## Starting point

- Active local checkout: `~/Developer/eks-ai-incident-lab`. The old Documents checkout is retained but cloud-managed files caused repeated local read failures.
- PR #24 contains the app manifests and study notes 18–19. Check its latest required jobs before merging.
- Both images are published in ECR and pinned by digest in the app manifest.
- Last verified runtime: one Ready EKS node and healthy system Pods; `orders-lab` absent. Refresh this evidence at kickoff.
- The app stores orders and idempotency keys in Java process memory. Restarting that process loses them.

## 1. Preflight and merge

Tan follows these commands in the local checkout:

```bash
cd /Users/sayantanchowdhury/Developer/eks-ai-incident-lab
git status -sb
kubectl config current-context
kubectl get nodes
kubectl get pods -A
gh pr checks 24
```

Trunks verifies the current PR and cluster, handles routine Git recovery if needed, and guides the reviewed merge. Explain how merge updates Git without deploying app resources until a reconciler manages them.

## 2. Bootstrap Argo CD

Provide the full commands in chat before Tan runs them. Verify and pin a suitable Argo CD release, use its non-HA installation for this small lab, and check node memory/CPU requests and Pod slots before scheduling the additional components. Explain application controller, repo server, API/UI server and their responsibilities. Keep UI access through local port forwarding for this checkpoint.

Inspect the installation's RBAC scope and explain why bootstrap permissions differ from application runtime permissions. Verify Argo Pods become ready. Any generated login credential is retrieved locally when needed and stays out of Git/study notes.

## 3. Declare the Git-to-cluster relationship

Tan types an Argo CD Application manifest supplied in full in chat. Its source points to this public repository, `main`, and `gitops/apps`; its destination is the lab cluster and `orders-lab`. Place the Application manifest outside the app's watched directory so the first example has no accidental self-management loop.

Use an intentional first sync to observe reconciliation. Explain desired versus live state, Synced versus Healthy, initial Namespace creation, and resource ownership. Terraform owns AWS infrastructure; CI publishes images; Git selects the desired digest; Argo manages the app's Kubernetes resources. Explain automatic sync, self-heal and pruning before enabling those behaviors.

## 4. Watch the app become runnable

Observe Deployment → ReplicaSet → Pod and Service → EndpointSlice, and connect them to study note 19. Verify image pulls, startup/readiness/liveness behavior and actual Pod events. Use:

```bash
kubectl -n orders-lab get deploy,rs,pods,svc
kubectl -n orders-lab get pods -o wide
kubectl -n orders-lab get endpointslices
kubectl -n orders-lab get events --sort-by=.metadata.creationTimestamp
```

Explain how to distinguish Pending, ImagePullBackOff, CrashLoopBackOff, Running-but-unready and a business request failure. A dry run or green PR is not runtime evidence.

## 5. Send an order and examine a controlled failure

After the Deployments are ready, forward the Orders API in one terminal:

```bash
kubectl -n orders-lab port-forward svc/orders-api 8080:8080
```

In a second terminal:

```bash
curl -i http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: first-eks-order' \
  -d '{"sku":"book","quantity":1,"labMode":"ok"}'
```

Verify the returned order and correlated Java/payment logs. Explain the local port-forward path and its limits: it does not by itself prove normal ClusterIP routing or an external Ingress path. Validate internal Service discovery/routing with a suitable diagnostic approach during the live session.

If the healthy request is verified, run the controlled timeout case:

```bash
curl -i http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: first-eks-timeout' \
  -d '{"sku":"book","quantity":1,"labMode":"timeout"}'
```

Explain the expected Java 504 from a 1500 ms timeout versus a 3000 ms simulated payment delay, even while readiness stays green. Trace request IDs and compare infrastructure health with successful business transactions. Discuss uncertain payment outcomes and durable idempotency in a real integration.

## Completion evidence and next checkpoint

Record Argo sync/health state, both Deployment availability results, the successful HTTP order, selected event/log evidence, and the timeout outcome if exercised. Append and push study notes from observed results.

Then convert these same working resources into one small Helm chart. Teach chart structure, values, lint/render validation, image digests, configuration checksums and controlled rollouts. Argo will render the chart and continue managing the application lifecycle. Helm is a separate bounded checkpoint after the first deployment is understood.
