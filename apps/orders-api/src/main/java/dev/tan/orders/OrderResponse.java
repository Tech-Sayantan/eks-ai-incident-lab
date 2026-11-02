package dev.tan.orders;

import java.util.UUID;

public record OrderResponse(UUID id, String sku, int quantity, String status) {
}
