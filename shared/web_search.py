"""
🔍 Web Search Tool v2
Shared utility for all agents that need to search the web.
Fixed: DDG package, Reddit rate limits, GitHub parsing, diverse search.
"""

import asyncio
import json
import os
import re
import warnings
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus


class WebSearchTool:
    """
    Web search across multiple free sources:
    1. DuckDuckGo (via ddgs package)
    2. Hacker News (free Algolia API)
    3. Reddit (JSON API, no auth)
    4. GitHub Trending (HTML scrape)
    """

    def __init__(self):
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    # ========================================
    # DuckDuckGo (using new ddgs package)
    # ========================================

    async def search_ddg(self, query: str, max_results: int = 10) -> list[dict]:
        """Search DuckDuckGo — runs sync ddgs in thread pool"""
        try:
            loop = asyncio.get_event_loop()

            def _search():
                try:
                    from ddgs import DDGS
                except ImportError:
                    # Fallback to old package name
                    from duckduckgo_search import DDGS
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with DDGS() as ddgs:
                        return list(ddgs.text(query, max_results=max_results))

            raw = await loop.run_in_executor(None, _search)
            results = []
            for r in raw:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "source": "duckduckgo",
                })
            return results
        except Exception as e:
            print(f"   [DDG error: {e}]")
            return []

    # ========================================
    # Hacker News (Free Algolia API)
    # ========================================

    async def search_hackernews(self, query: str, max_results: int = 10,
                                 time_range: str = "week") -> list[dict]:
        """
        Search Hacker News via Algolia API (100% free, no key needed).
        time_range: 'day', 'week', 'month', 'year'
        """
        session = await self._get_session()

        # Calculate numeric filter for time range
        import time as _time
        now = int(_time.time())
        ranges = {"day": 86400, "week": 604800, "month": 2592000, "year": 31536000}
        since = now - ranges.get(time_range, 604800)

        url = (
            f"https://hn.algolia.com/api/v1/search?"
            f"query={quote_plus(query)}&tags=story"
            f"&numericFilters=created_at_i>{since}"
            f"&hitsPerPage={max_results}"
        )

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for hit in data.get("hits", []):
                        results.append({
                            "title": hit.get("title", ""),
                            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            "points": hit.get("points", 0),
                            "comments": hit.get("num_comments", 0),
                            "author": hit.get("author", ""),
                            "created_at": hit.get("created_at", ""),
                            "source": "hackernews",
                        })
                    return results
        except Exception as e:
            print(f"   [HN search error: {e}]")
        return []

    async def get_hn_front_page(self, limit: int = 30) -> list[dict]:
        """Get current Hacker News front page stories"""
        session = await self._get_session()
        url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [{
                        "title": hit.get("title", ""),
                        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                        "points": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                        "source": "hackernews_frontpage",
                    } for hit in data.get("hits", [])]
        except Exception as e:
            print(f"   [HN frontpage error: {e}]")
        return []

    # ========================================
    # Reddit (JSON API, no auth needed)
    # ========================================

    async def search_reddit(self, query: str, subreddit: str = "all",
                             sort: str = "relevance", time_filter: str = "month",
                             limit: int = 10) -> list[dict]:
        """
        Search Reddit via public JSON API.
        Uses month time filter (wider net) and proper User-Agent.
        Adds small delay between calls to avoid rate limiting.
        """
        session = await self._get_session()

        if subreddit == "all":
            url = (
                f"https://www.reddit.com/search.json?"
                f"q={quote_plus(query)}&sort={sort}&t={time_filter}&limit={limit}"
            )
        else:
            url = (
                f"https://www.reddit.com/r/{subreddit}/search.json?"
                f"q={quote_plus(query)}&sort={sort}&t={time_filter}"
                f"&restrict_sr=on&limit={limit}"
            )

        try:
            # Small delay to respect rate limits
            await asyncio.sleep(0.5)

            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for child in data.get("data", {}).get("children", []):
                        post = child.get("data", {})
                        results.append({
                            "title": post.get("title", ""),
                            "url": f"https://reddit.com{post.get('permalink', '')}",
                            "subreddit": post.get("subreddit", ""),
                            "score": post.get("score", 0),
                            "comments": post.get("num_comments", 0),
                            "selftext": post.get("selftext", "")[:500],
                            "created_utc": post.get("created_utc", 0),
                            "source": "reddit",
                        })
                    return results
                elif resp.status == 429:
                    print(f"   [Reddit rate limited on r/{subreddit}]")
                    await asyncio.sleep(3)
        except Exception as e:
            print(f"   [Reddit error r/{subreddit}: {e}]")
        return []

    async def get_reddit_hot(self, subreddit: str, limit: int = 10) -> list[dict]:
        """Get hot posts from a subreddit (no search query needed)"""
        session = await self._get_session()
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

        try:
            await asyncio.sleep(0.5)
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for child in data.get("data", {}).get("children", []):
                        post = child.get("data", {})
                        if post.get("stickied"):
                            continue
                        results.append({
                            "title": post.get("title", ""),
                            "url": f"https://reddit.com{post.get('permalink', '')}",
                            "subreddit": post.get("subreddit", subreddit),
                            "score": post.get("score", 0),
                            "comments": post.get("num_comments", 0),
                            "selftext": post.get("selftext", "")[:500],
                            "source": "reddit_hot",
                        })
                    return results
        except Exception:
            pass
        return []

    # ========================================
    # GitHub Trending
    # ========================================

    async def get_github_trending(self, language: str = "", since: str = "weekly") -> list[dict]:
        """Scrape GitHub trending page — uses h2>a href pattern (confirmed working)"""
        session = await self._get_session()
        lang_path = f"/{language}" if language else ""
        url = f"https://github.com/trending{lang_path}?since={since}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    html = await resp.text()

                    # Primary pattern: <h2 ...> <a href="/org/repo">
                    repo_links = re.findall(
                        r'<h2[^>]*>\s*<a[^>]*href="(/[^"]+)"', html, re.DOTALL
                    )

                    # Extract descriptions (p tags after h2)
                    descriptions = re.findall(
                        r'<p class="[^"]*col-[^"]*">\s*(.*?)\s*</p>', html, re.DOTALL
                    )

                    # Extract star counts
                    stars = re.findall(
                        r'class="d-inline-block float-sm-right">\s*.*?(\d[\d,]*)\s*stars\s+today',
                        html, re.DOTALL | re.IGNORECASE
                    )
                    if not stars:
                        stars = re.findall(r'(\d[\d,]*)\s*stars today', html, re.IGNORECASE)

                    results = []
                    seen = set()
                    for i, repo_path in enumerate(repo_links):
                        clean = repo_path.strip().rstrip("/")
                        parts = clean.lstrip("/").split("/")
                        if len(parts) != 2:
                            continue
                        if clean in seen:
                            continue
                        seen.add(clean)

                        desc = ""
                        if i < len(descriptions):
                            desc = re.sub(r'\s+', ' ', descriptions[i]).strip()

                        today_stars = 0
                        if i < len(stars):
                            today_stars = int(stars[i].replace(",", ""))

                        results.append({
                            "repo": clean.lstrip("/"),
                            "url": f"https://github.com{clean}",
                            "description": desc[:200],
                            "stars_today": today_stars,
                            "language": language or "mixed",
                            "source": "github_trending",
                        })
                        if len(results) >= 15:
                            break
                    return results
        except Exception as e:
            print(f"   [GitHub trending error: {e}]")
        return []

    # ========================================
    # Unified Search
    # ========================================

    async def search_all(self, query: str, max_per_source: int = 5) -> list[dict]:
        """Search across all available sources"""
        tasks = [
            self.search_ddg(query, max_results=max_per_source),
            self.search_hackernews(query, max_results=max_per_source),
            self.search_reddit(query, limit=max_per_source),
        ]

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        all_results = []
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)

        return all_results
