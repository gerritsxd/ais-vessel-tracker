
#!/usr/bin/env python3
# manual_shipping_scraper.py

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

USER_AGENT = "manual-shipping-scraper/1.0 (research; contact: you@example.com)"
REQ_TIMEOUT = 25


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_ws(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def extract_visible_text(html: str) -> str:
    """
    Lightweight boilerplate removal:
    - drops script/style/noscript/svg
    - tries to drop nav/footer/header/asides if present
    - extracts text from body
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    # common boilerplate containers
    for selector in ["nav", "footer", "header", "aside"]:
        for tag in soup.find_all(selector):
            tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator=" ")
    return normalize_ws(text)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
})


def fetch_url(url: str, sleep_s: float = 0.5) -> str:
    r = SESSION.get(url, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    if sleep_s:
        time.sleep(sleep_s)
    return r.text


def fetch_url(url: str, sleep_s: float = 0.5) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    r = requests.get(url, headers=headers, timeout=REQ_TIMEOUT)
    r.raise_for_status()

    if sleep_s:
        time.sleep(sleep_s)

    return r.text



def wikipedia_fetch(title: str, lang: str = "en") -> Dict[str, Any]:
    """
    Uses MediaWiki API (no key) to fetch:
    - canonical page url
    - short extract
    - full extract (plain text)
    """
    if not title:
        return {}

    api = f"https://{lang}.wikipedia.org/w/api.php"
    headers = {"User-Agent": USER_AGENT}

    # First request: get page, extracts + canonical URL
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|info",
        "inprop": "url",
        "explaintext": 1,
        "exsectionformat": "plain",
        "titles": title,
        "redirects": 1,
    }
    r = requests.get(api, headers=headers, params=params, timeout=REQ_TIMEOUT)
    r.raise_for_status()
    data = r.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return {}

    page = next(iter(pages.values()))
    if "missing" in page:
        return {}

    full_text = normalize_ws(page.get("extract", ""))
    summary = full_text[:900] + ("…" if len(full_text) > 900 else "")
    return {
        "title": page.get("title"),
        "url": page.get("fullurl"),
        "summary": summary,
        "text": full_text,
        "length": len(full_text),
    }


@dataclass
class CompanySpec:
    company_name: str

    # Manual Wikipedia page title (recommended; avoids fuzzy search errors)
    wikipedia_title: Optional[str] = None

    # Manual list of website pages to scrape
    # Example: [{"page_type":"home","url":"https://..."}, ...]
    website_pages: List[Dict[str, str]] = field(default_factory=list)

    # Optional numeric/categorical fields you already computed elsewhere
    attributes: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, Any] = field(default_factory=dict)


def scrape_company(spec: CompanySpec) -> Dict[str, Any]:
    pages_out: List[Dict[str, Any]] = []

    for p in spec.website_pages:
        page_type = p.get("page_type", "unknown")
        url = p.get("url")
        if not url:
            continue

        try:
            html = fetch_url(url)
            text = extract_visible_text(html)

        except requests.HTTPError as e:
            # --- FIX #3: text-only fallback for hard 403s ---
            if e.response is not None and e.response.status_code == 403:
                try:
                    fallback_url = f"http://textise.net/showtext.aspx?strURL={url}"
                    html = fetch_url(fallback_url, sleep_s=0)
                    text = extract_visible_text(html)
                except Exception as e2:
                    text = f"[SCRAPE_ERROR] 403 + fallback failed: {type(e2).__name__}: {e2}"
            else:
                text = f"[SCRAPE_ERROR] HTTPError: {e}"

        except Exception as e:
            text = f"[SCRAPE_ERROR] {type(e).__name__}: {e}"


        pages_out.append(
            {
                "page_type": page_type,
                "url": url,
                "text": text,
                "length": len(text),
            }
        )

    wiki_out = {}
    if spec.wikipedia_title:
        try:
            wiki_out = wikipedia_fetch(spec.wikipedia_title)
        except Exception as e:
            wiki_out = {"error": f"{type(e).__name__}: {e}", "title": spec.wikipedia_title}

    # Ensure the exact keys exist even if empty
    return {
        "company_name": spec.company_name,
        "timestamp": utc_now_iso(),
        "attributes": {
            "vessel_count": spec.attributes.get("vessel_count"),
            "avg_emissions_tons": spec.attributes.get("avg_emissions_tons"),
            "avg_co2_per_distance": spec.attributes.get("avg_co2_per_distance"),
            "avg_technical_efficiency": spec.attributes.get("avg_technical_efficiency"),
            "avg_wasp_fit_score": spec.attributes.get("avg_wasp_fit_score"),
            "primary_ship_types": spec.attributes.get("primary_ship_types", []),
        },
        "labels": {
            "company_categories": spec.labels.get("company_categories", []),
            "fleet_size_category": spec.labels.get("fleet_size_category"),
            "emissions_category": spec.labels.get("emissions_category"),
        },
        "text_data": {
            "wikipedia": wiki_out if wiki_out else {},
            "website": {
                "pages": [
                    # Keep the same shape you showed (no url required, but useful)
                    {"page_type": x["page_type"], "text": x["text"], "length": x["length"]}
                    for x in pages_out
                ],
                "pages_count": len(pages_out),
                "total_length": sum(x["length"] for x in pages_out),
            },
        },
    }


def main() -> None:
    # --- EDIT THIS: your 15 companies ---
    companies: List[CompanySpec] = [
        CompanySpec(
            company_name="CLDN RORO S.A.",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.cldn.com/"},
                {"page_type": "about-us", "url": "https://www.cldn.com/our-company"},
                {"page_type": "fleet", "url": "https://www.cldn.com/our-fleet"},
                {"page_type": "sustainability", "url": "https://www.cldn.com/corporate-social-responsibility"},
            ],),
        CompanySpec(
            company_name="Anthony Veder Rederijzaken B.V.",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://anthonyveder.com/"},
                {"page_type": "about-us", "url": "https://anthonyveder.com/about-us/"},
                {"page_type": "fleet", "url": "https://anthonyveder.com/our-fleet/"},
                {"page_type": "sustainability", "url": "https://anthonyveder.com/sustainability/"},
                {"page_type": "environment", "url": "https://anthonyveder.com/blog/story/careforenvironment/"}
            ],),
        CompanySpec(
            company_name="Jifmar Offshore Services",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://jifmar.com/who-we-are/"},
                {"page_type": "about-us", "url": "https://jifmar.com/our-vision-values/"},
                {"page_type": "fleet", "url": "https://jifmar.com/our-fleet/"},
                {"page_type": "sustainability", "url": "https://jifmar.com/our-policies/"},
            ],),
        CompanySpec(
            company_name="SMT Shipping (Cyprus) Ltd",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.smtshipping.com/"},
                {"page_type": "about-us", "url": "https://www.smtshipping.com/our-company/"},
                {"page_type": "sustainability", "url": "https://www.smtshipping.com/policies/esg-policy-2/"},
            ],),
        CompanySpec(
            company_name="Carisbrooke Shipping Ltd",
            wikipedia_title="Carisbrooke Shipping",
            website_pages=[
                {"page_type": "home", "url": "https://carisbrooke.co/"},
                {"page_type": "about-us", "url": "https://carisbrooke.co/about-us/"},
                {"page_type": "sustainability", "url": "https://carisbrooke.co/sustainable-shipping/"},
                {"page_type": "environment", "url": "https://carisbrooke.co/the-green-ship-project/"}
            ],),
        CompanySpec(
            company_name="Compagnie Maritime Nantaise - MN",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.compagnie-maritime-nantaise.com/en/"},
                {"page_type": "about-us", "url": "https://www.compagnie-maritime-nantaise.com/en/our-know-how/"},
                {"page_type": "fleet", "url": "https://www.compagnie-maritime-nantaise.com/en/fleet/"},
                {"page_type": "sustainability", "url": "https://www.compagnie-maritime-nantaise.com/en/environment/"},
            ],),

        CompanySpec(
            company_name="Nippon Yusen Kabushiki Kaisha",
            wikipedia_title="",
            website_pages=[
                {"page_type": "about-us", "url": "https://www.nyk.com/english/profile/message/"},
                {"page_type": "sustainability", "url": "https://www.nyk.com/english/sustainability/envi/"},
                {"page_type": "environment", "url": "https://www.nyk.com/english/sustainability/envi/decarbonization/"}
            ],),
        CompanySpec(
            company_name="Rederi Ab Nathalie",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.rabn.fi/"},
                {"page_type": "about-us", "url": "https://www.rabn.fi/about-us/"},
                {"page_type": "fleet", "url": "https://www.rabn.fi/our-fleet/"},
                {"page_type": "sustainability", "url": "https://www.rabn.fi/advancing-the-shipping-industry/"},
            ],),
        CompanySpec(
            company_name="Boomsma Shipping",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://boomsmashipping.nl/"},
                {"page_type": "about-us", "url": "https://boomsmashipping.nl/about-us"},
                {"page_type": "fleet", "url": "https://boomsmashipping.nl/our-fleet"},
                {"page_type": "sustainability", "url": "https://boomsmashipping.nl/wind-for-shipping-(w4s)"},
                {"page_type": "environment", "url": "https://boomsmashipping.nl/newbuilding-order-4-4-low-emissions-short-sea-dry-cargo-vessels"}
            ],),

        CompanySpec(
            company_name="Sea-Cargo",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://sea-cargo.no/?utm_source=google&utm_campaign=19338743234&utm_medium=ad&utm_content=642252478683&utm_term=sea%20cargo&gad_source=1&gad_campaignid=19338743234&gbraid=0AAAAADjxPXrUTlJB4m325EmlcUxF_efAr&gclid=Cj0KCQiA6Y7KBhCkARIsAOxhqtPPcZnXJCNO3QbFmWFl40eJeLixgZ-7xU8xFigiARUCbHkpDMrjds8aAnl6EALw_wcB"},
                {"page_type": "about-us", "url": "https://sea-cargo.no/about-us/"},
                {"page_type": "sustainability", "url": "https://sea-cargo.no/2025/03/25/the-future-of-shipping-is-here/"},
                {"page_type": "environment", "url": "https://sea-cargo.no/2024/12/05/combatting-climate-change-sea-cargo-express/"}
            ],),
        CompanySpec(
            company_name="Cargill",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.cargill.nl/en/ocean-transportation"},
                {"page_type": "about-us", "url": "https://www.cargill.nl/en/about-cargill"},
                {"page_type": "sustainability", "url": "https://www.cargill.nl/en/sustainability"},
            ],),
        CompanySpec(
            company_name="Eastern Pacific Shipping",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.epshipping.com.sg/"},
                {"page_type": "about-us", "url": "https://www.epshipping.com.sg/who-we-are/"},
                {"page_type": "sustainability", "url": "https://www.epshipping.com.sg/emissions-reduction-and-tracking/"},
                {"page_type": "environment", "url": "https://www.epshipping.com.sg/environment/"}
            ],),
        CompanySpec(
            company_name="Odfjell",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.odfjell.com/"},
                {"page_type": "about-us", "url": "https://www.odfjell.com/about"},
                {"page_type": "fleet", "url": "https://www.odfjell.com/tankers"},
                {"page_type": "sustainability", "url": "https://www.odfjell.com/about/our-stories/odfjell-has-launched-the-first-operational-green-corridor-between-brazil-and-europe/"},
                {"page_type": "environment", "url": "https://www.odfjell.com/about/our-stories/delivering-net-zero-in-practiceodfjells-pragmatic-pathway-draws-strong-interest-at-imo/"}
            ],),
        CompanySpec(
            company_name="Maersk Tankers",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://maersktankers.com/"},
                {"page_type": "about-us", "url": "https://maersktankers.com/our-purpose"},
                {"page_type": "fleet", "url": "https://maersktankers.com/newsroom/maersk-tankers-and-partners-disclose-climate-impact-of-vessel-operations"},
                {"page_type": "sustainability", "url": "https://maersktankers.com/sustainability"},
                {"page_type": "environment", "url": "https://maersktankers.com/shipping-solutions"}
            ],),
        CompanySpec(
            company_name="Louis Dreyfus Armateurs",
            wikipedia_title="",
            website_pages=[
                {"page_type": "home", "url": "https://www.lda.fr/en/"},
                {"page_type": "about-us", "url": "https://www.lda.fr/en/the-group/"},
                {"page_type": "fleet", "url": "https://www.lda.fr/en/innovation-lda/culture-of-innovation/"},
                {"page_type": "sustainability", "url": "https://www.lda.fr/en/marine-industrial-solutions/renewable-marine-energy/"},
                {"page_type": "environment", "url": "https://www.lda.fr/en/commitments/environmental-policy/"}
            ],),
        
        # Add 14 more CompanySpec(...) entries here
    ]

    out: Dict[str, Any] = {}
    for spec in companies:
        out[spec.company_name] = scrape_company(spec)

    with open("shipping_companies_dataset.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(out)} companies to shipping_companies_dataset.json")


if __name__ == "__main__":
    main()
