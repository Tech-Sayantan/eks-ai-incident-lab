# 13 — Application foundations: Java, Node.js, and Docker

## Verified checkpoint (3 November 2026 IST)

Trunks built the Java Orders API and Node.js payment simulator under `apps/`. Java uses Spring Boot 4.1.2, Java 21 bytecode, the Maven wrapper, JUnit behavior tests, and Maven Checkstyle. `./mvnw verify` passed 3 tests and 0 Checkstyle violations. `npm ci` and `npm test` passed 3 Node tests. A local two-process HTTP smoke test returned 201 for a new order, 200 with the same order ID for an idempotent retry, 422 for a declined payment, 502 for a simulated upstream error, and 504 for a timeout. Both Java health probes returned 200. The three Docker base-image tags resolved, but Docker Desktop was not running, so **container builds and EKS deployment are not yet verified**.

## Business flow and boundaries

```text
client -> Java Orders API -> Node.js payment simulator
             |                     |
        in-memory orders      controlled outcomes
             +---- X-Request-ID ---+

Python incident investigator (later) -> read-only logs, metrics, runbooks
```

The Java API owns orders. The Node service stands in for a flaky downstream payment provider; it does not process real payments. `labMode` is an explicit lab-only way to reproduce a decline, error, or slow response. The later Python service will investigate incidents, not sit in the checkout request path. This gives the three languages distinct roles and a real failure story for interviews.

**Idempotency:** The `Idempotency-Key` header prevents a client retry from authorizing payment twice within one Java process. The same key and changed body returns 409. A failed payment does not store an order. This is an application guarantee for this single-process MVP, **not** a durable, cross-replica guarantee. A production design would persist the key and outcome in a database, handle races and crashes, and clarify the external payment provider's own idempotency contract.

**Timeout and status mapping:** Java waits at most 1500 ms for Node. A payment decline becomes 422, an upstream error becomes 502, and a timeout becomes 504. The request ID is forwarded so the same attempt can be found in both services' logs. A production service would add bounded retries only for safe operations, backoff, metrics, and a circuit breaker where justified; blind retries can duplicate charges.

**Health probes:** Liveness asks whether a container should be restarted; readiness asks whether it should receive traffic. Java uses Spring Actuator probes. Node exposes small health endpoints. Later Kubernetes manifests will connect these endpoints to probes; a green local endpoint alone does not prove a Pod is healthy in EKS.

## Build and Docker concepts

`./mvnw verify` runs Maven's lifecycle through compilation, tests, packaging, and the configured Checkstyle check. The wrapper pins the Maven distribution for teammates and CI. `npm ci` installs the exact versions in `package-lock.json` and is suited to repeatable CI builds; `npm install` is used when intentionally changing dependencies.

The Java Dockerfile has a Maven build stage and a smaller Java runtime stage. The Node Dockerfile installs production dependencies from its lockfile. Both run as a non-root user. `.dockerignore` excludes local build output and dependencies from the build context. We will build and scan the images in the application CI checkpoint; base-tag existence is not a successful image build or security scan.

## Interview and troubleshooting practice

**Q: Why did CI tests pass but Kubernetes could still fail?** Tests verify code behavior; runtime depends on image build, registry pull, environment variables, service DNS, probes, and node capacity. Check the failed layer in order.

**Q: What if the Java Pod restarts?** Its in-memory orders and idempotency keys disappear. That is why the later RDS checkpoint matters. Do not claim persistence or high availability from this MVP.

**Q: Why does a timeout need its own scenario?** A slow downstream can occupy request threads and exhaust resources even when it eventually responds. A finite timeout limits that wait and gives operators a clear 504 signal.

**Common issues:** `mvnw` download failures point to network or Java/Maven setup; Checkstyle failures show the exact file and line; `npm ci` failures often mean the lockfile and package manifest disagree; `502` may mean Node is down or returned an error; `504` means Java did not receive a response before its timeout. Check both services using `X-Request-ID` and the health endpoints.
