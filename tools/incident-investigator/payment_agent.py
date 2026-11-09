"""A2A payment specialist that correlates a request ID against recent Pod logs."""

import asyncio
import json
import logging
import os

from a2a.helpers.proto_helpers import get_data_parts, new_data_part, new_task
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
    TaskState,
)
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from urllib3.exceptions import HTTPError

from payment_a2a import (
    MAX_EVENTS,
    PAYMENT_ARTIFACT,
    PAYMENT_HTTP_STATUSES,
    PAYMENT_MODES,
    PAYMENT_RPC_PATH,
    PAYMENT_SKILL,
    REQUEST_ID,
)

LOGGER = logging.getLogger(__name__)
MAX_PODS = 3
MAX_LOG_LINES = 200
MAX_LOG_BYTES = 65_536
REQUEST_TIMEOUT = (2, 2)
PAYMENT_CONTAINER = "payment-simulator"


def _matching_events(log: str, pod: str, request_id: str) -> list[dict]:
    events = []
    for line in log.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            not isinstance(record, dict)
            or record.get("event") != "payment.authorize"
            or record.get("requestId") != request_id
        ):
            continue

        mode, status = record.get("mode"), record.get("status")
        if (
            isinstance(mode, str)
            and mode in PAYMENT_MODES
            and type(status) is int
            and status in PAYMENT_HTTP_STATUSES
        ):
            events.append({"pod": pod, "mode": mode, "status": status})
            if len(events) == MAX_EVENTS:
                break
    return events


def _cluster_events(request_id: str) -> tuple[list[dict], bool]:
    namespace = os.environ.get("PAYMENT_NAMESPACE", "orders-lab")
    configuration = client.Configuration()
    config.load_incluster_config(client_configuration=configuration)
    events = []

    with client.ApiClient(configuration) as kube_client:
        api = client.CoreV1Api(kube_client)
        pods = api.list_namespaced_pod(
            namespace,
            label_selector=f"app={PAYMENT_CONTAINER}",
            limit=MAX_PODS,
            _request_timeout=REQUEST_TIMEOUT,
        )
        incomplete = not pods.items or bool(pods.metadata._continue)
        for pod in pods.items:
            try:
                # The SDK can stringify bytes as b'...\n...'. Decode the
                # plain-text response so each JSON log line stays separate.
                with api.read_namespaced_pod_log(
                    pod.metadata.name,
                    namespace,
                    container=PAYMENT_CONTAINER,
                    tail_lines=MAX_LOG_LINES,
                    limit_bytes=MAX_LOG_BYTES,
                    _preload_content=False,
                    _request_timeout=REQUEST_TIMEOUT,
                ) as response:
                    logs = response.read(MAX_LOG_BYTES).decode("utf-8", errors="replace")
            except (ApiException, HTTPError) as error:
                LOGGER.warning("Payment Pod log read failed (%s).", type(error).__name__)
                incomplete = True
                continue

            events.extend(_matching_events(logs, pod.metadata.name, request_id))
            if len(events) >= MAX_EVENTS:
                break
    return events[:MAX_EVENTS], incomplete


def _look_up_payment(request_id: str) -> dict:
    fixture_path = os.environ.get("PAYMENT_LOG_FIXTURE")
    source = "local_fixture" if fixture_path else "kubernetes_pod_logs"
    try:
        if fixture_path:
            with open(fixture_path, encoding="utf-8") as fixture:
                log = fixture.read(MAX_LOG_BYTES)
            events = _matching_events(log, "local-fixture", request_id)
            incomplete = len(log) == MAX_LOG_BYTES
        else:
            events, incomplete = _cluster_events(request_id)
    except (ApiException, ConfigException, HTTPError, OSError, UnicodeError) as error:
        LOGGER.warning("Payment evidence lookup failed (%s).", type(error).__name__)
        events, incomplete = [], True

    if events:
        status = "observed"
    elif incomplete:
        status = "unavailable"
    else:
        status = "not_found"

    return {
        "request_id": request_id,
        "evidence_status": status,
        "source": source,
        "events": events,
    }


class PaymentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task is None:
            await event_queue.enqueue_event(
                new_task(context.task_id, context.context_id, TaskState.TASK_STATE_SUBMITTED)
            )

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        parts = get_data_parts(context.message.parts) if context.message else []
        payload = parts[0] if len(parts) == 1 else None
        request_id = payload.get("request_id") if isinstance(payload, dict) else None
        if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
            message = updater.new_agent_message([Part(text="Supply a valid request_id.")])
            await updater.reject(message)
            return

        await updater.start_work()
        evidence = await asyncio.to_thread(_look_up_payment, request_id)
        await updater.add_artifact(
            [new_data_part(evidence, media_type="application/json")],
            name=PAYMENT_ARTIFACT,
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()


async def health(_request):
    return JSONResponse({"status": "ok"})


public_origin = os.environ.get("PAYMENT_A2A_URL", "http://127.0.0.1:8080").rstrip("/")
card = AgentCard(
    name="Orders Lab Payment Specialist",
    description="Looks up one exact payment request ID in recent simulator logs.",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False, push_notifications=False),
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    supported_interfaces=[
        AgentInterface(
            url=public_origin + PAYMENT_RPC_PATH,
            protocol_binding=TransportProtocol.JSONRPC,
            protocol_version=PROTOCOL_VERSION_CURRENT,
        )
    ],
    skills=[
        AgentSkill(
            id=PAYMENT_SKILL,
            name="Correlate a payment request ID",
            description="Returns a sanitized payment log match, absence, or evidence unavailability.",
            tags=["kubernetes", "payment", "read-only"],
            examples=['{"request_id":"orders-demo-42"}'],
        )
    ],
)
handler = DefaultRequestHandler(
    agent_executor=PaymentExecutor(),
    task_store=InMemoryTaskStore(),
    agent_card=card,
    validate_input_modes=True,
)
app = Starlette(
    routes=[
        Route("/healthz", health),
        *create_agent_card_routes(card),
        *create_jsonrpc_routes(handler, PAYMENT_RPC_PATH),
    ]
)
