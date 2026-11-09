import asyncio
import json
from pathlib import Path

from openai import OpenAI
from openai.providers import bedrock

from check_rollout import check_rollout
from orders_mcp_client import fetch_rollout_report


MODEL = "openai.gpt-oss-20b"
ROLLOUT_TOOL = {
    "type": "function",
    "name": "get_rollout_report",
    "description": "Check the saved Orders API Deployment practice snapshot.",
    "parameters": {
        "type": "object",
        "properties": {
            "snapshot": {"type": "string", "enum": ["orders-api-practice"]},
        },
        "required": ["snapshot"],
        "additionalProperties": False,
    },
    "strict": True,
}


def get_rollout_report():
    path = Path(__file__).with_name("fixtures") / "healthy.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return check_rollout(snapshot)

def main():
    client = OpenAI(
        provider=bedrock(
            profile="eks-ai-incident-lab",
            region="ap-south-1",
            base_url="https://bedrock-mantle.ap-south-1.api.aws/v1",
        ),
        timeout=30.0,
        max_retries=0,
    )
    question = {
        "role": "user",
        "content": (
            "What does our saved Orders API rollout snapshot show? "
            "Call get_rollout_report for orders-api-practice, then explain it in one sentence. "
            "Describe only what the saved snapshot shows."
        ),
    }

    first = client.responses.create(
        model=MODEL,
        input=[question],
        tools=[ROLLOUT_TOOL],
        tool_choice="auto",
        parallel_tool_calls=False,
        max_output_tokens=768,
        store=False,
    )

    calls = [item for item in first.output if item.type == "function_call"]
    if first.status != "completed" or len(calls) != 1:
        raise SystemExit(
            f"Expected one tool request. Bedrock status: {first.status}; "
            f"error: {first.error}"
        )

    call = calls[0]
    args = json.loads(call.arguments)
    if call.name != "get_rollout_report" or args != {"snapshot": "orders-api-practice"}:
        raise SystemExit(f"Unexpected tool request: {call.name} {call.arguments}")

    print(f"1. Bedrock requested: {call.name} {call.arguments}", flush=True)
    report = asyncio.run(fetch_rollout_report())
    print("2. MCP returned:", report, flush=True)

    tool_result = {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": report,
    }
    final = client.responses.create(
        model=MODEL,
        input=[question, *first.output, tool_result],
        max_output_tokens=768,
        store=False,
    )
    if final.status != "completed" or not final.output_text:
        raise SystemExit(f"No complete answer. Bedrock status: {final.status}")

    print("3. Bedrock answered:", final.output_text)


if __name__ == "__main__":
    main()
