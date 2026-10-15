from creator_digest import ContentItem, Subscriber, build_digest_deliveries


def test_weekly_digest_only_sends_ready_matching_assets_to_active_subscribers() -> None:
    subscribers = [
        Subscriber(
            subscriber_id="sub_1",
            email="sub1@example.com",
            creator_id="creator_1",
            status="active",
            interests=["art"],
        ),
        Subscriber(
            subscriber_id="sub_2",
            email="sub2@example.com",
            creator_id="creator_1",
            status="paused",
            interests=["art"],
        ),
    ]

    content = [
        ContentItem(
            content_id="item_ready",
            creator_id="creator_1",
            title="Weekly Wallpaper",
            category="art",
            asset_name="weekly-wallpaper.zip",
            asset_url="https://cdn.example.com/weekly-wallpaper.zip",
            state="ready",
        ),
        ContentItem(
            content_id="item_draft",
            creator_id="creator_1",
            title="Draft Pack",
            category="art",
            asset_name="draft-pack.zip",
            asset_url="https://cdn.example.com/draft-pack.zip",
            state="draft",
        ),
    ]

    deliveries = build_digest_deliveries(subscribers, content)

    assert len(deliveries) == 1
    assert deliveries[0].subscriber_id == "sub_1"
    assert deliveries[0].asset_names == ["weekly-wallpaper.zip"]
    assert deliveries[0].asset_urls == ["https://cdn.example.com/weekly-wallpaper.zip"]
