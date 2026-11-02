package dev.tan.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class OrdersServiceTest {

    @Test
    void retryWithSameKeyReturnsSameOrderWithoutSecondPayment() {
        AtomicInteger paymentCalls = new AtomicInteger();
        PaymentGateway gateway = (id, quantity, mode, requestId) -> paymentCalls.incrementAndGet();
        OrdersService service = new OrdersService(gateway);
        CreateOrderRequest request = new CreateOrderRequest("book", 2, "ok");

        OrdersService.CreateResult first = service.create("checkout-1", request, "request-1");
        OrdersService.CreateResult retry = service.create("checkout-1", request, "request-2");

        assertTrue(first.created());
        assertFalse(retry.created());
        assertEquals(first.order().id(), retry.order().id());
        assertEquals(1, paymentCalls.get());
        assertEquals(first.order(), service.find(first.order().id()));
    }

    @Test
    void reusedKeyWithDifferentPayloadIsRejected() {
        OrdersService service = new OrdersService((id, quantity, mode, requestId) -> { });
        service.create("checkout-2", new CreateOrderRequest("book", 1, "ok"), "request-1");

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> service.create("checkout-2", new CreateOrderRequest("pen", 1, "ok"), "request-2"));

        assertEquals(HttpStatus.CONFLICT, exception.getStatusCode());
    }

    @Test
    void failedPaymentDoesNotCreateOrder() {
        UUID[] attemptedId = new UUID[1];
        PaymentGateway gateway = (id, quantity, mode, requestId) -> {
            attemptedId[0] = id;
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "payment unavailable");
        };
        OrdersService service = new OrdersService(gateway);

        assertThrows(ResponseStatusException.class,
                () -> service.create("checkout-3", new CreateOrderRequest("book", 1, "error"), "request-1"));
        ResponseStatusException missing = assertThrows(ResponseStatusException.class,
                () -> service.find(attemptedId[0]));
        assertEquals(HttpStatus.NOT_FOUND, missing.getStatusCode());
    }
}
