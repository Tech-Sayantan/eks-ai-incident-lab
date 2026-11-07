# 23 — Understand Helm, then package our application

## What actually happened

On 6 November 2026, Tan deferred the timeout exercise and prioritized Helm. Tan created the three chart files and added the value substitutions. At Tan's request, Trunks completed the missing Java Pod-template checksum and final newlines.

The actual repository chart passed local Helm 4.2.2 lint and rendering. Its six resources match the working raw manifests semantically except for the intentional checksum annotation. A local timeout override to the string `2000` changed the rendered ConfigMap and checksum. No new live deployment occurred: the Argo Application still points to `gitops/apps` and uses manual sync.

CI configuration now adds pinned Helm 4.2.2 installation, strict lint and rendering for Kubernetes 1.36.0 to the existing `images` job before its Docker builds. The setup action is pinned to a commit. Thus the existing required `images` check covers Helm too; no branch-protection change or new required check is needed. This describes prepared CI configuration, not a completed remote run, PR merge or deployed chart.

## Start with the team's problem

Our application needs a Java Deployment, Node.js Deployment, two Services, a ConfigMap and a Namespace. Imagine maintaining separate copies for development, staging and production. A new image must be promoted, staging needs a different payment URL, and production eventually needs different resources. Editing each copy independently makes accidental differences easy.

We want one reviewed description of the resource structure, with selected inputs for each environment. Helm combines that structure and those inputs into ordinary Kubernetes YAML. It does not build Java, build its image, make its state persistent or continuously monitor the process.

A typical team request is: “Deploy the tested application to staging with staging configuration, then promote that same image to production.” A chart makes resource structure reusable; values supply configuration. Review, secrets, runtime verification and recovery still require deliberate design.

## Five words to distinguish

| Term | Easy meaning | Our example |
|---|---|---|
| Chart | The application package: templates, defaults and metadata | `gitops/charts/orders-lab` |
| Values | Inputs supplied to the templates | Image digests, replicas, payment timeout |
| Rendered manifests | Ordinary Kubernetes YAML after substitution | `/tmp/orders-lab-rendered.yaml` |
| Release | A named installation managed by Helm's install/upgrade lifecycle | Conceptual example: a separately installed `orders-staging` |
| Revision | A numbered change recorded for that Helm-managed release | Install revision 1, upgrade revision 2 |

The chart is a package; a release is a particular installation. Changing values can create a new release revision without changing the chart package. A rollback is another release-history operation. Our Argo-rendered app uses a different lifecycle, explained below. [Helm usage guide](https://docs.helm.sh/docs/intro/using_helm/)

## Follow one value from source to Pod

Values:

```yaml
orders:
  replicas: 1
```

Template:

```yaml
spec:
  replicas: {{ .Values.orders.replicas }}
```

Rendered result:

```yaml
spec:
  replicas: 1
```

Kubernetes receives the last form. Its Deployment controller maintains the desired Pods. Helm does not sit inside a container evaluating the expression. Creating a value alone does nothing: a template must read it. Editing an unused value cannot change the rendered resources.

## Our files and the different versions

```text
gitops/charts/orders-lab/
├── Chart.yaml
├── values.yaml
└── templates/
    └── resources.yaml
```

`Chart.yaml` describes the package; chart API `v2` is distinct from Kubernetes `apps/v1` and the CLI's Helm 4 version. `values.yaml` holds defaults. `templates/resources.yaml` contains the six resources separated by `---`. A separate file for each resource is organizational, not mandatory. [Chart structure](https://docs.helm.sh/docs/topics/charts/)

| Identifier | What it identifies | Effect in this lab |
|---|---|---|
| Chart `version: 0.1.0` | Chart package version | Does not itself change a Pod template |
| `appVersion: "0.1.0"` | Informational application metadata | Our image field does not read it |
| Image digest | Exact container image content | A different rendered image changes the Pod template |
| Helm release revision | Recorded direct-Helm lifecycle change | Separate from chart/app versions |
| Argo Git revision | Source commit rendered or synced | A documentation-only commit need not change workloads |

A packaging fix need not rebuild Java; a new Java image need not change Deployment structure. Inspect how a particular chart wires its values rather than assuming appVersion selects its image.

## Read the template language

Text inside `{{ ... }}` is evaluated by Helm's Go template engine. The surrounding YAML remains ordinary YAML.

```yaml
image: {{ .Values.orders.image | quote }}
```

Read left to right: find the image, pass it to `quote`, insert a quoted string. A pipe passes a result to the next function. Quote strings; keep Kubernetes integer fields such as replicas numeric.

```yaml
data: {{ toYaml .Values.orders.config | nindent 2 }}
```

`toYaml` serializes the configuration map. `nindent 2` adds a newline and two spaces before its lines, making the entries children of `data`. YAML indentation determines structure, so this affects correctness. Our timeout is quoted in values because ConfigMap data values are strings. [Functions and pipelines](https://docs.helm.sh/docs/chart_template_guide/functions_and_pipelines/)

The leading dot means the current context. At the top level, common built-in objects are:

| Expression | Purpose |
|---|---|
| `.Values.orders.image` | Effective Java image input |
| `.Chart.Name`, `.Chart.Version` | Package metadata, often used in labels |
| `.Release.Name` | Name supplied for rendering/installing |
| `.Release.Namespace` | Target namespace supplied to Helm |
| `.Capabilities.KubeVersion.Version` | Kubernetes version context for compatibility choices |
| `.Files.Get "config/example.txt"` | An ordinary file packaged with the chart |
| `.Template.BasePath` | Current chart's templates path |

Release data existing during rendering does not mean `helm template` installed a release. Our first chart deliberately retains the existing resource names and namespace. [Built-in objects](https://docs.helm.sh/docs/chart_template_guide/builtin_objects/)

Recognize these controls; no need to add them all today:

```yaml
{{- if .Values.ingress.enabled }}
# Render optional Ingress content here.
{{- end }}
```

`if` emits content conditionally. `with` temporarily makes a nested object the current dot. `range` repeats a block for map/list entries. Inside such blocks `.Values` may no longer refer to root values; `$` refers to the root context, as in `$.Release.Name`. Wrong scope commonly produces field-evaluation errors. `{{-` and `-}}` trim whitespace; overusing them can join YAML lines accidentally. [Flow control](https://docs.helm.sh/docs/chart_template_guide/control_structures/)

## Where effective values come from

For common direct CLI usage, increasing precedence is:

```text
chart defaults → supplied values files in order → --set / --set-string
```

For a conflicting key, the rightmost `-f` file wins. Omitted map entries retain lower-priority defaults; lists generally replace the previous list. A parent chart can also supply dependency values. `--set-string` prevents a supplied numeric-looking value from becoming a number. [Values files](https://docs.helm.sh/docs/chart_template_guide/values_files/)

Argo has additional input sources, with this precedence:

```text
parameters > valuesObject > values > valueFiles > chart defaults
```

If editing an environment file seems ineffective, inspect higher-priority inputs and the rendered result. Our current chart uses defaults only; multiple environment files are not required for this MVP. [Argo precedence](https://argo-cd.readthedocs.io/en/latest/user-guide/helm/#helm-value-precedence)

A verified local example is worth remembering: strict lint and rendering can succeed with `--set orders.config.PAYMENT_TIMEOUT_MS=2000`, while the emitted ConfigMap contains a number. That violates ConfigMap's string-data requirement. With `--set-string`, the output remains a string. Lint/render are not a complete Kubernetes schema or admission check. A values schema is one way to reject wrong input types earlier.

## Two deployment lifecycles: learn both, use one

Direct Helm lifecycle:

```text
operator/CI → Helm install or upgrade → API server → controllers → Pods
```

For a separately Helm-installed release, use `helm list`, `helm status`, `helm history`, `helm get values` and `helm get manifest` to inspect it; `helm rollback` selects an earlier revision for that lifecycle.

Our lifecycle:

```text
reviewed Git chart + values → Argo renders with Helm → Argo applies resources
                                                       ↓
                                             Kubernetes controllers → Pods
```

For this application use Git history, Argo diff/operation status and Kubernetes evidence. An Argo-rendered app need not appear as a Helm CLI release. Running `helm install` or `helm upgrade` on the same objects would introduce a competing lifecycle owner. [Argo Helm integration](https://argo-cd.readthedocs.io/en/latest/user-guide/helm/)

Our installed CLI is Helm 4.2.2. `helm upgrade --help` confirms `--rollback-on-failure` and Helm 4 wait strategies. Many Helm 3 examples use different flags, including `--atomic`; check installed help before reusing commands. Waiting/automatic recovery does not establish business correctness or undo external side effects. [Helm 4 overview](https://docs.helm.sh/docs/overview/)

## Why our checksum matters

Java reads `orders-config` through `envFrom`. A process gets those environment variables at startup; a ConfigMap update does not rewrite them in a running process. A replacement Pod receives the new values. Mounted files behave differently and still need application reload support. [Kubernetes configuration updates](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/)

Our Java Pod template now includes:

```yaml
template:
  metadata:
    annotations:
      checksum/config: {{ .Values.orders.config | toJson | sha256sum | quote }}
```

The configured map is serialized as JSON, hashed, then placed in `spec.template.metadata.annotations`. A configuration change changes that hash; after Argo applies the new template, the Deployment controller replaces Pods according to its strategy. Putting the annotation only on top-level Deployment metadata would not provide this trigger.

Helm calculates text locally; rendering does not restart Pods. The hash covers this values map, not arbitrary live ConfigMap edits or external Secrets. It is a change detector, not encryption or a secret watcher.

The first checksum addition changes the Pod template even when configuration values are unchanged. Java currently uses one replica and `Recreate`, so deploying it briefly interrupts the application. Restart loses memory-only orders and idempotency keys. The chart does not solve persistence.

## Migration constraints we deliberately preserve

Keep kinds, names, namespaces, selectors, ports, probes, resource settings and image digests consistent with the working app. This isolates the packaging change from unrelated behavior changes.

This fixed-name chart is for one lab installation. Another release using the same names in the same namespace would collide. `--namespace` does not rewrite explicitly hardcoded `metadata.namespace` fields. Reusable naming can be a later refactor.

Java stays at one replica. Three Java processes would have three independent memory stores. Durable shared state, concurrency and idempotency guarantees must come before claiming safe horizontal scaling.

## Your commands: inspect without deploying

```bash
cd ~/Developer/eks-ai-incident-lab
helm version --short
helm lint --strict gitops/charts/orders-lab
helm template orders-lab gitops/charts/orders-lab \
  --namespace orders-lab --kube-version 1.36.0 \
  > /tmp/orders-lab-rendered.yaml
rg -n 'kind:|name:|image:|replicas:|PAYMENT_|checksum/config' \
  /tmp/orders-lab-rendered.yaml
```

The first `orders-lab` is the rendering release name; the next argument is the chart path. Redirection saves YAML locally. `--kube-version` supplies rendering context; it does not contact that cluster or prove compatibility. Lint should report zero failed charts. An optional icon recommendation is informational.

Try this bounded override:

```bash
helm template orders-lab gitops/charts/orders-lab \
  --namespace orders-lab --kube-version 1.36.0 \
  --set-string orders.config.PAYMENT_TIMEOUT_MS=2000 \
  > /tmp/orders-lab-override.yaml
diff -u /tmp/orders-lab-rendered.yaml /tmp/orders-lab-override.yaml
```

Expect the timeout string and checksum to change. `diff` exit status 1 means differences were found, not failed rendering. Git defaults and live Kubernetes remain unchanged.

## Diagnose the stage that failed

| Stage | Symptoms | Investigation and remedy |
|---|---|---|
| Chart loading/rendering | Missing Chart.yaml, nonexistent values file, nil/field error, YAML parse error | Verify paths/maps/scope and indentation; render with debug and fix source |
| Value selection | Correctly rendered but wrong URL/image | Reproduce deployment inputs; inspect higher-priority overrides and tracked revision |
| API admission | Wrong data type, unsupported field, immutable selector, policy rejection | Read exact resource/field error; fix inputs or plan a compatible migration |
| Scheduling/startup | Pending, image pull failure, missing config, crashing process | Inspect Pod events, references and logs; fix the indicated dependency |
| Application behavior | Ready Pods but failed orders | Trace a real request and downstream behavior; health is not business success |

Useful rendering diagnostics:

```bash
helm lint --strict gitops/charts/orders-lab
helm template orders-lab gitops/charts/orders-lab \
  --namespace orders-lab --debug
```

Inspect the template named in the error and the generated structure. Repeated Argo sync cannot repair invalid templates. Avoid exposing real secrets in debug output. [Helm debugging](https://docs.helm.sh/docs/chart_template_guide/debugging/)

For source-selection issues:

```bash
kubectl -n argocd get application orders-lab -o yaml
```

Check path, revision, Helm inputs, status conditions and manual-sync state. A file existing on your branch does not mean Argo's tracked `main` contains it.

A later optional API check, requiring a valid lab session, is:

```bash
kubectl apply --dry-run=server -f /tmp/orders-lab-rendered.yaml
```

This contacts the API without persisting these resources; it does not run containers and is not our deployment command. Fix an immutable-field error deliberately rather than routinely choosing Force/replacement.

Runtime evidence:

```bash
kubectl -n orders-lab get pods
kubectl -n orders-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n orders-lab describe deployment orders-api
kubectl -n orders-lab logs deploy/orders-api --tail=100
```

Then inspect the particular failing Pod with `kubectl describe pod POD_NAME -n orders-lab`; for a restarted container, inspect `kubectl logs POD_NAME -n orders-lab --previous`.

- `Pending`/FailedScheduling: examine resource requests, node capacity, placement and available Pod slots.
- `ImagePullBackOff`: check exact digest, registry authorization and connectivity using pull events.
- `CreateContainerConfigError`: check referenced ConfigMap/Secret names and namespaces.
- `CrashLoopBackOff`: inspect exit reason, current/previous logs and probe events.
- `OOMKilled`: inspect memory usage, JVM/native-memory needs and limit; choose a justified correction.

A longer timeout does not fix a nonexistent image or a crashing process. Diagnose before increasing limits or waiting longer.

## Requests a DevOps engineer might receive

| Request | Practical response |
|---|---|
| Promote the tested image | Reviewed digest change, render/diff, CI, Argo sync, rollout and order verification |
| Use staging payment configuration | Environment input change; verify precedence, rendered config and process behavior |
| Config changed but application did not | Inspect config input, checksum, Pod creation time and effective behavior |
| Undo bad configuration | Revert intended Git change, sync and verify; consider state/external effects separately |
| Install another instance for a team | Check names, namespace, state and ownership; this chart needs reuse-oriented naming |
| Upgrade a third-party chart | Review new defaults, application changes, Kubernetes support and migration needs |
| Standardize deployment across services | Define useful inputs and validation; avoid a giant chart exposing every possible field |

## Interview questions: explain cause, evidence and tradeoff

**1. Why Helm if Kubernetes accepts YAML?** Kubernetes operates resources; Helm packages and parameterizes their source. In our app, values changes select images/config while common probes and resource structure stay consistent. Explain review of rendered output too. Templates add complexity, so a tiny static deployment may not need Helm immediately.

**2. Chart version, appVersion, image and release revision: what differs?** Package version, informational metadata, selected executable content and direct-Helm operation history are separate. Our template does not read appVersion for image selection; changing it alone cannot deploy new Java code. Check the actual chart's wiring.

**3. What does helm template prove?** It proves rendering succeeded for the selected inputs/context. It does not create an installed release, validate all admission policies, pull images or execute business requests. Describe separate evidence for each stage.

**4. I merged a values change but the application still has the old value. Why?** Check Argo path/revision and manual sync first, then higher-priority inputs. Render with matching inputs. Finally inspect application config loading: an existing process can retain its environment. Separate source, delivery and runtime-loading problems.

**5. Why does a ConfigMap checksum restart the application?** A changed hash changes the Pod template; the controller then replaces Pods when that template is applied. The hash has no independent restart power. In this lab Recreate causes an interruption and memory-only state is lost.

**6. Lint passed but Pods are unhealthy. What next?** Identify the failed stage: Argo generation/admission, scheduling, image pull, missing config, process startup or probes. Follow events and logs. Do not repeat deployment or inflate timeouts without a cause supported by evidence.

**7. How do you roll back under Argo?** Revert the intended chart/values change through Git, inspect the difference, sync and verify rollout plus order behavior. Directly Helm-installed releases use Helm history/rollback instead. Neither method automatically undoes database mutations or a payment.

**8. Argo shows my app but helm list does not. Is something wrong?** Not for this integration: Argo renders with Helm and owns its application lifecycle. Inspect Git revision, Argo operations and Kubernetes. Do not install a competing release over the same objects to make helm list display something.

**9. Can this chart be installed twice with different release names?** Not safely into the same namespace: names are fixed. A reusable chart needs deliberate resource naming, namespace boundaries and state isolation. A different release argument cannot change hardcoded resource names.

**10. Can we scale Java to three replicas now?** The templates can express that number, but each process has an independent order/idempotency store. Different Pods would see different data. Shared durable state and concurrency contracts must precede claiming safe scale-out.

**11. Should database passwords go in values.yaml?** Not as plaintext in this public repository. Values/rendered manifests can leak through Git, logs and release records. Use a deliberate secret-management integration and reference its Secret. Base64 and checksum annotations are not encryption or secret management.

**12. A chart upgrade changes an immutable Deployment selector. How do you fix it?** Compare old/new render and read the precise error. Preserve compatible selectors where possible. If replacement is genuinely needed, plan ownership, traffic and outage effects. Force is not a harmless way to make immutable fields mutable.

## Later concepts to recognize, without expanding today's MVP

**Helpers:** `_helpers.tpl` can hold reusable named templates for labels/names. `include` returns text that can be piped into indentation. Prefix helper names, such as `orders-lab.labels`, to reduce collisions with dependencies. [Named templates](https://docs.helm.sh/docs/chart_template_guide/named_templates/)

**Validation:** `values.schema.json` can enforce input shapes/types before deployment; `required` gives a deliberate error for missing critical input. This would address our numeric-timeout example. Our compact chart currently includes neither a schema nor helpers. [Chart schema](https://docs.helm.sh/docs/topics/charts/)

**Dependencies:** a chart can include other charts. A `Chart.lock` captures resolved dependencies; build can reproduce that selection, while update resolves declared requirements. A database dependency is an operational responsibility, not a free feature. Our chart has no dependencies.

**Hooks:** Jobs can participate in lifecycle phases, but require idempotency, permissions, bounded failure handling and compatible database changes. Helm hooks and Argo lifecycle mapping differ; do not assume an install hook executes exactly once. Our chart adds no hooks. [Helm hooks](https://docs.helm.sh/docs/topics/charts_hooks/)

**OCI distribution:** chart packages and container images are different artifacts, even if an OCI registry can hold both. A versioned chart archive can be published separately from its image. Our Argo source is Git, so no chart registry is required for this checkpoint. [OCI chart distribution](https://docs.helm.sh/docs/topics/registries/)

## Next delivery checkpoint

Review the chart and CI changes through the PR workflow, then perform an explicit reviewed migration of the existing Argo Application to the chart path. This Application is not managed by a parent app: changing its YAML file in Git alone does not update the live Application.

Preserve all six resource identities and inspect the intended checksum difference before manual sync. Explain the first Java restart beforehand. Verify the rollout, Services and an actual order afterward. Record remote CI, merge, Argo synchronization and HTTP evidence separately when each actually occurs.
