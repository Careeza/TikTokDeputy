#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Part 1: Generate possible TikTok usernames for French deputies

Sources:
1. Cross-reference with Twitter handles (DB_AN_twitter.csv)
2. Pattern-based generation (name variants)
3. Web search: DuckDuckGo/Bing for "{name} député tiktok"

Output: JSON with usernames separated by source for confidence scoring
"""
import argparse
import re
import time
import json
import os
import html as html_module
from pathlib import Path
from typing import List, Set, Dict
from urllib.parse import urlparse, parse_qs, urljoin
import unicodedata

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "DeputesTikTokSearch/1.0 (+research)",
    "Accept-Language": "fr,en;q=0.9"
}

TIKTOK_USERNAME_RE = re.compile(r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9._\-]+)", re.IGNORECASE)

def normalize_string(text: str) -> str:
    """Remove accents and convert to lowercase for comparison"""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return text.lower().strip()

def generate_pattern_variants(full_name: str) -> List[str]:
    """
    Generate username patterns from a name.
    Returns only the most common and useful patterns.
    """
    name = normalize_string(full_name)
    name = name.replace('-', ' ')
    parts = name.split()
    
    if len(parts) < 2:
        return [name.replace(" ", "")]
    
    first = parts[0]
    last_parts = parts[1:]
    last = "".join(last_parts)
    last_word = parts[-1]
    
    initials = "".join([p[0] for p in parts])
    first_initial = first[0]
    
    variants = [
        # Most common patterns on TikTok
        f"{first}{last}",              # firstlast - most common
        f"{first}.{last}",             # first.last - very common
        f"{first}_{last}",             # first_last - very common
        f"{first_initial}{last}",      # flast - common abbreviation
        f"{last}{first}",              # lastfirst - reversed
        f"{last}.{first}",             # last.first - reversed with dot
        f"{last}_{first}",             # last_first - reversed with underscore
        f"{first}{last}_officiel",     # with French "official" suffix
        f"{first_initial}{last}_officiel",  # abbreviated + official
    ]
    
    return list(dict.fromkeys(variants))

def get_twitter_variants(name: str, twitter_df: pd.DataFrame) -> List[str]:
    """
    Get Twitter usernames for this deputy from the Twitter database.
    Twitter handles are often similar to TikTok handles.
    """
    variants = []

    # Try exact match first
    # remove white spaces and accents
    matched = twitter_df[twitter_df['Nom.C'] == normalize_string(name)]

    
    # If no exact match, try case-insensitive
    if matched.empty:
        matched = twitter_df[twitter_df['Nom.C'].str.lower().str.strip() == name.lower().strip()]
    
    if not matched.empty:
        row = matched.iloc[0]
        
        # Get twitter handles from all columns
        twitter = row.get('twitter', '')
        twitter_2 = row.get('twitter_2', '')
        twitter_wiki = row.get('twitter_wiki_NE', '')
        
        for handle in [twitter, twitter_2, twitter_wiki]:
            if pd.notna(handle) and handle and str(handle).strip():
                # Clean the handle (remove @, convert to lowercase)
                clean = str(handle).strip().lstrip('@').lower()
                if clean and len(clean) > 1:
                    variants.append(clean)
                    # Also try without underscores (common variation)
                    no_underscore = clean.replace('_', '')
                    if no_underscore != clean and len(no_underscore) > 1:
                        variants.append(no_underscore)
                    # And with dots instead of underscores
                    with_dots = clean.replace('_', '.')
                    if with_dots != clean and len(with_dots) > 1:
                        variants.append(with_dots)
    return variants

def bing_search(query: str, top_n: int = 3, timeout: int = 20) -> List[Dict]:
    """Search using Bing API if BING_API_KEY env var is set"""
    api_key = os.environ.get("BING_API_KEY", "").strip()
    if not api_key:
        return []
    
    try:
        url = "https://api.bing.microsoft.com/v7.0/search"
        params = {"q": query, "count": top_n, "mkt": "fr-FR", "textDecorations": False, "safeSearch": "Off"}
        r = requests.get(url, headers={**HEADERS, "Ocp-Apim-Subscription-Key": api_key}, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        web_pages = data.get("webPages", {}).get("value", []) if isinstance(data, dict) else []
        return [{"title": item.get("name", ""), "url": item.get("url", "")} for item in web_pages[:top_n]]
    except:
        return []

def ddg_search(query: str, top_n: int = 3, timeout: int = 20) -> List[Dict]:
    """Search using DuckDuckGo HTML (no API key needed)"""
    try:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        
        for a in soup.select("a.result__a")[:top_n]:
            href = a.get("href", "")
            # DuckDuckGo proxies links - extract real URL
            real_url = href
            parsed = urlparse(href)
            if parsed.path.startswith("/l/"):
                qs = parse_qs(parsed.query or "")
                uddg = qs.get("uddg", [None])[0]
                if uddg:
                    real_url = html_module.unescape(uddg)
            
            title = a.get_text(strip=True)
            results.append({"title": title, "url": real_url})
        
        return results
    except:
        return []

def extract_tiktok_from_page(url: str, timeout: int = 10) -> List[str]:
    """Fetch a page and extract TikTok usernames from links"""
    usernames = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        
        # Find all TikTok URLs in the page
        matches = TIKTOK_USERNAME_RE.findall(r.text)
        for username in matches:
            clean = username.strip().lstrip("@").lower()
            if clean and len(clean) > 2:
                usernames.append(clean)
    except:
        pass
    
    return usernames

def search_web_for_tiktok(name: str, sleep: float = 1.0) -> List[str]:
    """
    Search web for "{name} député tiktok" using Bing or DuckDuckGo.
    Extract TikTok usernames from search results.
    """
    variants = set()
    query = f"{name} député tiktok"
    
    try:
        # Try Bing first (if API key available), fallback to DuckDuckGo
        results = bing_search(query, top_n=3, timeout=10)
        if not results:
            results = ddg_search(query, top_n=3, timeout=10)
        
        time.sleep(sleep)  # Be polite
        
        for result in results:
            url = result.get("url", "")
            
            # Check if URL itself is a TikTok link
            match = TIKTOK_USERNAME_RE.search(url)
            if match:
                username = match.group(1).strip().lstrip("@").lower()
                if username and len(username) > 2:
                    variants.add(username)
            else:
                # Fetch page and look for TikTok links inside
                page_usernames = extract_tiktok_from_page(url, timeout=10)
                variants.update(page_usernames)
                time.sleep(0.5)  # Small delay between page fetches
        
    except Exception as e:
        # Silently fail - web search is optional
        pass
    
    return list(variants)

def generate_all_usernames(name: str, twitter_df: pd.DataFrame, use_web_search: bool = True, sleep: float = 1.0) -> Dict[str, List[str]]:
    """
    Generate all possible TikTok usernames from all sources.
    Returns dict with usernames separated by source for confidence scoring.
    
    Returns:
        {
            'twitter_username': [...],
            'variant_username': [...],
            'websearch_username': [...]
        }
    """
    # Source 1: Twitter handles (high priority)
    twitter_variants = get_twitter_variants(name, twitter_df)
    
    # Source 2: Pattern-based generation
    pattern_variants = generate_pattern_variants(name)
    
    # Source 3: Web search
    web_variants = []
    if use_web_search:
        web_variants = search_web_for_tiktok(name, sleep)
    
    # Clean and deduplicate within each source
    twitter_clean = list(dict.fromkeys([v for v in twitter_variants if v and len(v) > 1]))
    pattern_clean = list(dict.fromkeys([v for v in pattern_variants if v and len(v) > 1]))
    web_clean = list(dict.fromkeys([v for v in web_variants if v and len(v) > 1]))
    
    return {
        'twitter_username': twitter_clean,
        'variant_username': pattern_clean,
        'websearch_username': web_clean
    }

def main():
    parser = argparse.ArgumentParser(description="Generate possible TikTok usernames for deputies")
    parser.add_argument("--in", dest="input_path", required=True, help="Input CSV with deputy names")
    parser.add_argument("--twitter", dest="twitter_path", required=True, help="Twitter database CSV (DB_AN_twitter.csv)")
    parser.add_argument("--out", dest="output_path", default="possible_usernames.json", help="Output JSON path")
    parser.add_argument("--sleep", dest="sleep", type=float, default=1.0, help="Seconds between web searches (default: 1.0)")
    parser.add_argument("--no-web-search", dest="no_web", action="store_true", help="Skip web search (faster but less complete)")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    twitter_path = Path(args.twitter_path)
    output_path = Path(args.output_path)

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return
    
    if not twitter_path.exists():
        print(f"Twitter database not found: {twitter_path}")
        return

    # Load data
    deputies_df = pd.read_csv(input_path)
    twitter_df = pd.read_csv(twitter_path)
    # convert Nom.C to normalize_string
    twitter_df['Nom.C'] = twitter_df['Nom.C'].apply(normalize_string)
    
    print(f"\nLoaded {len(deputies_df)} deputies")
    print(f"Loaded {len(twitter_df)} Twitter accounts\n")
    print(f"{'='*70}")
    print("Generating username variants...\n")
    
    results = []
    
    for idx, row in deputies_df.iterrows():
        name = row.get('Nom', '')
        legis = row.get('Legislature', '')
        
        print(f"[{idx+1}/{len(deputies_df)}] {name}")
        
        # Generate all possible usernames separated by source
        usernames_by_source = generate_all_usernames(
            name, 
            twitter_df, 
            use_web_search=not args.no_web,
            sleep=args.sleep
        )
        
        # Count total unique usernames
        all_usernames = set()
        all_usernames.update(usernames_by_source['twitter_username'])
        all_usernames.update(usernames_by_source['variant_username'])
        all_usernames.update(usernames_by_source['websearch_username'])
        total_count = len(all_usernames)
        
        print(f"    Twitter: {len(usernames_by_source['twitter_username'])}", end="")
        if usernames_by_source['twitter_username']:
            print(f" - {', '.join(usernames_by_source['twitter_username'][:3])}")
        else:
            print()
        
        print(f"    Patterns: {len(usernames_by_source['variant_username'])}")
        
        print(f"    Web search: {len(usernames_by_source['websearch_username'])}", end="")
        if usernames_by_source['websearch_username']:
            print(f" - {', '.join(usernames_by_source['websearch_username'][:3])}")
        else:
            print()
        
        print(f"    Total unique: {total_count}")
        
        results.append({
            'name': name,
            'Legislature': legis,
            'twitter_username': usernames_by_source['twitter_username'],
            'variant_username': usernames_by_source['variant_username'],
            'websearch_username': usernames_by_source['websearch_username']
        })
        
        print()
    
    # Save results as JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Calculate statistics
    total_twitter = sum(len(r['twitter_username']) for r in results)
    total_patterns = sum(len(r['variant_username']) for r in results)
    total_web = sum(len(r['websearch_username']) for r in results)
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Processed: {len(results)} deputies")
    print(f"Average by source:")
    print(f"  - Twitter: {total_twitter/len(results):.1f} per deputy")
    print(f"  - Patterns: {total_patterns/len(results):.1f} per deputy")
    print(f"  - Web search: {total_web/len(results):.1f} per deputy")
    print(f"Saved to: {output_path}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()

