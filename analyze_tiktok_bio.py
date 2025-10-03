#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
import requests
import unicodedata
from typing import Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class BioAnalysis:
    username: str
    bio_text: str
    bio_found: bool
    mentions_depute: bool
    mentions_party: bool
    mentions_region: bool
    mentions_assemblee: bool
    party_name: Optional[str] = None
    followers: int = 0
    verified: bool = False
    
    def to_dict(self):
        return asdict(self)

def normalize_string(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return text.lower().strip()

def extract_user_info(username: str, timeout: int = 10) -> Dict:
    url = f"https://www.tiktok.com/@{username}"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return {}
        
        bio = ''
        followers = 0
        verified = False
        
        for pattern in [r'"signature":"([^"]*)"', r'"bioDescription"[:\\s]*"([^"]*)"']:
            match = re.search(pattern, r.text)
            if match:
                bio_candidate = match.group(1)
                try:
                    bio_candidate = json.loads(f'"{bio_candidate}"')
                except:
                    bio_candidate = bio_candidate.replace('\\/', '/').replace('\\n', ' ')
                if len(bio_candidate) > 3 and 'signature' not in bio_candidate.lower():
                    bio = bio_candidate.strip()
                    break
        
        for pattern in [r'"followerCount":(\d+)', r'"fans":(\d+)']:
            match = re.search(pattern, r.text)
            if match:
                followers = int(match.group(1))
                break
        
        if '"verified":true' in r.text or '"isVerified":true' in r.text:
            verified = True
        
        return {'bio': bio, 'followers': followers, 'verified': verified}
    except:
        return {}

def analyze_bio_keywords(bio_text: str) -> Dict[str, any]:
    if not bio_text:
        return {
            'mentions_depute': False,
            'mentions_party': False,
            'mentions_region': False,
            'mentions_assemblee': False,
            'party_name': None
        }
    
    bio_normalized = normalize_string(bio_text)
    
    depute_keywords = ['depute', 'deputee', 'parlementaire', 'elu', 'elue']
    mentions_depute = any(kw in bio_normalized for kw in depute_keywords)
    
    assemblee_keywords = ['assemblee nationale', 'assemblee', 'palais bourbon']
    mentions_assemblee = any(kw in bio_normalized for kw in assemblee_keywords)
    
    parties = {
        'LFI': ['lfi', 'france insoumise', 'la france insoumise', 'insoumis'],
        'Renaissance': ['renaissance', 'renew', 'ensemble'],
        'RN': ['rn', 'rassemblement national', 'front national', 'fn'],
        'LR': ['lr', 'les republicains', 'republicains'],
        'PS': ['ps', 'parti socialiste', 'socialiste'],
        'EELV': ['eelv', 'ecologiste', 'europe ecologie', 'verts'],
        'PCF': ['pcf', 'communiste', 'parti communiste'],
        'Modem': ['modem', 'democrate'],
        'Horizons': ['horizons'],
        'UDI': ['udi', 'union des democrates']
    }
    
    detected_party = None
    for party_name, keywords in parties.items():
        if any(kw in bio_normalized for kw in keywords):
            detected_party = party_name
            break
    
    region_keywords = [
        'circonscription', 'departement', 'region', 'territoire',
        'seine', 'paris', 'lyon', 'marseille', 'nord', 'sud',
        'val-de-marne', 'essonne', 'hauts-de-seine', 'yvelines'
    ]
    mentions_region = any(kw in bio_normalized for kw in region_keywords)
    
    return {
        'mentions_depute': mentions_depute or mentions_assemblee,
        'mentions_party': detected_party is not None,
        'mentions_region': mentions_region,
        'mentions_assemblee': mentions_assemblee,
        'party_name': detected_party
    }

def analyze_tiktok_bio(username: str, timeout: int = 10) -> BioAnalysis:
    username = username.strip().lstrip('@').lower()
    
    try:
        user_info = extract_user_info(username, timeout=timeout)
        bio_text = user_info.get('bio', '')
        
        if not bio_text:
            return BioAnalysis(
                username=username,
                bio_text="",
                bio_found=False,
                mentions_depute=False,
                mentions_party=False,
                mentions_region=False,
                mentions_assemblee=False,
                followers=user_info.get('followers', 0),
                verified=user_info.get('verified', False)
            )
        
        analysis = analyze_bio_keywords(bio_text)
        
        return BioAnalysis(
            username=username,
            bio_text=bio_text,
            bio_found=True,
            mentions_depute=analysis['mentions_depute'],
            mentions_party=analysis['mentions_party'],
            mentions_region=analysis['mentions_region'],
            mentions_assemblee=analysis['mentions_assemblee'],
            party_name=analysis['party_name'],
            followers=user_info.get('followers', 0),
            verified=user_info.get('verified', False)
        )
    except Exception as e:
        return BioAnalysis(
            username=username,
            bio_text="",
            bio_found=False,
            mentions_depute=False,
            mentions_party=False,
            mentions_region=False,
            mentions_assemblee=False
        )

def main():
    parser = argparse.ArgumentParser(description="Analyze TikTok bio for political indicators")
    parser.add_argument("username", help="TikTok username (with or without @)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = analyze_tiktok_bio(args.username, timeout=args.timeout)
    
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Username: @{result.username}")
        print(f"Followers: {result.followers:,}")
        print(f"Verified: {result.verified}")
        print(f"Bio found: {result.bio_found}")
        
        if result.bio_found:
            print(f'\nBio: "{result.bio_text}"')
            print(f"\nMentions député: {result.mentions_depute}")
            print(f"Mentions Assemblée: {result.mentions_assemblee}")
            print(f"Mentions party: {result.mentions_party}")
            if result.party_name:
                print(f"  → {result.party_name}")
            print(f"Mentions region: {result.mentions_region}")

if __name__ == "__main__":
    main()
