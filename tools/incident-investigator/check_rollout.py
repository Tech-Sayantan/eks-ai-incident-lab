import argparse
import json
from pathlib import Path


def check_rollout(deployment):
    if deployment["kind"] != "Deployment":
        raise ValueError("Expected a Deployment snapshot")

    generation = deployment["metadata"]["generation"]
    desired = deployment["spec"]["replicas"]
    status = deployment.get("status", {})
    observed = status.get("observedGeneration", 0)

    total = status.get("replicas", 0)
    updated = status.get("updatedReplicas", 0)
    available = status.get("availableReplicas", 0)

    numbers = (generation, observed, desired, total, updated, available)
    if any(type(value) is not int or value < 0 for value in numbers):
        raise ValueError("Expected non-negative integer generations and replica counts")

    if generation == 0 or observed != generation:
        return f"UNKNOWN | generation={generation} observed={observed}"

    counts = f"desired={desired} total={total} updated={updated} available={available}"
    if desired == 0 and total == 0:
        return f"SCALED_DOWN | {counts}"

    for condition in status.get("conditions", []):
        if condition.get("type") == "Progressing" and condition.get("status") == "False":
            reason = condition.get("reason", "Progressing=False")
            return f"NOT_READY | {counts} | {reason}"

    if desired > 0 and desired == total == updated == available:
        return f"READY | {counts}"

    return f"NOT_READY | {counts} | replica counts have not converged"


def main():
    parser = argparse.ArgumentParser(description="Check an Orders rollout snapshot")
    parser.add_argument("snapshot", type=Path, help="Deployment JSON file")
    args = parser.parse_args()

    try:
        deployment = json.loads(args.snapshot.read_text(encoding="utf-8"))
        print(check_rollout(deployment))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"UNKNOWN | {error}")


if __name__ == "__main__":
    main()