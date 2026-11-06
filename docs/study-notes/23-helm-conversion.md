# 23 — Package the working application with Helm

## Status and objective

Tan chose to defer the timeout exercise and move directly to Helm on 6 November 2026. The assistant checked a proposed chart in a temporary directory: Helm 4.2.2 lint passed; all six rendered resources matched the current source manifest after excluding the intentional new Java config checksum annotation; overriding PAYMENT_TIMEOUT_MS as a string changed both the ConfigMap value and Java checksum. This validates the proposed conversion, not Tan's future files or a live Helm deployment. No chart implementation files were created in the repository by the assistant.

Tan's checkpoint: create `gitops/charts/orders-lab/Chart.yaml`, `values.yaml` and `templates/resources.yaml`, then lint and render. Keep the existing Argo Application pointed at `gitops/apps` until the chart is reviewed. The Application uses manual sync.

## Why a team uses Helm

Suppose staging needs one replica and production needs three, or a release changes only an image digest. Copying whole manifests makes unrelated configuration drift easier. A chart keeps a common resource structure; values provide selected inputs. Rendering combines both into ordinary Kubernetes YAML. Helm does not make an application highly available or solve persistence by itself.

This first chart intentionally targets the single orders-lab namespace. Resource names and namespace remain fixed to preserve the existing Argo-managed identities. It is not yet a general-purpose chart supporting multiple releases in one namespace. Keep Java at one replica while its order/idempotency store is in memory.

## The files and expressions

- Chart.yaml declares an application chart using chart API v2, name orders-lab and chart version 0.1.0. Chart version describes the package; appVersion is informational and does not select the image.
- values.yaml holds two image references, two replica counts and the Java environment configuration. Images retain the already-published immutable ECR digests.
- templates/resources.yaml begins as a copy of the six working resources. A template file can contain multiple YAML documents separated by `---`; splitting files later is organization, not a requirement for Kubernetes.
- `{{ .Values.orders.replicas }}` substitutes a chart value. The dot refers to the current template context; `.Values` is its values object.
- `{{ .Values.orders.image | quote }}` passes an image string to quote. The pipe passes one function's result into the next function.
- `data:{{ toYaml .Values.orders.config | nindent 2 }}` serializes the configuration map, adds a leading newline, and indents its entries by two spaces beneath data. ConfigMap data values must be strings, so the timeout is quoted in values.yaml.
- `checksum/config: {{ .Values.orders.config | toJson | sha256sum | quote }}` puts a deterministic configuration hash inside the Java Pod template. It is a change detector, not encryption or a secret-storage mechanism.

## Why the checksum belongs in spec.template.metadata.annotations

The Java process gets environment variables at container startup using envFrom. Updating the ConfigMap does not update the environment of an already-running process. A Deployment creates replacement Pods when its Pod template changes. A changed configuration hash changes that template, so a later Argo sync drives the restart.

The annotation must be under spec.template.metadata.annotations. Putting it only on the Deployment's top-level metadata does not change the Pod template and therefore does not trigger this rollout.

The first addition also changes the Pod template even though the configuration values are the same. Java uses Recreate and one replica, so the live migration will briefly interrupt it. Its current in-memory orders/idempotency keys are lost on restart. Explain and observe this before syncing; do not claim zero downtime or persistence.

## Validation and what each step proves

Run from the repository root:

```bash
helm lint gitops/charts/orders-lab
helm template orders-lab gitops/charts/orders-lab \
  --namespace orders-lab > /tmp/orders-lab-rendered.yaml
rg -n 'kind:|name:|image:|replicas:|PAYMENT_|checksum/config' \
  /tmp/orders-lab-rendered.yaml
```

Lint checks chart structure and common issues. An optional icon recommendation is informational. Template executes the templates locally and emits YAML; it does not create Pods or pull images. These steps do not prove API admission, image availability, successful scheduling, correct probes or business behavior.

For a bounded local override demonstration:

```bash
helm template orders-lab gitops/charts/orders-lab \
  --namespace orders-lab \
  --set-string orders.config.PAYMENT_TIMEOUT_MS=2000 \
  > /tmp/orders-lab-override.yaml
diff -u /tmp/orders-lab-rendered.yaml /tmp/orders-lab-override.yaml
```

Expected differences: the timeout string and checksum only; diff exit status 1 means the files differ, not that rendering failed. This changes neither Git values nor the cluster. Do not increase replicas as a demonstration for the in-memory Java service.

## GitOps delivery boundary

Current: Git raw YAML -> Argo -> Kubernetes.

After reviewed migration: Git chart and values -> Argo invokes Helm template -> Kubernetes resources -> Argo applies/reconciles -> Deployment controller manages Pods.

Do not also helm install/upgrade this same application. Argo uses Helm for rendering and owns this lifecycle. A Helm release managed by helm install has different release-history semantics; an Argo-rendered app is not expected to appear as a normal Helm-installed release in helm list.

The existing orders-lab Application was applied directly, not through a parent app. Merely editing its YAML in Git will not update that live Application. After the chart PR/CI is ready, explicitly apply the reviewed Application path change, then manually sync through Argo. Preserve all six resource identities, including Namespace, and inspect the diff before using Prune.

## Daily DevOps requests and diagnosis

| Team request or failure | Reasoning and action |
|---|---|
| Promote a new image | Update its digest in values through PR; CI renders/scans as applicable; review and merge; sync with Argo and verify rollout plus HTTP. appVersion alone does not change a Pod image. |
| ConfigMap changed but app still uses old value | Check whether config is envFrom or a mounted file. For this envFrom app, verify the checksum changed under the Pod template and a new Pod started; inspect rollout and actual behavior. |
| YAML parse error | Render with helm template --debug, inspect the reported template line, quoting and indentation. nindent adds a newline; indent alone does not. |
| Wrong value appears | Inspect default values, any values files, Argo parameters and CLI overrides. Values precedence can explain why an edited default is not effective. |
| ImagePullBackOff after a correct render | Check Pod events, exact ECR digest, node pull permissions and network reachability. Rendering never tests an image pull. |
| Argo still displays raw YAML source | Check the live Application spec.source.path. This Application needs an explicit reviewed update; changing its file in Git alone is insufficient today. |
| Failed rollout after configuration change | Compare rendered old/new values; inspect events, Pod logs and probe failures. Revert the desired configuration through Git, sync and verify recovery. |

## Interview answers with reasoning

**What problem does Helm solve?** It packages Kubernetes resource templates and configurable values so teams can consistently render an application's manifests. Explain which values change between environments and how a reviewed values change becomes an actual rollout. It does not replace Kubernetes controllers.

**Does Argo CD install a Helm release?** In this integration Argo uses Helm to generate manifests and owns synchronization/application lifecycle. Helm CLI release history is not the deployment record for this Argo-managed app; use Git history, Argo operation status and Kubernetes rollout evidence.

**Why did changing a ConfigMap not restart the application?** A ConfigMap update does not itself change a Deployment Pod template. This application reads environment variables at startup, so its process retains old values. A configuration checksum in the Pod template ties a configuration change to replacement Pods.

**Can a successful helm template prove a deployment is safe?** No. It proves local rendering succeeded for those inputs. Admission policies, immutable fields, missing secrets, scheduling capacity, image pulls and application behavior require further checks and runtime evidence.

**Can this service simply scale to three replicas?** The templates can express three replicas, but the application's memory-only order/idempotency store is per process. Different Pods would see different state. Durable shared state and correct concurrency/idempotency contracts must precede claiming safe horizontal scaling.

**How would you migrate existing manifests?** First render with unchanged resource identities, compare semantics and review intentional Pod-template differences. Keep one lifecycle owner, update the live Argo source explicitly, sync in a controlled window and verify rollout/business behavior. Do not delete and recreate the application just to adopt templates.

## Sources

- [Helm charts](https://helm.sh/docs/topics/charts/)
- [Argo CD Helm integration](https://argo-cd.readthedocs.io/en/latest/user-guide/helm/)

Record Tan's actual lint/render output before claiming this checkpoint complete; record the later PR and live Argo migration separately.
