import os
from typing import Dict, List

import infrai
from creator_digest import (
    ContentItem,
    Subscriber,
    SubscriberUpdate,
    apply_subscriber_updates,
    build_digest_deliveries,
)

DIGEST_WEBHOOK_URL = os.environ.get("DIGEST_WEBHOOK_URL", "https://example.com/tasks/creator-weekly-digest")
DIGEST_QUEUE_NAME = os.environ.get("DIGEST_QUEUE_NAME", "creator-weekly-digest-subscriber-updates")


def schedule_weekly_digest() -> str:
    job = infrai.cron.create(cron_expr="0 14 * * 1", task=DIGEST_WEBHOOK_URL)
    return str(job.get("job_id", ""))


def create_update_queue() -> None:
    infrai.queue.create(name=DIGEST_QUEUE_NAME)


def publish_subscriber_updates(updates: List[SubscriberUpdate]) -> int:
    for update in updates:
        infrai.queue.publish(
            queue=DIGEST_QUEUE_NAME,
            payload=update.model_dump(),
            idempotency_key=f"subscriber-update:{update.subscriber_id}:{update.status}:{','.join(update.interests)}",
        )
    return len(updates)


def consume_subscriber_updates(max_messages: int = 10, visibility_timeout: int = 30) -> List[SubscriberUpdate]:
    data = infrai.queue.consume(
        queue=DIGEST_QUEUE_NAME,
        max_messages=max_messages,
        visibility_timeout=visibility_timeout,
    )
    messages = data.get("messages") or []
    applied: List[SubscriberUpdate] = []

    for message in messages:
        payload = message.get("payload") or {}
        update = SubscriberUpdate(**payload)
        applied.append(update)
        message_id = message.get("message_id")
        if message_id:
            infrai.queue.ack(queue=DIGEST_QUEUE_NAME, message_id=message_id)

    return applied


def sample_subscribers() -> Dict[str, Subscriber]:
    return {
        "c_001": Subscriber(
            subscriber_id="c_001",
            email="active@example.com",
            creator_id="creator_7",
            status="active",
            interests=["art"],
        ),
        "c_002": Subscriber(
            subscriber_id="c_002",
            email="paused@example.com",
            creator_id="creator_7",
            status="paused",
            interests=["art", "music"],
        ),
    }


def sample_content() -> List[ContentItem]:
    return [
        ContentItem(
            content_id="asset_1",
            creator_id="creator_7",
            title="Starter Kit",
            category="art",
            asset_name="starter-kit.zip",
            asset_url="https://cdn.example.com/starter-kit.zip",
            state="ready",
        ),
        ContentItem(
            content_id="asset_2",
            creator_id="creator_9",
            title="Brush Pack",
            category="art",
            asset_name="brush-pack.zip",
            asset_url="https://cdn.example.com/brush-pack.zip",
            state="ready",
        ),
    ]


def sample_updates() -> List[SubscriberUpdate]:
    return [
        SubscriberUpdate(
            subscriber_id="c_002",
            email="reactivated@example.com",
            creator_id="creator_7",
            status="active",
            interests=["art"],
        ),
        SubscriberUpdate(
            subscriber_id="c_003",
            email="newfan@example.com",
            creator_id="creator_9",
            status="active",
            interests=["art"],
        ),
    ]


def main() -> None:
    job_id = schedule_weekly_digest()
    print(f"scheduled weekly digest job: {job_id}")

    create_update_queue()
    print("created subscriber update queue")

    updates = sample_updates()
    published = publish_subscriber_updates(updates)
    print(f"published {published} subscriber updates")

    consumed = consume_subscriber_updates(max_messages=10, visibility_timeout=30)
    print(f"applied {len(consumed)} queued subscriber updates")

    subscribers = apply_subscriber_updates(sample_subscribers(), consumed)
    deliveries = build_digest_deliveries(list(subscribers.values()), sample_content())

    print(f"prepared {len(deliveries)} digest deliveries")
    for delivery in deliveries:
        print(f"{delivery.subscriber_id} -> {delivery.asset_names}")


if __name__ == "__main__":
    main()
