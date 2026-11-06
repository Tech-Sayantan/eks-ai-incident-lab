# Next session — Helm conversion, then GitOps delivery

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
2. The controlled timeout exercise is deferred at Tan's request. Move directly to the Helm conversion in study note 23.
3. Tan creates Chart.yaml and values.yaml, copies the working manifest to templates/resources.yaml and replaces the six blocks supplied in chat. Preserve resource names, namespaces, selectors, probes and image digests.
4. Run Helm lint and template locally; inspect the rendered objects and configuration checksum. This is preparation, not deployment.
5. After Tan returns the results, add Helm validation to PR CI, review the diff, and merge through the existing checks. Change the existing Argo Application source path to the chart with a reviewed, explicit Application update; that Application is not itself currently managed by a parent Argo app.
6. Use the existing manual Argo sync and verify the rollout, Services and an actual order request. A first checksum annotation changes the Java Pod template and causes a Recreate restart; explain the brief outage and loss of in-memory orders before syncing. Keep Argo as the workload lifecycle owner; do not run helm install against these resources.

## Teaching order

Brief purpose → one small practical action → see its result → explain the fields and component interactions → diagnose a controlled failure → production tradeoffs and interview reasoning. Avoid introducing interview questions before the basic tool behavior has been observed.

## Before stopping or resuming

Local port forwards can be stopped with Ctrl+C in their respective terminals. That closes local tunnels; it does not stop EKS or delete the applications. The EKS cluster and worker continue to incur charges until teardown. The Java store is in memory, so restarting Java loses its orders and idempotency keys. Do not infer persistence from a successful rollout or HTTP response.
