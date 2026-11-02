import express from 'express';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';

const validModes = new Set(['ok', 'decline', 'error', 'timeout']);

export function createApp({ delayMs = 3000 } = {}) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '8kb' }));

  app.get('/health/live', (_request, response) => response.json({ status: 'UP' }));
  app.get('/health/ready', (_request, response) => response.json({ status: 'UP' }));

  app.post('/payments/authorize', async (request, response) => {
    const { orderId, quantity } = request.body ?? {};
    const mode = request.get('X-Lab-Mode') ?? 'ok';
    const requestId = request.get('X-Request-ID') ?? randomUUID();

    if (typeof orderId !== 'string' || !orderId || !Number.isInteger(quantity) || quantity < 1) {
      return response.status(400).json({ code: 'INVALID_PAYMENT_REQUEST' });
    }
    if (!validModes.has(mode)) {
      return response.status(400).json({ code: 'INVALID_LAB_MODE' });
    }

    const result = mode === 'decline' ? 422 : mode === 'error' ? 503 : 200;
    if (mode === 'timeout') {
      await delay(delayMs);
    }
    console.log(JSON.stringify({ event: 'payment.authorize', requestId, orderId, mode, status: result }));

    if (mode === 'decline') {
      return response.status(422).json({ code: 'PAYMENT_DECLINED' });
    }
    if (mode === 'error') {
      return response.status(503).json({ code: 'PAYMENT_PROVIDER_UNAVAILABLE' });
    }
    return response.json({ paymentId: randomUUID(), status: 'AUTHORIZED' });
  });

  return app;
}
