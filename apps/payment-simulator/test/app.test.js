import assert from 'node:assert/strict';
import { once } from 'node:events';
import test from 'node:test';
import { createApp } from '../src/app.js';

async function withServer(run) {
  const server = createApp({ delayMs: 20 }).listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    await run(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

async function authorize(baseUrl, mode, body = { orderId: 'order-1', quantity: 2 }) {
  return fetch(`${baseUrl}/payments/authorize`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-lab-mode': mode },
    body: JSON.stringify(body),
  });
}

test('authorizes a valid payment', async () => {
  await withServer(async (baseUrl) => {
    const response = await authorize(baseUrl, 'ok');
    assert.equal(response.status, 200);
    assert.equal((await response.json()).status, 'AUTHORIZED');
  });
});

test('exposes a controlled downstream failure', async () => {
  await withServer(async (baseUrl) => {
    const response = await authorize(baseUrl, 'error');
    assert.equal(response.status, 503);
    assert.equal((await response.json()).code, 'PAYMENT_PROVIDER_UNAVAILABLE');
  });
});

test('rejects malformed payment requests', async () => {
  await withServer(async (baseUrl) => {
    const response = await authorize(baseUrl, 'ok', { orderId: 'order-2', quantity: 0 });
    assert.equal(response.status, 400);
  });
});
