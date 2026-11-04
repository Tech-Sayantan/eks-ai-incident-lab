# 19 — Understand the Kubernetes resources and dry run

## Evidence and learning goal

Tan typed `gitops/apps/orders-lab.yaml` and opened [PR #24](https://github.com/Tech-Sayantan/eks-ai-incident-lab/pull/24). Its four existing checks passed. Trunks reviewed the manifest and independently reproduced all six `created (dry run)` messages with client dry run. The `orders-lab` namespace is still absent; only system Pods are running. This lesson does not claim an application deployment. The existing PR jobs test Terraform, application code, and image builds; they do not yet include a Kubernetes manifest-specific check.

The goal is to explain what each resource makes Kubernetes do, predict its limits, and investigate failures from evidence. Commands in the troubleshooting sections are for **after the first Argo CD deployment**, unless explicitly labelled safe now.

## 1. Client, server, and the control loop

`kubectl` on the Mac is a Kubernetes API **client**. The EKS control-plane endpoint runs the Kubernetes API **server**. kubeconfig selects the cluster endpoint, certificate authority, authentication configuration, context, and optional namespace. Our kubeconfig uses the named AWS profile to obtain an EKS authentication token. AWS identity authentication and permission to perform Kubernetes operations are related but separate checks.

kubectl sends HTTPS API requests; it does not SSH to a worker and run Docker commands. The API server authenticates the caller, authorizes the operation, checks applicable admission rules, and stores accepted state. Controllers then reconcile desired state with observed state. EKS manages the control-plane components and their state store; worker nodes run kubelet and containerd.

For an actual Deployment creation, the Deployment controller manages a ReplicaSet, the ReplicaSet maintains Pods, the scheduler assigns unscheduled Pods to suitable nodes, and each node's kubelet asks the container runtime to run assigned containers. VPC CNI supplies Pod networking in our cluster. These actions are asynchronous. Successful API acceptance is earlier evidence than a successful image pull, Ready Pod, or successful order.

## 2. Exactly what dry run means

Read `kubectl apply --dry-run=client -f gitops/apps/orders-lab.yaml` in pieces:

- `kubectl`: the client program.
- `apply`: calculate the changes needed to manage the declared objects.
- `-f`: read the declarations from the supplied file.
- `--dry-run=client`: calculate and display the intended result without sending modifying create/patch requests to persist these objects.

Client dry run is **not guaranteed offline**. kubectl may contact the API server for discovery, schemas, and current object reads. In the installed v1.36.2 implementation, `apply` obtains existing object state before its client-dry-run branch. Consequently, client dry run can need connectivity and read permissions while still failing to prove create/patch permission or admission acceptance. See the [apply reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_apply/) and [v1.36.2 implementation](https://github.com/kubernetes/kubectl/blob/v0.36.2/pkg/cmd/apply/apply.go).

| Operation | What is evaluated | Are the declared resources persisted? | Does the workload run? |
| --- | --- | --- | --- |
| `apply --dry-run=client` | Client preparation/validation; discovery and existing-object reads may occur | No | No |
| `apply --dry-run=server` | API authentication, authorization, defaults, applicable admission/validation and patch processing | No | No |
| Actual apply or Argo sync | API request plus persistence if accepted | Yes | Controllers attempt to run it; success must be checked |

Server dry run sends the request with `dryRun=All`. The server processes it without storing the resulting object. This is stronger evidence that the current API would accept it. It still does not pull the image, schedule a Pod, execute Java, resolve the payment Service from a Pod, or test an order. A nonexistent image digest can pass both dry-run modes. [API dry run](https://kubernetes.io/docs/reference/using-api/api-concepts/#dry-run)

There is an extra trap in our six-document file: server-dry-running the Namespace does not leave it available for later requests in the file. If the namespace is absent, later namespaced resources may fail with `namespace not found`. Dry run is not a simulated cluster or transaction that retains hypothetical earlier creates. A dry-run request can also be rejected if an admission webhook does not declare compatible side-effect behavior.

`--server-side` is another option with another purpose: it chooses Server-Side Apply and API-side field ownership/merge handling. `--dry-run=server` chooses whether the operation is persisted. They are separate concepts. `apply --server-side --dry-run=server` previews Server-Side Apply. [Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/)

Safe commands now:

```bash
kubectl apply --dry-run=client -f gitops/apps/orders-lab.yaml
kubectl apply --dry-run=client -f gitops/apps/orders-lab.yaml -o yaml
kubectl get namespace orders-lab --ignore-not-found
```

`created (dry run)` describes the proposed create. It does not mean a Namespace or Deployment now exists. A misspelled field may be caught by schema validation; a perfectly well-formed but wrong payment URL can survive and fail at runtime.

## 3. Read the YAML structure before memorizing fields

`---` separates six API objects in one file. `apiVersion: v1` identifies a core API version; `apps/v1` identifies the apps API group/version. Neither is the business application's version. `kind` selects the resource type. `metadata.name` identifies the object, and `metadata.namespace` scopes namespaced objects. `spec` describes desired behavior; Kubernetes later reports observed behavior in `status`. A ConfigMap puts its key/value configuration under `data` instead.

The order in the file is not an application startup dependency graph. The Java Pod might start before payment is ready. Production callers need bounded timeouts, appropriate retry/idempotency behavior, and graceful failure handling.

## 4. Namespace: organization and policy scope

`orders-lab` gives this app its own naming scope. Two namespaces may each contain a Service called `orders-api`. A missing `-n orders-lab` is a common reason a working app appears absent in CLI output. Namespace separation supports team RBAC, quotas, and policy scope, but those controls must be configured. A namespace alone does not block network traffic, reserve node capacity, or create dedicated hardware.

The Namespace object itself is cluster-scoped. Our ConfigMap, Deployments, Services, ReplicaSets and Pods are namespaced. The Node is cluster-scoped. Separate namespaces on our one worker do not protect against that worker failing.

## 5. Deployment, ReplicaSet, Pod, container

A container runs the app process. A Pod is the scheduling unit and network context containing that container. Our Pods each contain one app container. A ReplicaSet maintains the required count of matching Pods. A Deployment manages ReplicaSets and rollout history so we can replace one Pod template with another.

This distinction matters during incidents. If the Java process exits, kubelet can restart its container inside the same Pod, increasing the restart count. If a Pod is deleted or lost and replacement is required, the ReplicaSet creates a different Pod with a new identity and potentially a new IP. Kubernetes keeps the desired workload running; it does not recover application memory.

`replicas: 1` is the desired steady-state count. It is not high availability. `spec.selector.matchLabels` must match `spec.template.metadata.labels`. Deployment metadata labels alone do not select the Pods. Choose selectors carefully: an existing Deployment's selector is immutable. A Service has its own selector, which must also match the Pods.

Changing the image, container environment declaration, or another Pod-template field triggers a Deployment rollout. Changing a Service port or ConfigMap data alone does not change that Pod template.

Our Java Deployment uses `Recreate`: during a Deployment upgrade, old revision Pods terminate before new revision Pods are created. This causes downtime. It is not a global singleton guarantee for every manual deletion or failure, and it does not preserve orders. Our Node Deployment uses the default RollingUpdate strategy; even with one desired replica, a normal rollout can temporarily need capacity for an extra Pod. `revisionHistoryLimit: 2` retains old ReplicaSets for deployment rollback; it is not a database or memory backup. [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

The application stores orders and idempotency keys in Java maps. Any Java container restart loses both. Two replicas would have independent maps, so the same idempotency key could be processed separately. A durable design needs shared storage and correct uniqueness/transaction/idempotency handling. Using an external database does not require switching this web app to a StatefulSet.

## 6. Services: stable discovery over changing Pods

The Node Service's selector is `app: payment-simulator`. Kubernetes tracks matching Pod addresses and readiness in EndpointSlices. The Service provides a stable virtual ClusterIP and DNS name; kube-proxy configures the node's Service routing rules from endpoint information. CoreDNS resolves the name; it does not forward every application request.

Java calls `http://payment-simulator:3000`. The short name works because both apps share `orders-lab`. With the standard cluster DNS suffix, the full name is `payment-simulator.orders-lab.svc.cluster.local`. Another namespace should specify the namespace when addressing this Service.

`port: 3000` is the Service-facing port. `targetPort: http` resolves the named container port `http`, which has number 3000. The application's actual listening socket must agree. `containerPort: 3000` does not start a listener or expose the Mac/node/public internet. The Node source binds `0.0.0.0`; a process listening only on localhost inside its Pod would not accept normal traffic sent to the Pod IP.

Both Services are ClusterIP. This creates no AWS public load balancer and no public domain route. We will add Ingress separately. The Namespace provides no network isolation by itself. [Services](https://kubernetes.io/docs/concepts/services-networking/service/), [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)

## 7. ConfigMap: configuration and the reload trap

`orders-config` holds a non-secret payment URL and timeout. `envFrom` makes its keys container environment variables at startup. Spring reads them through the application's property configuration. This lets us change environment-specific settings without rebuilding the Java image.

Updating the ConfigMap does not update an already running Java process's environment and does not itself trigger a Deployment rollout. New containers can get the new values while old containers still use the old ones. We must arrange a rollout. Later, our Helm chart will use a configuration checksum in Pod-template annotations to make relevant configuration changes trigger one declaratively. ConfigMap volumes have different update behavior, and the application must still reload changed files. [Configuration update behavior](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/)

We keep passwords out of this ConfigMap. Kubernetes Secrets and AWS secret delivery will be a separate lesson; base64 encoding by itself is not encryption.

## 8. Requests, limits, JVM memory and scheduling

Java requests 100m CPU and 256Mi memory, and limits CPU to 1 and memory to 512Mi. Node requests 50m/64Mi and limits 250m/128Mi. Together the app containers request 150m CPU and 320Mi memory. System Pods and future Argo CD components also need node capacity.

1000m equals one CPU core's worth of time; 100m is 0.1. A CPU limit does not pin the container to a particular physical core. Requests influence scheduling and CPU sharing under contention. Memory requests are not unused RAM physically preallocated exclusively to the app. CPU can burst when capacity exists up to its limit; enforced CPU limits can throttle it. Memory limits can result in OOM termination when consumption cannot be kept within the limit. Both app Pods use Burstable QoS because requests and limits are not equal. [Resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

The scheduler uses requested resources, not a prediction of future peak memory. A node can look lightly used yet reject scheduling because requests, affinity, taints, Pod slots, or other constraints do not fit. Our single node also has a Pod-count limit. App limits are initial lab choices, not measured production sizing.

The Java Dockerfile sets `MaxRAMPercentage=70.0`. A 512Mi limit therefore allows an approximately 358Mi heap target, but JVM memory also includes stacks, metaspace, code cache and native allocations. An OOM can occur even if heap metrics appear below their maximum. Inspect termination reasons and memory evidence; exit code 137 alone is not proof of an OOM.

ECR's compressed image size measures artifact storage. It is different from runtime memory and writable disk usage. `kubectl top` also requires a working metrics API, which our current add-on set has not established.

## 9. Probes: three operational decisions

The kubelet performs our HTTP probes against the Pod. Startup gives slow Java initialization time before ordinary readiness/liveness evaluation. With a five-second period and threshold 30, our configured startup allowance is roughly 150 seconds. Readiness controls ordinary Service eligibility; failure leaves the process running. Repeated liveness failure causes the container to restart according to its restart policy. [Probe behavior](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

Do not make a downstream payment outage automatically fail Java liveness: restarting every Java Pod can make the incident worse without repairing payment. Readiness dependency checks need application-specific decisions about whether the app can still serve useful routes.

In our code, both Node probe handlers return UP, and Java's Actuator readiness has no custom payment health indicator. Both Pods can therefore be Ready while order creation fails. The injected payment timeout waits 3000 ms while Java allows 1500 ms, producing a Java 504 even when process-level health stays green. Readiness measures what its implementation actually checks; successful customer transactions need separate monitoring.

## 10. Identity boundaries

`automountServiceAccountToken: false` disables the ordinary automatic Kubernetes API token mount for the app Pod. These web apps do not call the Kubernetes API. This does not stop kubelet from pulling ECR images with node-role permissions, and it does not create a network firewall.

The CI publisher role uploads images. The worker node role pulls them. Kubernetes RBAC/ServiceAccounts govern API access. Workload access to AWS services will need its own scoped mechanism. These are separate identities even though they all participate in the same application delivery path.

## 11. Investigate in order, after deployment

Start with desired and observed state:

```bash
kubectl -n orders-lab get deploy,rs,pods,svc
kubectl -n orders-lab get pods -o wide
kubectl -n orders-lab get events --sort-by=.metadata.creationTimestamp
```

Then replace `POD_NAME` with the failing Pod:

```bash
kubectl -n orders-lab describe pod POD_NAME
kubectl -n orders-lab logs POD_NAME --tail=100
kubectl -n orders-lab logs POD_NAME --previous --tail=100
```

`--previous` reads a prior container instance in that Pod; it does not recover logs from a deleted Pod. Longer retention needs centralized logging.

| Symptom or request | Evidence to collect | Recovery reasoning |
| --- | --- | --- |
| Pending Pod | Scheduling events, node allocatable/requested capacity, Pod slot limits, taints and constraints | Fix the actual constraint; resizing limits alone may not change requests or solve placement. |
| ImagePullBackOff | Describe-Pod events, full image digest, ECR image existence, node role, network | Fix artifact reference, permission, or connectivity before restarting repeatedly. |
| CrashLoopBackOff | Current/previous logs, termination reason, exit code, probe events | Fix the crash or bad probe; backoff describes repeated failed starts, not one root cause. |
| OOMKilled | Last termination reason, JVM/native memory, memory usage history, node pressure | Investigate leak/load/heap and right-size from evidence; raising limits alone may shift the failure. |
| Running 0/1 | Probe path, port, response and startup timing | Running phase does not imply the container is ready for Service traffic. |
| Service unreachable | Pod labels, Service selector/ports, EndpointSlices and readiness | Empty ready backends can explain failure even though the Service object exists. |
| ConfigMap changed, old URL still used | ConfigMap content and running process environment | Roll out relevant Pods through the owning GitOps configuration. |
| All Pods Ready, orders 504 | Correlated request IDs, downstream latency and timeout settings | Treat as a request/dependency incident; do not assume Kubernetes restarting fixes it. |
| New rollout stuck at one replica | New Pod events and surge capacity | RollingUpdate can require an extra slot even for one desired replica. |

For the payment route:

```bash
kubectl -n orders-lab get pods --show-labels
kubectl -n orders-lab get service payment-simulator -o yaml
kubectl -n orders-lab get endpointslices \
  -l kubernetes.io/service-name=payment-simulator -o yaml
kubectl -n orders-lab exec deploy/orders-api -- printenv PAYMENT_BASE_URL
```

After confirming endpoints, test DNS and TCP/HTTP from inside the cluster using a suitable diagnostic environment; application images may not contain curl or nslookup. Compare name resolution, ClusterIP routing, direct Pod reachability and listening ports to isolate the layer. A laptop cannot normally use cluster-only DNS directly.

`kubectl port-forward svc/orders-api 8080:8080` is useful for a local HTTP smoke test. It forwards through the Kubernetes API path to a selected Pod; it does not by itself prove the Service's normal ClusterIP routing or an external load balancer/Ingress path. Verify the customer traffic path separately.

In GitOps, use live inspection for evidence and commit desired-state fixes to Git. Direct live edits or imperative rollback may be overwritten by reconciliation. An old image can also be incompatible with a new database schema, so rollout history alone is not a complete recovery plan.

## 12. Scenario interviews and Helm progression

**"Both Pods are Running but checkout fails. What do you do?"** Establish scope and a failing request, compare Ready conditions and recent changes, inspect the caller's logs/status code, find the same request ID downstream, then test discovery/endpoints/connectivity and timeout behavior. In our timeout fixture, 1500 ms versus 3000 ms explains the 504 while readiness stays green. A payment timeout in a real system can have an uncertain business outcome; use durable provider idempotency and reconciliation rather than blindly issuing a second charge.

**"Why not scale Java to two replicas?"** Our state and idempotency keys are process-local. More Pods do not create shared state. Fix storage and transaction/idempotency design, then use measured scaling and rollout policies.

**"A ConfigMap is correct in Git but the app still uses an old URL. Why?"** We inject environment variables when containers start. Updating the ConfigMap did not replace them. Compare the live environment, arrange a controlled rollout, and design a deterministic configuration-change trigger.

**"A Pod was OOMKilled. Would you increase its memory limit?"** Inspect termination evidence, load, heap/native usage and requests first. A leak, poor sizing, bad JVM setting or node pressure needs a different fix. Verify the node can accommodate any revised request.

**"Dry run succeeded. Is this safe to deploy?"** It is useful preflight evidence with a known scope. Explain whether the client or API evaluated it, then list the remaining runtime checks: scheduling, pull, startup, readiness, routing and business request success.

Helm is planned as a hands-on conversion of these exact working resources into one small chart. `Chart.yaml` describes the chart, `values.yaml` supplies defaults, templates generate ordinary Kubernetes YAML, and environment values select image digests/configuration/resources. We will use linting and local rendering, inspect the generated manifests, and test a configuration checksum-triggered rollout. Values files alone do not create another cluster or environment. [Helm charts](https://docs.helm.sh/docs/topics/charts/)

With Argo CD, Helm renders the chart and Argo manages the resulting resource lifecycle. We will promote a Git change and recover through Git. We will also explain ordinary `helm install`, `upgrade`, `history` and `rollback`, while keeping one active owner for the deployed application. [Argo CD with Helm](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)

The sequence is: understand these resources, run the app through Argo CD, investigate one failure, then convert to Helm and compare the rendered result. The same lesson standard applies to later topics: purpose, exact configuration, runtime behavior, evidence, failure diagnosis, tradeoffs and scenario-based interview answers.
