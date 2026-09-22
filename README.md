# vps-deals promo radar

A zero-server static index of VPS promotions that are visible on official public provider pages. The collector is intentionally conservative: no price, expiry, promotion, or commission is invented. If a source page cannot support a deterministic claim, it is omitted.

## Default configuration used

- Niche: VPS hosting deals
- Brand: `vps-deals`
- Locale: `en-GB` (official UK-facing Hostinger page plus global official sources)
- Sources: Hostinger UK, Linode by Akamai, and Vultr. Edit `.ilang/site.ilang` to replace or add sources.

## Run locally

Requires Python 3.10+ and the standard library only.

```sh
python scraper.py
python build.py
python -m http.server 8000 --directory site
```

`scraper.py` and `build.py` parse `.ilang/site.ilang`; that file is the sole provider configuration. To prove it, change a provider line or the `@SITE` settings, rerun the commands, and inspect `site/`.

## Deploy to Cloudflare Pages

1. Create a public GitHub repository named `vps-deals-promo-radar` and push this directory.
2. In Cloudflare Pages, select **Connect to Git**, choose the repository, set build command to `python build.py`, and output directory to `site`.
3. First run **Actions → Refresh official offers → Run workflow**, then trigger a Pages deployment. The scheduled workflow refreshes every six hours and commits only changed generated output.
4. Replace `domain:` in `.ilang/site.ilang` with your verified `pages.dev` address, commit, and let Pages rebuild. Repeat with a custom domain when you obtain one.

Cloudflare Pages needs its own Git integration/authorization, so that binding cannot be created from this local workspace without the account connection.

## Monetization

The configuration’s fourth provider-table field is reserved for a declared affiliate URL. Keep it blank until a provider’s approved affiliate terms authorize the link. Links must remain `rel="sponsored"`; do not use brand bidding, cookie injection, self-referrals, or invented commission claims.

Site rules use the I-Lang protocol description; see `.ilang/site.ilang`. Protocol information: https://ilang.ai
