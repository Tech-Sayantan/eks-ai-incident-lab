# 21 — First Argo sync, sync options and application health

## Verified evidence

Tan typed `gitops/argocd/orders-lab.yaml`, registered the Application, and performed the first UI sync. Independent read-back reported sync `Synced`, health `Healthy`, and operation `Succeeded`. Both app Deployments have one available replica; both Pods are Running, 1/1 Ready, with zero restarts. Both Services have EndpointSlice addresses. Read-only HTTP tests from inside the payment Pod to `http://orders-api:8080/actuator/health/readiness` and `http://payment-simulator:3000/health/ready` returned 200 and UP. This exercised internal Service-name discovery and routing for those requests. An actual order transaction is the next user-run check and is not yet claimed here.

## The Sync dialog options

**Prune:** delete resources previously managed by this Application when they are no longer in its desired Git content. Example: remove a managed Service from Git, merge the change, then sync with pruning to remove its live counterpart. This is not a sweep of all unrelated cluster objects. Deleting a Deployment can cascade to its child resources; deleting a namespace has a much wider effect. Review the proposed deletion list and policy before pruning. A one-time prune selection does not by itself enable every future automated prune.

**Dry Run:** preview/validate the proposed sync without persisting its workload changes. It does not start Pods, prove image pulls, or exercise business requests. The dialog operation differs from our earlier kubectl client preview in how it is requested; keep its validation scope distinct from a successful runtime test.

**Force:** allow force-style application/replacement where ordinary apply cannot perform an update. Depending on apply mode and options, this can delete and recreate resources and cause downtime. An immutable Job change is one situation requiring an explicit recreation decision. Force is not a general remedy for bad YAML, missing permissions, wrong images or unhealthy code, and is distinct from Server-Side Apply field-conflict ownership handling. Our first sync left Force off.

The first sync used ordinary apply with no deliberate pruning or forced replacement. [Argo sync options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)

## Who configured the health checks?

There are two layers:

1. **Application endpoints and Kubernetes probes.** Trunks wrote the Node `/health/live` and `/health/ready` handlers. Java's health endpoints come from Spring Boot Actuator, enabled in the app's configuration. Tan typed the supplied probe YAML into the Deployments. The node's kubelet performs those configured HTTP checks against the containers. Startup protects Java initialization, readiness influences Service eligibility, and repeated liveness failures can restart a container.
2. **Argo resource health assessments.** Argo ships built-in assessments for resource types such as Deployments. It reads Kubernetes resource status and rollout/availability information; we did not write a custom Argo health assessment. The Application's green status does not mean Argo called `POST /orders`.

For this lab: endpoint response → kubelet probe result → Pod/Deployment status → Argo's resource-health assessment. The desired/live Git comparison is a separate `Synced` signal. [Argo resource health](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/)

Our Node probe endpoints always return UP, and Java readiness has no custom payment check. An upstream payment timeout can therefore break order creation while all these readiness checks remain green. We will observe this after establishing a successful order.

## Follow along: first order

Keep the Argo UI port forward on 8081 running. In another terminal:

```bash
kubectl -n orders-lab port-forward svc/orders-api 8080:8080
```

Leave that process running. In another terminal:

```bash
curl -i http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: tan-eks-order-01' \
  -H 'X-Request-ID: tan-eks-order-01' \
  -d '{"sku":"book","quantity":1,"labMode":"ok"}'
```

Expected on first creation: HTTP 201 and an order with status CONFIRMED. Repeat the exact same command: expect HTTP 200 with the same order ID while the same Java process retains its state. This application-specific idempotency behavior is separate from Kubernetes health or availability.

```bash
kubectl -n orders-lab logs deploy/orders-api --since=5m | rg 'tan-eks-order-01'
kubectl -n orders-lab logs deploy/payment-simulator --since=5m | rg 'tan-eks-order-01'
```

Find the correlated request ID in both services. On the repeat, the in-memory idempotency record should avoid another payment authorization. A Java restart loses that record; shared durable idempotency remains a later database/application-design exercise.

Port forwarding reaches a selected Java Pod through the Kubernetes API path. Its outgoing payment call still uses the payment Service in the cluster. The laptop-to-Java test does not establish an external Ingress route; that is a separate checkpoint.

If the request fails, keep its HTTP status/body and inspect the corresponding request ID and Pod events before changing configuration. 201/200, correlated payment logs and repeat behavior are the expected evidence to append after Tan completes this step.
