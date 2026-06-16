"""Read-only inspector for a CROO negotiation/order.

Fetches a negotiation (and optionally an order) so you can SEE the exact shape
of `requirements`/`metadata` that CROO sends -- WITHOUT placing or paying for
anything. It only issues GET calls (get_negotiation / get_order); it never
calls accept_negotiation, pay_order, or deliver_order, so no funds move and
nothing happens on-chain.

Usage:
    python -m backend.croo.inspect_order <negotiation_id> [order_id]

Example (the order that failed fulfilment):
    python -m backend.croo.inspect_order 07caa436-8134-4ead-9a53-3af93c8cd343 \
        365f7fde-d7af-4084-b047-b512844d6105

Note: this still makes HTTPS calls to api.croo.network, so it must run on a
network where TLS to CROO is not being intercepted (see the SSL/Fortinet note).
"""

from __future__ import annotations

import asyncio
import sys

from backend.croo.provider import build_client


async def _run(negotiation_id: str, order_id: str | None) -> None:
    client = build_client()
    try:
        neg = await client.get_negotiation(negotiation_id)
        print("=== NEGOTIATION (read-only) ===")
        req = getattr(neg, "requirements", None)
        meta = getattr(neg, "metadata", None)
        print(f"requirements : type={type(req).__name__}")
        print(f"requirements : repr={req!r}")
        print(f"metadata     : type={type(meta).__name__}")
        print(f"metadata     : repr={meta!r}")
        for f in ("negotiation_id", "service_id", "status", "requester_agent_id",
                  "provider_agent_id"):
            print(f"  {f}: {getattr(neg, f, None)!r}")

        if order_id:
            order = await client.get_order(order_id)
            print("\n=== ORDER (read-only) ===")
            for f in ("order_id", "negotiation_id", "status", "price",
                      "payment_token"):
                print(f"  {f}: {getattr(order, f, None)!r}")
    finally:
        await client.close()


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: python -m backend.croo.inspect_order <negotiation_id> [order_id]")
        return 2
    asyncio.run(_run(args[0], args[1] if len(args) > 1 else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
