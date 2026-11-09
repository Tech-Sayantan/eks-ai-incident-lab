import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from payment_agent import _cluster_events


class PaymentLogTest(unittest.TestCase):
    def test_decodes_multiline_kubernetes_log_before_matching_request_id(self):
        log = (
            b'{"event":"payment.started"}\n'
            b'{"event":"payment.authorize","requestId":"sample-504","mode":"timeout","status":200}\n'
            b'{"event":"payment.authorize","requestId":"sample-504-extra","mode":"ok","status":200}\n'
        )
        pod = SimpleNamespace(metadata=SimpleNamespace(name="payment-simulator-test"))
        pods = SimpleNamespace(items=[pod], metadata=SimpleNamespace(_continue=None))

        with (
            patch("payment_agent.config.load_incluster_config"),
            patch("payment_agent.client.CoreV1Api") as api_type,
        ):
            api = api_type.return_value
            api.list_namespaced_pod.return_value = pods
            api.read_namespaced_pod_log.return_value = io.BytesIO(log)
            events, incomplete = _cluster_events("sample-504")

        self.assertFalse(incomplete)
        self.assertEqual(events, [
            {"pod": "payment-simulator-test", "mode": "timeout", "status": 200},
        ])
        self.assertIs(api.read_namespaced_pod_log.call_args.kwargs["_preload_content"], False)
