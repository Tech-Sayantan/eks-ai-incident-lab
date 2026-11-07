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
3. Tan already created the three chart files and most substitutions. At Tan's explicit request, Trunks completed the Java Pod-template checksum and normalized final newlines. Actual chart lint/render passed; all six resources retain the original semantics except the intentional checksum annotation. A string timeout override changed both configuration and hash.
4. Trunks added Helm 4.2.2 strict lint/render steps to the existing required images CI job. Review the chart and learn the Helm concepts from note 23; run the supplied local commands to observe rendering and values precedence. This is preparation, not deployment.
5. Review the PR and passing checks, then merge through the existing gates. Change the existing Argo Application source path to the chart with a reviewed, explicit Application update; that Application is not itself currently managed by a parent Argo app. Its source path has not been changed in this checkpoint.
6. Use the existing manual Argo sync and verify the rollout, Services and an actual order request. A first checksum annotation changes the Java Pod template and causes a Recreate restart; explain the brief outage and loss of in-memory orders before syncing. Keep Argo as the workload lifecycle owner; do not run helm install against these resources.

## Teaching order

Brief purpose → one small practical action → see its result → explain the fields and component interactions → diagnose a controlled failure → production tradeoffs and interview reasoning. Avoid introducing interview questions before the basic tool behavior has been observed.

## Before stopping or resuming

Local port forwards can be stopped with Ctrl+C in their respective terminals. That closes local tunnels; it does not stop EKS or delete the applications. The EKS cluster and worker continue to incur charges until teardown. The Java store is in memory, so restarting Java loses its orders and idempotency keys. Do not infer persistence from a successful rollout or HTTP response.
