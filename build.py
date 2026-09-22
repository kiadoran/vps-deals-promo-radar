#!/usr/bin/env python3
"""ILANG
::TYPE{builder}::ROLE{render_static_offer_index_from_verified_data}
::RULE{read_site_rules_from_.ilang/site.ilang; never_publish_expired_as_active}
"""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scraper import parse_ilang

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
TEMPLATES = ROOT / "templates"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def url_for(domain: str, path: str = "") -> str:
    root = domain if domain.startswith("http") else f"https://{domain}"
    return root.rstrip("/") + path


def jsonld(value: dict) -> str:
    return '<script type="application/ld+json">' + json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "</script>"


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def render(name: str, **values: object) -> str:
    output = load_template(name)
    for key, value in values.items():
        output = output.replace("{{" + key + "}}", str(value))
    return output


def write(relative: str, contents: str) -> None:
    target = SITE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(contents, encoding="utf-8")


def active(offer: dict) -> bool:
    until = offer.get("valid_until")
    if not until:
        return True
    try:
        return datetime.fromisoformat(until.replace("Z", "+00:00")) >= datetime.now(timezone.utc)
    except ValueError:
        return False


def card(offer: dict, domain: str) -> str:
    detail = f"/deals/{esc(offer['id'])}/"
    price = f"<p class=\"price\">{esc(offer['currency'])} {esc(offer['price'])}</p>" if offer.get("price") else ""
    return f'<article class="card"><p class="provider">{esc(offer["provider"])}</p><h2><a href="{detail}">{esc(offer["title"])}</a></h2>{price}<p>{esc(offer.get("description", ""))}</p><a class="button" href="{detail}">View terms</a></article>'


def head_schema(domain: str, path: str, title: str, description: str, schema: dict) -> str:
    canonical = url_for(domain, path)
    return jsonld(schema) + f'<link rel="canonical" href="{esc(canonical)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website"><meta property="og:url" content="{esc(canonical)}"><meta name="twitter:card" content="summary_large_image">'


def main() -> None:
    config = parse_ilang(ROOT / ".ilang" / "site.ilang")
    site_cfg = config["site"]
    brand, domain, niche = site_cfg["brand"].strip(), site_cfg["domain"].strip(), site_cfg["niche"].strip()
    data = json.loads((ROOT / "data" / "offers.json").read_text(encoding="utf-8"))
    offers = [x for x in data.get("offers", []) if active(x)]
    shutil.rmtree(SITE, ignore_errors=True)
    SITE.mkdir()
    (SITE / "assets").mkdir()
    shutil.copy2(TEMPLATES / "style.css", SITE / "assets" / "style.css")
    generated = data.get("generated_at") or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    items = "".join(card(x, domain) for x in offers) or '<p class="empty">No verified active offers are currently published. We only show offers we can confirm on an official source.</p>'
    list_schema = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i, "url": url_for(domain, f"/deals/{o['id']}/")} for i, o in enumerate(offers, 1)]}
    title = f"{brand} | Verified {niche} offers"
    index_head = head_schema(domain, "/", title, "Official-source VPS hosting offers, checked automatically.", list_schema)
    write("index.html", render("index.html", BRAND=esc(brand), NICHE=esc(niche), OFFERS=items, UPDATED=esc(generated), HEAD=index_head))

    by_provider: dict[str, list[dict]] = {}
    for offer in offers:
        by_provider.setdefault(offer["provider"], []).append(offer)
    for provider in config["providers"]:
        name, key = provider["name"], slug(provider["name"])
        own = by_provider.get(name, [])
        prices = [float(x["price"]) for x in own if x.get("price")]
        aggregate = {"@context": "https://schema.org", "@type": "Service", "name": name + " VPS", "url": url_for(domain, f"/providers/{key}/")}
        if prices:
            aggregate["offers"] = {"@type": "AggregateOffer", "lowPrice": min(prices), "highPrice": max(prices), "priceCurrency": own[0]["currency"], "offerCount": len(prices)}
        phead = head_schema(domain, f"/providers/{key}/", f"{name} offers | {brand}", f"Verified current offers from {name}.", aggregate)
        write(f"providers/{key}/index.html", render("provider.html", BRAND=esc(brand), PROVIDER=esc(name), OFFERS="".join(card(x, domain) for x in own) or '<p class="empty">No currently verified offer.</p>', HEAD=phead))

    for offer in offers:
        path = f"/deals/{offer['id']}/"
        offer_schema = {"@context": "https://schema.org", "@type": "Offer", "name": offer["title"], "url": url_for(domain, path), "availability": "https://schema.org/InStock"}
        if offer.get("price"):
            offer_schema.update({"price": offer["price"], "priceCurrency": offer["currency"]})
        if offer.get("valid_until"):
            offer_schema["priceValidUntil"] = offer["valid_until"]
        breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": brand, "item": url_for(domain)}, {"@type": "ListItem", "position": 2, "name": offer["title"], "item": url_for(domain, path)}]}
        dhead = head_schema(domain, path, f"{offer['title']} | {brand}", offer.get("description", ""), offer_schema) + jsonld(breadcrumb)
        price = f"{esc(offer['currency'])} {esc(offer['price'])}" if offer.get("price") else "See official terms"
        write(f"deals/{offer['id']}/index.html", render("deal.html", BRAND=esc(brand), PROVIDER=esc(offer["provider"]), TITLE=esc(offer["title"]), DESCRIPTION=esc(offer.get("description", "")), PRICE=price, OFFER_URL=esc(offer["offer_url"]), SOURCE_URL=esc(offer["source_url"]), FETCHED=esc(offer["fetched_at"]), HEAD=dhead))

    compare_head = head_schema(domain, "/compare/", f"Compare active offers | {brand}", "A current list of official-source VPS offers.", list_schema)
    write("compare/index.html", render("compare.html", BRAND=esc(brand), OFFERS=items, HEAD=compare_head))
    urls = ["/"] + [f"/providers/{slug(p['name'])}/" for p in config["providers"]] + ["/compare/"] + [f"/deals/{o['id']}/" for o in offers]
    lastmod = esc(generated[:10])
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{esc(url_for(domain, u))}</loc><lastmod>{lastmod}</lastmod></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {url_for(domain, '/sitemap.xml')}\n")
    print(f"Built {len(offers)} active offer pages into {SITE}")


if __name__ == "__main__":
    main()
