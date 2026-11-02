package dev.tan.orders;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class PaymentClient implements PaymentGateway {

    private final HttpClient httpClient;
    private final URI paymentUri;
    private final Duration timeout;

    public PaymentClient(
            @Value("${payment.base-url}") String baseUrl,
            @Value("${payment.timeout-ms}") long timeoutMs) {
        this.timeout = Duration.ofMillis(timeoutMs);
        this.httpClient = HttpClient.newBuilder().connectTimeout(timeout).build();
        this.paymentUri = URI.create(baseUrl).resolve("/payments/authorize");
    }

    @Override
    public void authorize(UUID orderId, int quantity, String labMode, String requestId) {
        String body = "{\"orderId\":\"" + orderId + "\",\"quantity\":" + quantity + "}";
        HttpRequest request = HttpRequest.newBuilder(paymentUri)
                .timeout(timeout)
                .header("Content-Type", "application/json")
                .header("X-Request-ID", requestId)
                .header("X-Lab-Mode", labMode == null ? "ok" : labMode)
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();

        try {
            int status = httpClient.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
            if (status == 200) {
                return;
            }
            if (status == 422) {
                throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "payment declined");
            }
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "payment service returned " + status);
        } catch (HttpTimeoutException exception) {
            throw new ResponseStatusException(HttpStatus.GATEWAY_TIMEOUT, "payment service timed out", exception);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "payment service unavailable", exception);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "payment request interrupted", exception);
        }
    }
}
