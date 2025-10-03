#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
import time
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from analyze_tiktok_bio import analyze_tiktok_bio, BioAnalysis, extract_user_info

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

@dataclass
class TikTokCandidate:
    username: str
    exists: bool
    subscribers: int
    source: List[str]
    bio_analysis: Optional[BioAnalysis] = None
    raw_score: int = 0
    confidence: float = 0.0
    
    def to_dict(self):
        result = asdict(self)
        if self.bio_analysis:
            result['bio_analysis'] = self.bio_analysis.to_dict()
        return result

def quick_check_exists(username: str, delay: float = 1.0) -> bool:
    url = f"https://www.tiktok.com/@{username}"
    try:
        time.sleep(delay)
        r = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return r.status_code == 200
    except:
        return False

def check_tiktok_exists(username: str, delay: float = 1.0) -> Tuple[bool, int]:
    if not quick_check_exists(username, delay=delay):
        return False, 0
    
    try:
        user_info = extract_user_info(username, timeout=10)
        
        if not user_info:
            return False, 0
        
        followers = user_info.get('followers', 0)
        return True, followers
    except:
        return False, 0

def calculate_raw_score(candidate: TikTokCandidate) -> int:
    score = 0
    
    # score += len(candidate.source) * 10
    
    if candidate.subscribers >= 100000:
        score += 100
    elif candidate.subscribers >= 10000:
        score += 50
    elif candidate.subscribers >= 1000:
        score += 25
    elif candidate.subscribers >= 100:
        score += 5
    elif candidate.subscribers >= 1:
        score += 2
    
    if candidate.bio_analysis and candidate.bio_analysis.bio_found:
        if candidate.bio_analysis.mentions_depute:
            score += 10
        if candidate.bio_analysis.mentions_assemblee:
            score += 5
        if candidate.bio_analysis.mentions_party:
            score += 5
        if candidate.bio_analysis.verified:
            score += 50
    
    return score

def calculate_confidence(scores: np.ndarray) -> np.ndarray:
    """
    Calculate confidence scores for candidates.
    Assumes scores are already sorted in descending order (highest first).
    """
    if len(scores) == 0:
        return scores
    
    # Best score is first (already sorted)
    best_score = scores[0]
    
    # Quality factor: sigmoid centered at 60
    quality_factor = 1.0 / (1.0 + np.exp(-(best_score - 60) / 25))
    
    if len(scores) == 1:
        return np.array([0.30 + 0.65 * quality_factor])
    
    # Margin between best and second-best
    margin = scores[0] - scores[1]
    
    # Margin score: need substantial absolute margin
    margin_score = min(margin / 30.0, 1.0)  # Need 30+ point margin for max
    
    # Top confidence: both quality and margin must be good
    top_confidence = 0.25 + 0.70 * quality_factor * margin_score
    
    # Assign confidences: first gets top_confidence, rest split remaining
    confidences = np.zeros(len(scores))
    confidences[0] = top_confidence
    
    if len(scores) > 1:
        remaining_mass = 1.0 - top_confidence
        for i in range(1, len(scores)):
            confidences[i] = remaining_mass / (len(scores) - 1)
    
    return confidences

def process_deputy(deputy: Dict, delay: float = 1.0, show_details: bool = False) -> Tuple[Optional[TikTokCandidate], List[TikTokCandidate]]:
    name = deputy['name']
    legislature = deputy.get('Legislature', '')
    
    username_sources = {}
    
    for username in deputy.get('twitter_username', []):
        if username:
            if username not in username_sources:
                username_sources[username] = []
            username_sources[username].append('twitter')
    
    for username in deputy.get('websearch_username', []):
        if username:
            if username not in username_sources:
                username_sources[username] = []
            username_sources[username].append('websearch')
    
    for username in deputy.get('variant_username', []):
        if username:
            if username not in username_sources:
                username_sources[username] = []
            username_sources[username].append('variant')
    
    unique_usernames = [(username, sources) for username, sources in username_sources.items()]
    
    if not unique_usernames:
        return None, []
    
    candidates = []
    
    for username, sources in unique_usernames:
        exists, subscribers = check_tiktok_exists(username, delay=delay)
        
        if not exists:
            continue
        
        bio_analysis = None
        if subscribers >= 1:
            try:
                bio_analysis = analyze_tiktok_bio(username, timeout=10)
            except:
                pass
        
        candidate = TikTokCandidate(
            username=username,
            exists=True,
            subscribers=subscribers,
            source=sources,
            bio_analysis=bio_analysis
        )
        
        candidates.append(candidate)
    
    if not candidates:
        return None, []
    
    candidates_with_subs = [c for c in candidates if c.subscribers >= 1]
    
    if not candidates_with_subs:
        return candidates[0], [candidates[0]]
    
    for candidate in candidates_with_subs:
        candidate.raw_score = calculate_raw_score(candidate)
    
    # Sort by raw_score first (highest to lowest)
    sorted_candidates = sorted(candidates_with_subs, key=lambda c: c.raw_score, reverse=True)
    
    # Calculate confidences based on sorted scores
    scores = np.array([c.raw_score for c in sorted_candidates])
    confidences = calculate_confidence(scores)
    
    # Assign confidences to sorted candidates
    for i, candidate in enumerate(sorted_candidates):
        candidate.confidence = float(confidences[i])
    
    best_candidate = sorted_candidates[0]
    top_3 = sorted_candidates[:3]
    
    if show_details:
        print(f"\n{name} (Legislature {legislature}):")
        print(f"  Found {len(candidates_with_subs)} account(s) with subscribers")
        for c in top_3:
            sources_str = ','.join(c.source)
            print(f"    @{c.username}: {c.subscribers:,} subs, score={c.raw_score}, conf={c.confidence:.3f} [{sources_str}]")
    
    return best_candidate, top_3

def main():
    parser = argparse.ArgumentParser(description="Part 2: Find and verify TikTok accounts")
    parser.add_argument("--input", default="possible_usernames.json", help="Input JSON from Part 1")
    parser.add_argument("--output", default="tiktok_results.json", help="Output JSON file")
    parser.add_argument("--csv", help="Also save as CSV file")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--details", action="store_true", help="Show detailed scoring")
    parser.add_argument("--limit", type=int, help="Limit number of deputies to process")
    args = parser.parse_args()
    
    with open(args.input, 'r', encoding='utf-8') as f:
        deputies = json.load(f)
    
    if args.limit:
        deputies = deputies[:args.limit]
    
    print(f"Processing {len(deputies)} deputies...")
    print(f"Delay between requests: {args.delay}s\n")
    print("="*70)
    
    results = []
    
    for i, deputy in enumerate(deputies, 1):
        name = deputy['name']
        legislature = deputy.get('Legislature', '')
        
        print(f"[{i}/{len(deputies)}] {name}...", end=' ', flush=True)
        
        best, top_3 = process_deputy(deputy, delay=args.delay, show_details=args.details)
        
        if best:
            print(f"✓ @{best.username} ({best.subscribers:,} subs, conf={best.confidence:.2%})")
            
            top_3_data = []
            for candidate in top_3:
                top_3_data.append({
                    'username': candidate.username,
                    'subscribers': candidate.subscribers,
                    'raw_score': candidate.raw_score,
                    'confidence': candidate.confidence,
                    'sources': candidate.source,
                    'num_sources': len(candidate.source)
                })
            
            results.append({
                'name': name,
                'legislature': legislature,
                'best_match': {
                    'username': best.username,
                    'url': f"https://www.tiktok.com/@{best.username}",
                    'subscribers': best.subscribers,
                    'confidence': best.confidence,
                    'raw_score': best.raw_score,
                    'sources': best.source,
                    'num_sources': len(best.source),
                    'verified': best.bio_analysis.verified if best.bio_analysis else False,
                    'bio': best.bio_analysis.bio_text if best.bio_analysis else '',
                    'mentions_depute': best.bio_analysis.mentions_depute if best.bio_analysis else False,
                    'mentions_assemblee': best.bio_analysis.mentions_assemblee if best.bio_analysis else False,
                    'mentions_party': best.bio_analysis.mentions_party if best.bio_analysis else False,
                    'mentions_region': best.bio_analysis.mentions_region if best.bio_analysis else False,
                    'party_name': best.bio_analysis.party_name if best.bio_analysis else ''
                },
                'top_3_matches': top_3_data,
                'found': True
            })
        else:
            print("✗ Not found")
            
            results.append({
                'name': name,
                'legislature': legislature,
                'best_match': None,
                'top_3_matches': [],
                'found': False
            })
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    found_count = sum(1 for r in results if r['found'])
    confidences = [r['best_match']['confidence'] for r in results if r['found']]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    print("\n" + "="*70)
    print(f"\nResults saved to {args.output}")
    print(f"Found: {found_count} / {len(results)}")
    print(f"Average confidence: {avg_confidence:.2%}")
    
    if args.csv:
        csv_results = []
        for r in results:
            if r['found']:
                best = r['best_match']
                csv_results.append({
                    'name': r['name'],
                    'legislature': r['legislature'],
                    'tiktok_username': best['username'],
                    'tiktok_url': best['url'],
                    'subscribers': best['subscribers'],
                    'confidence': best['confidence'],
                    'raw_score': best['raw_score'],
                    'sources': ','.join(best['sources']),
                    'num_sources': best['num_sources'],
                    'verified': best['verified'],
                    'mentions_depute': best['mentions_depute'],
                    'mentions_party': best['mentions_party'],
                    'party_name': best['party_name'],
                    'bio': best['bio']
                })
            else:
                csv_results.append({
                    'name': r['name'],
                    'legislature': r['legislature'],
                    'tiktok_username': '',
                    'tiktok_url': '',
                    'subscribers': 0,
                    'confidence': 0.0,
                    'raw_score': 0,
                    'sources': '',
                    'num_sources': 0,
                    'verified': False,
                    'mentions_depute': False,
                    'mentions_party': False,
                    'party_name': '',
                    'bio': ''
                })
        
        df = pd.DataFrame(csv_results)
        df.to_csv(args.csv, index=False, encoding='utf-8')
        print(f"CSV also saved to {args.csv}")

if __name__ == "__main__":
    main()

