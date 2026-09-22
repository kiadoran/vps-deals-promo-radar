#!/usr/bin/env python3
"""ILANG
::TYPE{worker}::ROLE{fetch_public_official_offer_pages}
::BOUNDARY{never:invent_prices_or_offers; only:public_configured_sources}
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / ".ilang" / "site.ilang"
OUT = ROOT / "data" / "offers.json"


def parse_ilang(path: Path) -> dict:
    """Minimal, deliberate reader for the I-Lang configuration used by this project."""
    text = path.read_text(encoding="utf-8")
    state = re.search(r"::STATE\{@SITE,\s*([^}]*)}", text)
    if not state:
        raise ValueError("Missing @SITE state in .ilang/site.ilang")
    settings = dict(re.findall(r"([a-z_]+):([^,}]+)", state.group(1)))
    providers_block = re.search(r"::MODULE\{PROVIDERS[^}]*}\s*(.*?)(?=\n::MODULE)", text, re.S)
    if not providers_block:
        raise ValueError("Missing PROVIDERS module")
    providers = []
    for line in providers_block.group(1).splitlines():
        if "|" not in line:
            continue
        values = [x.strip() for x in line.split("|")]
        if len(values) >= 3 and values[0]:
            providers.append({"name": values[0], "website": values[1], "source_url": values[2], "affiliate_url": values[3] if len(values) > 3 else ""})
    return {"site": settings, "providers": providers}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "vps-deals-radar/1.0 (+public static index)"})
    with urllib.request.urlopen(req, timeout=25) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            return ""
        return response.read(1_500_000).decode(response.headers.get_content_charset() or "utf-8", "replace")


def visible_text(markup: str) -> str:
    markup = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def extract(provider: dict, page: str, locale_currency: str) -> list[dict]:
    """Conservative extraction: only emit when the source has an explicit offer signal.
    This intentionally drops pages whose deal facts cannot be established deterministically.
    """
    text = visible_text(page)
    if not re.search(r"\b(off|discount|credit|promo(?:tion)?|deal)\b|%\s*(?:off|discount)", text, re.I):
        return []
    result = []
    # A published dollar credit is a real offer but not a VPS price; price remains absent.
    credit = re.search(r"(?:free|up to|receive|with)\s*\$([0-9][0-9,]*)\s+(?:in\s+)?(?:cloud\s+)?credits?", text, re.I)
    if credit:
        amount = credit.group(1).replace(",", "")
        title = f"${amount} cloud credit"
        result.append({"id": slugify(provider["name"] + "-" + title), "provider": provider["name"], "title": title,
                       "description": "Official promotional credit; check eligibility and terms on the provider page.",
                       "currency": "USD", "offer_url": provider["affiliate_url"] or provider["source_url"], "source_url": provider["source_url"]})
    # Explicit monthly price adjacent to a sale/discount signal. Never derive a percentage or price.
    money = re.search(r"(?:£|\$|€)\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/\s*(?:mo|month)|per\s+month)", text, re.I)
    if money and re.search(r"(?:up to\s+)?\d{1,2}%\s*(?:off|discount)|\bdeal\b", text, re.I):
        symbol = money.group(0).strip()[0]
        currency = {"£": "GBP", "$": "USD", "€": "EUR"}.get(symbol, locale_currency)
        amount = money.group(1).replace(",", ".")
        title = "Promotional VPS plan"
        result.append({"id": slugify(provider["name"] + "-" + title + "-" + amount), "provider": provider["name"], "title": title,
                       "description": "Price shown on the official provider promotion page.", "price": amount, "currency": currency,
                       "offer_url": provider["affiliate_url"] or provider["source_url"], "source_url": provider["source_url"]})
    return result


def main() -> int:
    config = parse_ilang(CONFIG)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    offers, errors = [], []
    for provider in config["providers"]:
        try:
            page = fetch(provider["source_url"])
            for offer in extract(provider, page, config["site"].get("currency", "USD")):
                offer["fetched_at"] = now
                offers.append(offer)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            errors.append({"provider": provider["name"], "source_url": provider["source_url"], "error": str(exc)[:200]})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": now, "offers": offers, "errors": errors}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(offers)} verified offer(s); {len(errors)} source error(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
