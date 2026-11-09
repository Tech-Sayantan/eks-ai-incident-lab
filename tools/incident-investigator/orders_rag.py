import argparse
import os
from functools import lru_cache
from contextlib import closing

from fastembed import TextEmbedding
from openai import OpenAI
from openai.providers import bedrock
from qdrant_client import QdrantClient, models

from rollout_tool_call import get_rollout_report


COLLECTION = "orders_runbooks_bge_small_v1"
RUNBOOKS = [
    {
        "source": "orders-checkout-smoke",
        "text": (
            "After a healthy Orders API rollout, validate the purchase path. "
            "Port-forward the internal Orders API and send POST /orders "
            "with sku, quantity, and a fresh Idempotency-Key header. "
            "A new test order should return HTTP 201 and status CONFIRMED."
        ),
    },
    {
        "source": "orders-image-pull",
        "text": (
            "For ImagePullBackOff, inspect the new Pod events. "
            "If the registry cannot find the manifest, compare the requested "
            "image digest with the artifact published to ECR."
        ),
    },
    {
        "source": "orders-payment-timeout",
        "text": (
            "If the Orders API returns HTTP 504, check the payment simulator log "
            "for the exact X-Request-ID. Compare its recorded mode and status "
            "with the upstream error and verify the payment client timeout. "
            "A simulator event can explain the lab failure when it matches "
            "the request; a healthy rollout alone cannot explain a failed order."
        ),
    },
]


@lru_cache(maxsize=1)
def embedding_model():
    return TextEmbedding(
        model_name="BAAI/bge-small-en-v1.5",
        cache_dir=os.getenv("FASTEMBED_CACHE_PATH", "work/embedding-models"),
        threads=2,
    )



def retrieve(question):
    encoder = embedding_model()
    passages = [runbook["text"] for runbook in RUNBOOKS]
    vectors = list(encoder.passage_embed(passages))
    query_vector = next(encoder.query_embed(question))

    qdrant_url = os.getenv("QDRANT_URL")
    connection = (
        QdrantClient(url=qdrant_url, timeout=5)
        if qdrant_url
        else QdrantClient(path="work/qdrant-runbooks")
    )
    with closing(connection) as db:
        if not db.collection_exists(COLLECTION):
            db.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(
                    size=len(vectors[0]), distance=models.Distance.COSINE
                ),
            )

        points = []
        for index, vector in enumerate(vectors):
            points.append(
                models.PointStruct(
                    id=index + 1,
                    vector=vector.tolist(),
                    payload=RUNBOOKS[index],
                )
            )
        db.upsert(collection_name=COLLECTION, points=points, wait=True)

        matches = db.query_points(
            collection_name=COLLECTION,
            query=query_vector.tolist(),
            limit=1,
            with_payload=True,
        ).points

    if not matches or matches[0].payload is None:
        raise RuntimeError("Qdrant returned no runbook passage.")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--answer", action="store_true")
    args = parser.parse_args()

    hit = retrieve(args.question)
    source = hit.payload["source"]
    passage = hit.payload["text"]
    print(f"Retrieved [{source}] (score {hit.score:.3f})")
    print(passage, flush=True)

    if not args.answer:
        return

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
        input=(
            f"Question: {args.question}\n"
            f"Saved practice rollout report: {get_rollout_report()}\n"
            f"Runbook [{source}]: {passage}\n"
            "Answer from this evidence in two short sentences. "
            "Cite the runbook source in brackets. "
            "If the passage does not answer the question, say so."
        ),
        max_output_tokens=768,
        store=False,
    )
    if response.status != "completed" or not response.output_text:
        raise SystemExit(f"No complete Bedrock answer: {response.status}")
    print("Bedrock:", response.output_text)


if __name__ == "__main__":
    main()