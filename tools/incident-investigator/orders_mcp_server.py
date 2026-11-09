import argparse
import os

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from check_rollout import check_rollout
from rollout_tool_call import get_rollout_report


mcp = MCPServer("orders-investigator")


@mcp.tool()
def orders_rollout() -> str:
    """Read the Orders API Deployment and report rollout readiness."""
    if os.getenv("ORDERS_LIVE_EVIDENCE") != "1":
        return get_rollout_report()

    from kubernetes import client, config

    config.load_incluster_config()
    namespace = os.getenv("ORDERS_NAMESPACE", "orders-lab")
    with client.ApiClient() as api_client:
        deployment = client.AppsV1Api(api_client).read_namespaced_deployment(
            name="orders-api", namespace=namespace, _request_timeout=(3, 5)
        )
        snapshot = api_client.sanitize_for_serialization(deployment)
    return check_rollout(snapshot)


def main():
    parser = argparse.ArgumentParser(description="Serve the Orders rollout tool")
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default="stdio"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    allowed_hosts = [f"127.0.0.1:{args.port}", f"localhost:{args.port}"]
    service_host = os.getenv("ORDERS_MCP_ALLOWED_HOST")
    if service_host:
        allowed_hosts.append(service_host)
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(allowed_hosts=allowed_hosts),
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
