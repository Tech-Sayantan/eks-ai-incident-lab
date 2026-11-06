# 22 — Observe a slow request before explaining the incident

## Status

Prepared for Tan's next hands-on exercise. The controlled timeout has not yet been observed or claimed as completed. Previous verified runtime and first-order results are in note 21. Refresh the named AWS login and live cluster health before this exercise.

## Goal

See one order request fail because payment responds too slowly, then inspect what Kubernetes and Argo report. The fault mode belongs to this single request; it does not change the Deployment or globally break the payment process.

## 1. Reopen the local tunnels

Keep one terminal open for each tunnel that is needed:

```bash
kubectl -n orders-lab port-forward svc/orders-api 8080:8080
```

To observe the Argo UI too, use another terminal:

```bash
kubectl -n argocd port-forward svc/argocd-server 8081:443
```

The first mapping exposes the selected Java Pod locally; Java's outgoing payment call still uses the in-cluster payment Service. The second mapping exposes only local access to the Argo UI.

## 2. Send this request once

```bash
curl -i --max-time 10 \
  -w '\nHTTP %{http_code} | total %{time_total}s\n' \
  http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: tan-timeout-20261106-01' \
  -H 'X-Request-ID: tan-timeout-20261106-01' \
  -d '{"sku":"book","quantity":1,"labMode":"timeout"}'
```

Expected, not yet verified: HTTP 504 after approximately the caller's 1.5-second timeout plus request overhead. curl's own 10-second maximum is separate from the Java application's 1500 ms downstream timeout.

## 3. Observe before changing anything

```bash
kubectl -n orders-lab get pods
kubectl -n argocd get application orders-lab
kubectl -n orders-lab logs deploy/orders-api --since=10m \
  | rg 'tan-timeout-20261106-01|payment service timed out|504'
kubectl -n orders-lab logs deploy/payment-simulator --since=10m \
  | rg 'tan-timeout-20261106-01'
```

The Node event is written after its simulated 3-second wait, so it can appear after Java has already returned 504. The Java code currently logs confirmed orders, not a dedicated structured event for each failed payment call; no matching Java application log is therefore possible evidence of a logging gap, not proof that Java never received the request. The curl status/body, Node request ID and Pod state together provide the evidence.

## Explain after observing

Java waits up to 1500 ms for payment. The timeout fixture delays payment for 3000 ms. The Java client maps its timeout to HTTP 504. This response comes from the application code; the current route has no Ingress or external load balancer generating this error.

Pod health can stay green because these probes check process-level health and do not exercise an order transaction. Argo's desired/live comparison can remain Synced because no manifest changed. Health, configuration convergence and business-request success are distinct signals.

The payment log's `status: 200` describes its configured successful branch after the delay. It does not prove Java received that response before its deadline. In a real provider integration, a timeout can leave an uncertain business outcome. Provider-side idempotency, durable request state and reconciliation prevent blindly issuing a second charge. The current in-memory lab implementation does not establish those production guarantees.

Use a fresh key and `labMode: ok` for a subsequent normal control request. Because the fault is per request, this demonstrates continued normal operation; it is not evidence that a persistent outage or bad deployment was repaired. Avoid blind retries of a timed-out real payment.

Record the actual HTTP response/timing, Pod readiness/restarts, Argo state and correlated log evidence after Tan runs the exercise. Then convert the same working Kubernetes resources into Helm, preserving their ownership and inspecting rendered YAML before deployment.
