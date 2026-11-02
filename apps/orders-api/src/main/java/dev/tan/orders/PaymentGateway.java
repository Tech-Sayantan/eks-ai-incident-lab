package dev.tan.orders;

import java.util.UUID;

public interface PaymentGateway {

    void authorize(UUID orderId, int quantity, String labMode, String requestId);
}
