from urllib.parse import urlparse, parse_qs, unquote, urlencode
from bs4 import BeautifulSoup


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # Bing tracking: /ck/a?...&u=base64(real_url)
    if parsed.path.startswith("/ck/"):
        raw = qs.get("u") or qs.get("uddg") or qs.get("ru") or qs.get("href") or []
        if raw:
            return unquote(raw[0])
        # Try to extract from adlt/stuff
        for key in qs:
            val = qs[key][0]
            if val.startswith("http"):
                return unquote(val)
    # Bing redirect: /l/? , /lk/? , /d/
    if url.startswith("/l/?") or url.startswith("/lk/?") or url.startswith("/d/"):
        raw = qs.get("uddg") or qs.get("ru") or qs.get("href") or []
        if raw:
            return unquote(raw[0])
    return url


def parse_bing(html: str, max_results: int) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        link_el = li.select_one("h2 a")
        snippet = li.select_one(".b_caption p")
        if link_el:
            results.append({
                "title": link_el.get_text(strip=True),
                "url": _clean_url(link_el.get("href", "")),
                "description": snippet.get_text(strip=True) if snippet else "",
            })
        if len(results) >= max_results:
            break
    return results


def parse_ddg(html: str, max_results: int) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for div in soup.select("div.result"):
        title_el = div.select_one("h2.result__title a")
        snippet_el = div.select_one(".result__snippet")
        if title_el:
            results.append({
                "title": title_el.get_text(strip=True),
                "url": _clean_url(title_el.get("href", "")),
                "description": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        if len(results) >= max_results:
            break
    return results


def parse_tavily(data: dict, max_results: int) -> list:
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("content", ""),
        })
        if len(results) >= max_results:
            break
    return results
