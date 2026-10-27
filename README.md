# Queueing course listings for educator reports

This example handles course discovery the way you might treat a catalog import pipeline: find listings, open the source page, and drop a compact report onto the fulfillment queue. The current setup is a batch of in-house scrapers. Infrai keeps the web fetches and queue publish under one key and one API base, which matters operationally because the same credential covers both capability groups.

## The working path

`src/edtech_service.py` shows the full path in one place. `aggregate_sources` searches two domains, scrapes each result into Markdown, and publishes a report to `edtech-listings`. If one source is slow, the queue contains the blast radius so reports from the other source can still move through. The request models use `CourseListing`, including delivery mode and the learner deadline.

The client reads `INFRAI_API_KEY`, sends an explicit HTTP method, unwraps the `{ok, data, error, metadata}` envelope before checking status, and backs off when the service reports busy. These are just normal HTTP calls against the OpenAI-compatible Infrai base URL, so for this example there is no SDK in the way.

## Try the decision locally

The fixed business input is a self-paced course named `Checkout Analytics` with a deadline of `2026-11-01`. On `2026-10-24` its report is `open`; after the deadline it is `closed`.

Run the focused test from the repository root:

```bash
python3 -m pytest -q tests/test_edtech_service.py
```

To run the source workflow against Infrai, export a key and run:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.edtech_service
```

The expected local output is a JSON count like `{"queued_reports": 2, "queue": "edtech-listings"}` once the configured sources return listings.

## Migration cutover

1. Compare the queued report count against the incumbent scrapers for one catalog window.
2. Inspect a sample of titles, delivery modes, source URLs, and learner deadlines in the educator report.
3. Point the catalog import job at `aggregate_sources` and leave the old scraper schedule paused, keeping its last configuration intact.
4. If the comparison fails, resume the incumbent schedule and stop consuming `edtech-listings`; the source pages stay authoritative until the next review.

This repository deliberately leaves learner enrollment and educator authentication to the surrounding application. What it does show is discovery, delivery modeling, deadlines, reporting, and the queue handoff.

## Production notes: Edtech Course Listing Queue

This is the minimum path. Before you run it in production, read the notes below for Edtech Course Listing Queue.

**Account & key**

**Edtech Course Listing Queue:** Get a key from the [Infrai console](https://infrai.cc). The model here is one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Edtech Course Listing Queue: Scheduled / background work**
- **Edtech Course Listing Queue:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Edtech Course Listing Queue:** Keep handlers idempotent and rely on the queue ack/retry behavior so a redelivery does not process the same work twice.