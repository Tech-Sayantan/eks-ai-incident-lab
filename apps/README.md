# Orders incident lab applications

The Java Orders API calls the Node.js payment simulator when an order is created. The optional `labMode` field lets us reproduce a decline, upstream error, or timeout for CI, Kubernetes, observability, and AI incident exercises. No real payments are processed.

| Endpoint | Purpose |
|---|---|
| `POST /orders` (Java, port 8080) | Create an order after payment authorization; requires `Idempotency-Key` header |
| `GET /orders/{id}` (Java) | Read an order stored in this process |
| `GET /actuator/health/liveness` and `/readiness` (Java) | Kubernetes probes |
| `POST /payments/authorize` (Node.js, port 3000) | Simulated downstream payment authorization |
| `GET /health/live` and `/health/ready` (Node.js) | Kubernetes probes |

Run the simulator with `cd apps/payment-simulator && npm ci && npm test && npm start`. In another terminal, run the Java API with `cd apps/orders-api && ./mvnw verify && ./mvnw spring-boot:run`. Java 21 or later is required. The Java API uses `PAYMENT_BASE_URL=http://localhost:3000` and a 1500 ms payment timeout by default.

```bash
curl -i http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"sku":"book","quantity":1,"labMode":"ok"}'
```

Repeat with the same idempotency key and body: the API returns the same order and does not call payment again. Use a new key with `labMode` set to `decline`, `error`, or `timeout` to see 422, 502, or 504 respectively. The Java service forwards `X-Request-ID` to Node.js for log correlation.

Orders and idempotency keys are in memory. They disappear on restart and are not shared across replicas. We will use RDS later to practise durable state and stronger idempotency. The failure modes and public API are lab-only conveniences; a production payment integration needs authentication, durable transactions, and stricter access controls.
