package dev.tan.orders;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record CreateOrderRequest(
        @NotBlank String sku,
        @Min(1) int quantity,
        @Pattern(regexp = "ok|decline|error|timeout") String labMode) {
}
