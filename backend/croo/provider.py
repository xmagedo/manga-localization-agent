"""CROO provider loop for the manga localization agent (Stage F).

Connects to CROO over WebSocket, listens for the order lifecycle, and (in live
mode) accepts negotiations, runs localize() on payment, and delivers the
result.

Credentials are read from the environment via python-dotenv:
    CROO_SDK_KEY   - API key from the CROO Agent Store (format: croo_sk_...)
    CROO_API_URL   - e.g. https://api.croo.network
    CROO_WS_URL    - e.g. wss://api.croo.network/ws
    BASE_RPC_URL   - optional Base RPC URL
The key is never printed or logged.

SAFETY -------------------------------------------------------------------
By default this runs in OBSERVE (safe) mode: it connects (so the agent shows
"Online" in the dashboard) and logs every event, but it does NOT call
accept_negotiation or deliver_order -- i.e. it never triggers an on-chain /
paid action. To actually accept and fulfil real (paid) orders, run with
--live or set CROO_PROVIDER_LIVE=1. Do that only when you intend to transact.

Run:
    python -m backend.croo.provider --check   # verify env + client, no connect
    python -m backend.croo.provider           # go Online in OBSERVE mode
    python -m backend.croo.provider --live     # go Online and fulfil paid orders
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import signal
from pathlib import Path

from dotenv import load_dotenv

from croo import (
    AgentClient,
    Config,
    DeliverableType,
    DeliverOrderRequest,
    Event,
    EventType,
)

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("croo.provider")

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = BASE_DIR / "backend" / "data" / "input"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_ENV = ("CROO_SDK_KEY", "CROO_API_URL", "CROO_WS_URL")


def _live_enabled(cli_live: bool) -> bool:
    return cli_live or os.getenv("CROO_PROVIDER_LIVE", "0").lower() in ("1", "true", "yes")


def build_client() -> AgentClient:
    """Construct an AgentClient from env vars. Raises if any are missing.

    Does not connect; constructing the client performs no network call.
    """
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + " (set them in .env)"
        )
    config = Config(
        base_url=os.environ["CROO_API_URL"],
        ws_url=os.environ["CROO_WS_URL"],
        rpc_url=os.getenv("BASE_RPC_URL", ""),
    )
    return AgentClient(config, os.environ["CROO_SDK_KEY"])


# Matches an http(s) URL; stops at whitespace, quotes, or common JSON/markup delims.
_URL_RE = re.compile(r"""https?://[^\s"'<>\\)\]}]+""", re.IGNORECASE)
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def _coerce(obj):
    """If obj is a JSON string (object/array/quoted), parse it; else return as-is."""
    if isinstance(obj, str):
        s = obj.strip()
        if s[:1] in ("{", "[", '"'):
            try:
                return json.loads(s)
            except Exception:
                return obj
    return obj


def _iter_strings(obj):
    """Yield every string found anywhere inside nested dicts/lists/tuples."""
    obj = _coerce(obj)
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            yield from _iter_strings(v)


def _find_image_url(*candidates):
    """Search any number of (possibly nested/JSON) structures for an http(s)
    URL. Prefer one that looks like an image; otherwise return the first URL.
    """
    urls = []
    for c in candidates:
        for s in _iter_strings(c):
            urls.extend(_URL_RE.findall(s))
    # strip trailing punctuation the regex might capture
    urls = [u.rstrip(".,;'\"") for u in urls if u]
    for u in urls:
        if u.split("?")[0].lower().endswith(_IMAGE_EXTS):
            return u
    return urls[0] if urls else None


def _download_to_input(url: str) -> Path:
    import requests  # already a project dependency

    url = url.strip()
    fname = Path(url.split("?")[0]).name or "order_input.png"
    dest = INPUT_DIR / fname
    # Browser-like headers so hosts that block bots (e.g. catbox) still serve the image.
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "image/*",
    }
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    log.info("Downloaded order input image to %s", dest)
    return dest


def _resolve_image_path(negotiation) -> Path:
    """Figure out which image to localize from a negotiation.

    Robust extraction: accepts a bare URL, a named field, OR an http(s) image
    URL found anywhere inside the (possibly nested / JSON-encoded) requirements
    or metadata. Also honours a local {"image_path": ...}.
    Raises ValueError if no usable image reference is found.
    """
    req_raw = getattr(negotiation, "requirements", None)
    meta_raw = getattr(negotiation, "metadata", None)

    data = _coerce(req_raw)
    if isinstance(data, dict):
        # direct local path
        local = data.get("image_path")
        if local and Path(local).exists():
            return Path(local)
        # preferred named fields. CROO puts the URL under "text".
        for key in ("text", "image_url", "image", "url", "input", "content", "data"):
            found = _find_image_url(data.get(key))
            if found:
                return _download_to_input(found)

    # fallback: scan every string value anywhere in requirements, then metadata,
    # for anything that looks like an http(s) URL.
    url = _find_image_url(req_raw) or _find_image_url(meta_raw)
    if url:
        return _download_to_input(url)

    raise ValueError(
        "Could not find an image reference in negotiation. "
        f"requirements={type(req_raw).__name__}:{req_raw!r} "
        f"metadata={type(meta_raw).__name__}:{meta_raw!r}"
    )


async def _accept(client: AgentClient, negotiation_id: str) -> None:
    try:
        await client.accept_negotiation(negotiation_id)
        log.info("[LIVE] Accepted negotiation %s", negotiation_id)
    except Exception as e:  # noqa: BLE001
        log.exception("Failed to accept negotiation %s: %s", negotiation_id, e)


async def _fulfill(client: AgentClient, order_id: str) -> None:
    """Run localize() for a paid order and deliver the result."""
    try:
        order = await client.get_order(order_id)
        negotiation = await client.get_negotiation(order.negotiation_id)
        image_path = _resolve_image_path(negotiation)

        log.info("[LIVE] Running localize() for order %s on %s", order_id, image_path)
        # localize() is blocking (YOLO + OCR); keep the event loop responsive.
        from backend.services.localize import localize

        result = await asyncio.to_thread(localize, str(image_path), "ar")

        # Upload the cleaned page image and get a temporary download URL.
        clean_path = Path(result.clean_image_path)
        object_key = await client.upload_file(clean_path.name, clean_path.read_bytes())
        download_url = await client.get_download_url(object_key)

        payload = {
            "manifest": result.manifest,
            "clean_image_url": download_url,
            "clean_image_object_key": object_key,
            "bubbles": result.results.get("bubbles", []),
        }
        req = DeliverOrderRequest(
            deliverable_type=DeliverableType.TEXT,
            deliverable_text=json.dumps(payload, ensure_ascii=False),
        )
        await client.deliver_order(order_id, req)
        log.info("[LIVE] Delivered order %s (%d bubbles)", order_id, result.bubble_count)
    except Exception as e:  # noqa: BLE001
        log.exception("Failed to fulfil order %s: %s", order_id, e)


async def run(live: bool) -> None:
    client = build_client()
    mode = "LIVE (will accept + deliver paid orders)" if live else "OBSERVE (safe: no accept/deliver)"
    log.info("Connecting to CROO WebSocket... mode=%s", mode)

    stream = await client.connect_websocket()
    log.info("Connected. Your agent should now show ONLINE in the CROO dashboard.")
    if not live:
        log.info("OBSERVE mode: events are logged only; nothing on-chain happens. "
                 "Re-run with --live (or CROO_PROVIDER_LIVE=1) to fulfil real orders.")

    def on_negotiation_created(e: Event) -> None:
        log.info("NEGOTIATION_CREATED negotiation_id=%s service_id=%s requester=%s",
                 e.negotiation_id, e.service_id, e.requester_agent_id)
        if not live:
            log.info("OBSERVE mode: NOT accepting negotiation %s.", e.negotiation_id)
            return
        asyncio.create_task(_accept(client, e.negotiation_id))

    def on_order_paid(e: Event) -> None:
        log.info("ORDER_PAID order_id=%s", e.order_id)
        if not live:
            log.info("OBSERVE mode: NOT delivering order %s.", e.order_id)
            return
        asyncio.create_task(_fulfill(client, e.order_id))

    def on_other(e: Event) -> None:
        log.info("EVENT %s negotiation_id=%s order_id=%s status=%s reason=%s",
                 e.type, e.negotiation_id, e.order_id, e.status, e.reason)

    stream.on(EventType.NEGOTIATION_CREATED, on_negotiation_created)
    stream.on(EventType.ORDER_PAID, on_order_paid)
    for et in (
        EventType.NEGOTIATION_REJECTED,
        EventType.NEGOTIATION_EXPIRED,
        EventType.ORDER_CREATED,
        EventType.ORDER_COMPLETED,
        EventType.ORDER_REJECTED,
        EventType.ORDER_EXPIRED,
    ):
        stream.on(et, on_other)

    # Stay alive until Ctrl-C / SIGTERM.
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    log.info("Provider running. Press Ctrl-C to stop.")
    try:
        await stop.wait()
    finally:
        log.info("Shutting down...")
        try:
            await stream.close()
        finally:
            await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="CROO provider for the manga localization agent")
    parser.add_argument("--live", action="store_true",
                        help="Accept negotiations and deliver paid orders (on-chain). "
                             "Default is OBSERVE/safe mode.")
    parser.add_argument("--check", action="store_true",
                        help="Validate env vars + construct the client, then exit "
                             "(no WebSocket connect, no Online, no transaction).")
    parser.add_argument("--deliver", metavar="ORDER_ID",
                        help="Fulfil and deliver a single ALREADY-PAID order by id, "
                             "then exit. Uses the existing escrow -- no new payment. "
                             "Use this to deliver an order whose ORDER_PAID event was "
                             "missed (e.g. it failed the first time).")
    args = parser.parse_args()

    if args.check:
        build_client()  # raises if env is missing
        key = os.environ["CROO_SDK_KEY"]
        print("config OK:")
        print(f"  CROO_API_URL = {os.environ['CROO_API_URL']}")
        print(f"  CROO_WS_URL  = {os.environ['CROO_WS_URL']}")
        print(f"  CROO_SDK_KEY = present (length {len(key)}, not shown)")
        print(f"  BASE_RPC_URL = {os.getenv('BASE_RPC_URL', '(unset)')}")
        print("  client constructed; NOT connecting (use no flag to go Online).")
        return 0

    if args.deliver:
        async def _deliver_one() -> None:
            client = build_client()
            try:
                log.info("Manual delivery for already-paid order %s ...", args.deliver)
                await _fulfill(client, args.deliver)
            finally:
                await client.close()
        asyncio.run(_deliver_one())
        return 0

    live = _live_enabled(args.live)
    asyncio.run(run(live))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
