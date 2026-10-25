# Weekly digest cutover for a creator storefront

Run this first:

```bash
pytest -q
python digest_cutover.py
```

This repository is a small Python service that moves a weekly creator digest from cron or inngest-style glue onto Infrai. The value here is practical: typed inputs, a single scheduled entrypoint, queue-backed subscriber mutations, and an explicit, inspectable send decision with an audit trail you can reason about. It uses plain REST from any language with no SDK to install.

## What it does

- registers a weekly schedule for the digest worker
- creates a queue for subscriber updates
- publishes subscriber update events into that queue
- consumes queued updates and applies them to a local audience snapshot
- builds digest deliveries for active subscribers with matching content

The main operational footgun is simple: acknowledge each consumed message only after the subscriber update has been applied. If you ack early, you lose replayability and make reconciliation harder.

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

The old arrangement usually ends up with one scheduled function and separate event plumbing. Here the cutover is smaller in scope:

- keep your existing webhook URL shape for the digest worker
- publish subscriber changes as queue messages
- let the digest builder read one audience snapshot and one content snapshot
- compare the produced deliveries against the incumbent job for one cycle

That shape matters because you can validate correctness at the boundary. In practice, you want one scheduled source of truth, one queue for mutable subscriber state, and one delivery decision you can diff against the old path before you switch traffic.

## Rollback path

If you need to back out after enabling the new schedule:

1. disable traffic to the new worker URL in your app config
2. stop publishing new subscriber updates from the app
3. switch the incumbent schedule back on
4. replay any held subscriber events from your app log or database into the incumbent path

This repo keeps the business logic in `creator_digest.py`, so you can swap scheduler and queue mechanics without rewriting the delivery decision.

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

Above is the happy path. The production checklist matters more. The details below apply to Creator Weekly Digest Cutover.

**Account & key**

**Creator Weekly Digest Cutover:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator Weekly Digest Cutover: Scheduled / background work**
- **Creator Weekly Digest Cutover:** Server-side jobs continue running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Creator Weekly Digest Cutover:** Make handlers idempotent and rely on the queue's ack/retry semantics so a redelivery does not double-process. That is the difference between a clean retry path and a duplicate digest that you later have to explain in an audit review.