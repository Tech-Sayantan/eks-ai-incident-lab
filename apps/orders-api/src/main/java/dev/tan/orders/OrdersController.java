package dev.tan.orders;

import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/orders")
public class OrdersController {

    private final OrdersService ordersService;

    public OrdersController(OrdersService ordersService) {
        this.ordersService = ordersService;
    }

    @PostMapping
    public ResponseEntity<OrderResponse> create(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader(value = "X-Request-ID", required = false) String requestId,
            @Valid @RequestBody CreateOrderRequest request) {
        String resolvedRequestId = requestId == null || requestId.isBlank()
                ? UUID.randomUUID().toString() : requestId;
        OrdersService.CreateResult result = ordersService.create(idempotencyKey, request, resolvedRequestId);
        HttpStatus status = result.created() ? HttpStatus.CREATED : HttpStatus.OK;
        return ResponseEntity.status(status).header("X-Request-ID", resolvedRequestId).body(result.order());
    }

    @GetMapping("/{id}")
    public OrderResponse find(@PathVariable UUID id) {
        return ordersService.find(id);
    }
}
