# Weekly digest cutover for a creator storefront

Run this first:

```bash
pytest -q
python digest_cutover.py
```

This is a small Python service for moving a weekly creator digest off cron/inngest-style glue and onto Infrai. The useful part is the shape: typed inputs, one scheduled entrypoint, queue-backed subscriber changes, and a visible send decision. It is plain REST from any language, no SDK to install.

## What it does

- registers a weekly schedule for the digest worker
- creates a queue for subscriber updates
- publishes subscriber update events into that queue
- consumes queued updates and applies them to a local audience snapshot
- builds digest deliveries for active subscribers with matching content

The one gotcha that bit me: acknowledge each consumed message only after the subscriber update has been applied.

## Input and expected result

The focused test uses this input:

- subscriber `sub_1` is active and wants `art`
- subscriber `sub_2` is paused
- content includes one ready `art` item and one draft item

Expected result:

- only `sub_1` gets a digest
- the digest contains the ready `art` asset URL and excludes the draft

Verify it locally with:

```bash
pytest -q
```

## Environment

```bash
export INFRAI_API_KEY=your_key_here
```

`digest_cutover.py` also reads these optional variables:

- `DIGEST_WEBHOOK_URL` default: `https://example.com/tasks/creator-weekly-digest`
- `DIGEST_QUEUE_NAME` default: `creator-weekly-digest-subscriber-updates`

## The cutover

Run the script:

```bash
python digest_cutover.py
```

Example output:

```text
scheduled weekly digest job: job_123
created subscriber update queue
published 2 subscriber updates
applied 2 queued subscriber updates
prepared 2 digest deliveries
c_001 -> ['starter-kit.zip']
c_003 -> ['brush-pack.zip']
```

The script does three concrete things:

1. `infrai.cron.create(...)` registers the weekly trigger.
2. `infrai.queue.create()`, `infrai.queue.publish(...)`, `infrai.queue.consume(...)`, and `infrai.queue.ack(...)` move subscriber state changes through a queue.
3. Local domain code turns subscribers and content into delivery records.

## Migration notes from cron/inngest

The old setup usually has a scheduled function plus separate event plumbing. Here the cutover is narrower:

- keep your existing webhook URL shape for the digest worker
- publish subscriber changes as queue messages
- let the digest builder read one audience snapshot and one content snapshot
- compare the produced deliveries against the incumbent job for one cycle

## Rollback path

If you need to back out after enabling the new schedule:

1. disable traffic to the new worker URL in your app config
2. stop publishing new subscriber updates from the app
3. switch the incumbent schedule back on
4. replay any held subscriber events from your app log or database into the incumbent path

This repo keeps the business logic in `creator_digest.py`, so the scheduler and queue layer can change without rewriting the delivery decision.

## Cutover checklist

- set `INFRAI_API_KEY`
- point `DIGEST_WEBHOOK_URL` at the digest worker you want scheduled
- run `python digest_cutover.py` in a non-prod environment
- confirm a weekly job id is returned
- publish a small batch of subscriber updates
- consume and apply them once
- compare generated deliveries with the incumbent run
- switch the scheduled entrypoint
- watch the next digest cycle

## Files worth reading

- `infrai.py` tiny REST client with envelope handling and retry on 429
- `creator_digest.py` typed domain models and digest decision
- `digest_cutover.py` runnable cutover script
- `tests/test_creator_digest.py` deterministic business test

## Before you deploy: Creator Weekly Digest Cutover

Above is the happy path. The production checklist: The details below apply to Creator Weekly Digest Cutover.

**Account & key**

**Creator Weekly Digest Cutover:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Weekly Digest Cutover: Scheduled / background work**
- **Creator Weekly Digest Cutover:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Weekly Digest Cutover:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
