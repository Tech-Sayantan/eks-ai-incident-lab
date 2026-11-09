"""Discover the payment specialist and request a bounded A2A evidence lookup."""

import re

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers.proto_helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest, TaskState
from a2a.utils.constants import TransportProtocol
from a2a.utils.errors import A2AError

PAYMENT_SKILL = "correlate-payment-request"
PAYMENT_ARTIFACT = "payment-evidence"
PAYMENT_RPC_PATH = "/a2a"
PAYMENT_MODES = {"ok", "decline", "error", "timeout"}
PAYMENT_HTTP_STATUSES = {200, 422, 503}
MAX_EVENTS = 5
REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}")


class PaymentA2AError(RuntimeError):
    """The specialist could not be reached or returned an invalid A2A result."""


async def investigate_payment(base_url: str, request_id: str) -> dict:
    """Send one request ID to the specialist and return its completed artifact."""
    if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
        raise ValueError("Supply a request ID with 1–80 safe characters.")

    base_url = base_url.rstrip("/")
    expected_endpoint = base_url + PAYMENT_RPC_PATH
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False) as http:
            card = await A2ACardResolver(http, base_url).get_agent_card()
            if not any(skill.id == PAYMENT_SKILL for skill in card.skills):
                raise PaymentA2AError("The payment card does not advertise the required skill.")
            if len(card.supported_interfaces) != 1:
                raise PaymentA2AError("The payment card has an unexpected interface list.")
            interface = card.supported_interfaces[0]
            if (
                interface.protocol_binding != TransportProtocol.JSONRPC
                or interface.url != expected_endpoint
            ):
                raise PaymentA2AError("The payment card advertises an unexpected endpoint.")

            agent = await create_client(
                card, ClientConfig(streaming=False, httpx_client=http)
            )
            message = new_data_message(
                {"request_id": request_id},
                media_type="application/json",
                role=Role.ROLE_USER,
            )
            async for reply in agent.send_message(SendMessageRequest(message=message)):
                if not reply.HasField("task"):
                    raise PaymentA2AError("The specialist did not return an A2A task.")
                task = reply.task
                if task.status.state != TaskState.TASK_STATE_COMPLETED:
                    raise PaymentA2AError("The specialist task did not complete.")

                matching = [item for item in task.artifacts if item.name == PAYMENT_ARTIFACT]
                if len(matching) != 1:
                    raise PaymentA2AError("The payment evidence artifact is missing or duplicated.")
                parts = get_data_parts(matching[0].parts)
                if len(parts) != 1:
                    raise PaymentA2AError("The payment evidence artifact has an unexpected format.")
                evidence = _validate_evidence(parts[0], request_id)
                return {"agent": card.name, "task_id": task.id, **evidence}
    except (A2AError, httpx.HTTPError) as error:
        raise PaymentA2AError("The payment specialist request failed.") from error

    raise PaymentA2AError("The specialist returned no result.")


def _validate_evidence(evidence: object, request_id: str) -> dict:
    if not isinstance(evidence, dict) or evidence.get("request_id") != request_id:
        raise PaymentA2AError("Payment evidence has the wrong request ID.")
    status = evidence.get("evidence_status")
    source = evidence.get("source")
    events = evidence.get("events")
    if (
        status not in ("observed", "not_found", "unavailable")
        or source not in ("kubernetes_pod_logs", "local_fixture")
        or not isinstance(events, list)
        or len(events) > MAX_EVENTS
        or (status == "observed") != bool(events)
    ):
        raise PaymentA2AError("The payment evidence fields are invalid.")

    safe_events = []
    for event in events:
        if not isinstance(event, dict):
            raise PaymentA2AError("A payment event has an invalid format.")
        pod, mode, code = event.get("pod"), event.get("mode"), event.get("status")
        if (
            not isinstance(pod, str)
            or not re.fullmatch(r"[a-z0-9.-]{1,253}", pod)
            or not isinstance(mode, str)
            or mode not in PAYMENT_MODES
            or type(code) not in (int, float)
            or code not in PAYMENT_HTTP_STATUSES
        ):
            raise PaymentA2AError("A payment event contains invalid fields.")
        safe_events.append({"pod": pod, "mode": mode, "status": int(code)})

    return {
        "request_id": request_id,
        "evidence_status": status,
        "source": source,
        "events": safe_events,
    }
