from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class Subscriber(BaseModel):
    subscriber_id: str
    email: str
    creator_id: str
    status: Literal["active", "paused", "unsubscribed"]
    interests: List[str] = Field(default_factory=list)


class SubscriberUpdate(BaseModel):
    subscriber_id: str
    email: str
    creator_id: str
    status: Literal["active", "paused", "unsubscribed"]
    interests: List[str] = Field(default_factory=list)


class ContentItem(BaseModel):
    content_id: str
    creator_id: str
    title: str
    category: str
    asset_name: str
    asset_url: str
    state: Literal["ready", "draft"]


class DigestDelivery(BaseModel):
    subscriber_id: str
    email: str
    creator_id: str
    asset_names: List[str]
    asset_urls: List[str]


def apply_subscriber_updates(subscribers: Dict[str, Subscriber], updates: List[SubscriberUpdate]) -> Dict[str, Subscriber]:
    updated = dict(subscribers)
    for update in updates:
        updated[update.subscriber_id] = Subscriber(**update.model_dump())
    return updated


def build_digest_deliveries(subscribers: List[Subscriber], content_items: List[ContentItem]) -> List[DigestDelivery]:
    deliveries: List[DigestDelivery] = []

    for subscriber in subscribers:
        if subscriber.status != "active":
            continue

        matched = [
            item for item in content_items
            if item.creator_id == subscriber.creator_id
            and item.state == "ready"
            and item.category in subscriber.interests
        ]

        if not matched:
            continue

        deliveries.append(
            DigestDelivery(
                subscriber_id=subscriber.subscriber_id,
                email=subscriber.email,
                creator_id=subscriber.creator_id,
                asset_names=[item.asset_name for item in matched],
                asset_urls=[item.asset_url for item in matched],
            )
        )

    return deliveries
