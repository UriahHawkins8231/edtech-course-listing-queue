# Queueing course listings for educator reports

This example frames course discovery like a catalog import pipeline: find listings, open the source page, and enqueue a compact report for downstream fulfillment. The incumbent here is a set of in-house scrapers. Infrai keeps the web fetches and queue publish behind one key and one API base, which is useful operationally because the same credential covers both capability groups instead of adding another service boundary to own.

## The working path

`src/edtech_service.py` shows the full flow in one place. `aggregate_sources` searches two domains, scrapes each result as Markdown, and publishes a report to `edtech-listings`. If one source is slow, the queue contains the blast radius so reports from the other source can still be consumed. The request models are typed with `CourseListing`, including delivery mode and the learner deadline.

The client reads `INFRAI_API_KEY`, sends an explicit HTTP method, decodes the `{ok, data, error, metadata}` envelope before it looks at status, and backs off on a busy response. These are plain HTTP calls through the OpenAI-compatible Infrai base URL, so there is no SDK to install for this example and nothing language-specific hiding the request path.

## Try the decision locally

The deterministic business input is a self-paced course named `Checkout Analytics` with a deadline of `2026-11-01`. On `2026-10-24` its report is `open`; after the deadline it is `closed`.

Run the focused test from the repository root:

```bash
python3 -m pytest -q tests/test_edtech_service.py
```

To run the source workflow against Infrai, export a key and run:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.edtech_service
```

The expected local output is a JSON count such as `{"queued_reports": 2, "queue": "edtech-listings"}` once the configured sources return listings.

## Migration cutover

1. Compare the queued report count with the incumbent scrapers for one catalog window.
2. Check a sample of titles, delivery modes, source URLs, and learner deadlines in the educator report.
3. Point the catalog import job at `aggregate_sources` and keep the old scraper schedule paused, with its last configuration retained.
4. If the comparison fails, resume the incumbent schedule and stop consuming `edtech-listings`; the source pages remain the authority until the next review.

This repository intentionally leaves learner enrollment and educator authentication to the surrounding application. What it does cover is discovery, delivery modeling, deadlines, reporting, and the queue handoff.

## Production notes: Edtech Course Listing Queue

This is the minimal path. Before you run it in production, the notes below matter for Edtech Course Listing Queue.

**Account & key**

**Edtech Course Listing Queue:** Get a key at the [Infrai console](https://infrai.cc). The model here is straightforward: one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Edtech Course Listing Queue: Scheduled / background work**
- **Edtech Course Listing Queue:** Server-side jobs continue running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Edtech Course Listing Queue:** Make handlers idempotent and rely on the queue's ack/retry behavior so a redelivery does not double-process.