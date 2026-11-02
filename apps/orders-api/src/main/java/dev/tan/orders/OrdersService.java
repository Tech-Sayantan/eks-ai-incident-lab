package dev.tan.orders;

import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicBoolean;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class OrdersService {

    private static final Logger LOGGER = LoggerFactory.getLogger(OrdersService.class);

    private final PaymentGateway paymentGateway;
    private final ConcurrentMap<String, StoredOrder> ordersByKey = new ConcurrentHashMap<>();
    private final ConcurrentMap<UUID, OrderResponse> ordersById = new ConcurrentHashMap<>();

    public OrdersService(PaymentGateway paymentGateway) {
        this.paymentGateway = paymentGateway;
    }

    public CreateResult create(String idempotencyKey, CreateOrderRequest request, String requestId) {
        if (idempotencyKey.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Idempotency-Key cannot be blank");
        }

        AtomicBoolean created = new AtomicBoolean(false);
        StoredOrder stored = ordersByKey.compute(idempotencyKey, (key, existing) -> {
            if (existing != null) {
                if (!existing.request().equals(request)) {
                    throw new ResponseStatusException(
                            HttpStatus.CONFLICT, "Idempotency-Key was used for another order");
                }
                return existing;
            }

            UUID orderId = UUID.randomUUID();
            paymentGateway.authorize(orderId, request.quantity(), request.labMode(), requestId);
            OrderResponse order = new OrderResponse(orderId, request.sku(), request.quantity(), "CONFIRMED");
            ordersById.put(orderId, order);
            created.set(true);
            LOGGER.info("order confirmed requestId={} orderId={}", requestId, orderId);
            return new StoredOrder(request, order);
        });
        return new CreateResult(stored.order(), created.get());
    }

    public OrderResponse find(UUID id) {
        OrderResponse order = ordersById.get(id);
        if (order == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "order not found");
        }
        return order;
    }

    private record StoredOrder(CreateOrderRequest request, OrderResponse order) {
    }

    public record CreateResult(OrderResponse order, boolean created) {
    }
}
