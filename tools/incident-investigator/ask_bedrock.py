import json
from pathlib import Path

from openai import OpenAI
from openai.providers import bedrock

from check_rollout import check_rollout


def main():
    snapshot_path = Path(__file__).with_name("fixtures") / "healthy.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    rollout_report = check_rollout(snapshot)
    print("Python report:", rollout_report, flush=True)

    prompt = (
        f"Rollout report from a saved practice snapshot: {rollout_report}\n"
        "Lab context: Orders API is internal. Its public Ingress and load "
        "balancer were removed. We can reach it via kubectl port-forward.\n"
        "Explain what the saved snapshot shows in one sentence. Then give "
        "one business-level check using POST /orders. Use only these facts."
    )

    client = OpenAI(
        provider=bedrock(
            profile="eks-ai-incident-lab",
            region="ap-south-1",
            base_url="https://bedrock-mantle.ap-south-1.api.aws/v1",
        ),
        timeout=30.0,
        max_retries=0,
    )
    response = client.responses.create(
        model="openai.gpt-oss-20b",
        input=prompt,
        max_output_tokens=768,
        store=False,
    )

    if response.status != "completed" or not response.output_text:
        raise SystemExit(f"No complete answer from Bedrock: {response.status}")

    print("Bedrock reply:", response.output_text)


if __name__ == "__main__":
    main()
