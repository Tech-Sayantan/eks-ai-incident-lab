# Next session — a controlled incident, then Helm

## Completed and verified

- Argo CD v3.6.1 is installed and Tan has used its UI.
- The orders-lab Application is Synced and Healthy after a successful manual sync.
- Both app Pods are Ready with zero restarts at closeout.
- Internal Service-name health requests returned HTTP 200.
- Java confirmed Tan's order and the payment service logged a matching successful authorization.
- Independent repeat POST and GET returned HTTP 200 for the same CONFIRMED order; the correlated payment authorization count remained one.
- Original first-create HTTP 201 was expected but not independently captured. The observed results are in study note 21.

## Next hands-on sequence

1. Refresh the named IAM login if needed. Verify the correct cluster, node, app Pods and Argo Application before changes.
2. Reopen local port forwards only when needed. Reproduce the controlled payment timeout with a fresh idempotency key and request ID.
3. Observe Java returning 504 while Pod readiness and Argo health can remain green. Trace the same request through both logs and explain 1500 ms caller timeout versus 3000 ms simulated downstream delay.
4. Discuss the incident from the evidence: latency, timeout budgets, uncertain downstream outcomes, and durable idempotency. Change one thing at a time and verify the successful request path afterward.
5. Convert the existing working resources into one small Helm chart, typed by Tan from full code provided in chat. Cover Chart.yaml, values.yaml, templates, lint/render validation, pinned digests and configuration checksums.
6. Review the rendered Kubernetes objects before changing the Argo source to the chart. Keep Argo as the workload lifecycle owner. Record the observed rollout and HTTP results.

## Teaching order

Brief purpose → one small practical action → see its result → explain the fields and component interactions → diagnose a controlled failure → production tradeoffs and interview reasoning. Avoid introducing interview questions before the basic tool behavior has been observed.

## Before stopping or resuming

Local port forwards can be stopped with Ctrl+C in their respective terminals. That closes local tunnels; it does not stop EKS or delete the applications. The EKS cluster and worker continue to incur charges until teardown. The Java store is in memory, so restarting Java loses its orders and idempotency keys. Do not infer persistence from a successful rollout or HTTP response.
