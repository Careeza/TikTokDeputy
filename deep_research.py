import os
import json
from typing import List, Dict
from openai import OpenAI

MODEL = "gpt-4.1-mini"

SYSTEM = """\
You are a rigorous OSINT-style researcher specialized in finding and verifying social media accounts. You MUST perform deep web research before answering.

Hard rules:
- DO NOT guess or make assumptions. Always research across multiple credible sources.
- Priority sources (in order): 
  1. TikTok official profiles
  2. X/Twitter accounts (often similar usernames)
  3. Official personal/party websites
  4. Assemblée nationale (assemblee-nationale.fr)
  5. Reputable press articles and news sources
  6. LinkedIn, Instagram, Facebook (may indicate TikTok presence)
- Cross-reference information across multiple sources to verify authenticity.
- If a TikTok account is found or confidently inferred via cross-source patterns, propose up to 5 MOST PROBABLE TikTok usernames.
- If no direct TikTok is found, infer plausible usernames from verified cross-platform handles (especially X/Twitter) and common username patterns.
- NEVER include '@' at the start of usernames.
- Username constraints: Only letters, numbers, underscores, and periods. No spaces, hyphens, or emojis. Maximum 24 characters.
- Username preferences (in order of likelihood):
  1. Exact verified username from another platform
  2. firstname.lastname (most common format)
  3. firstname_lastname
  4. firstnamelastname (no separator)
  5. initials+lastname (e.g., aleaument)
  6. lastname.firstname
- Add tiny disambiguators ONLY if you find evidence they use them (e.g., 'fr', 'officiel', 'depute', year, or a single digit).
- Consider name variations: nicknames, shortened names, middle names.
- For politicians, check if they use political titles or party abbreviations in usernames.

Output format:
Return STRICT JSON complying with the provided JSON schema. No commentary outside the JSON structure.
"""

USER_PROMPT_TEMPLATE = """\
You will receive a list of French deputies' full names. For EACH name:
1) Perform comprehensive deep web research:
   - Search for "[name] député tiktok"
   - Search for "[name] tiktok france"
   - Look for their official websites and social media links
   - Check X/Twitter accounts (username often similar to TikTok)
   - Check Assemblée nationale profiles
   - Look for press articles mentioning their TikTok presence
2) Produce the 5 MOST PROBABLE TikTok usernames (no '@') in best-first order based on your research.
3) If there is a confirmed TikTok account found in your research, it MUST appear as #1.
4) Rank remaining suggestions by likelihood based on verified cross-platform handles and common patterns.

Names:
{names_block}

Return STRICT JSON matching the schema. No extra fields, no notes, no explanations outside the JSON.
"""

def run(names: List[str], out_path: str):
    """
    Run deep research for TikTok username suggestions.
    
    Args:
        names: List of full names to research
        out_path: Path to save the JSON output
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Build the user task
    names_block = "\n".join(f"- {n}" for n in names)
    user_prompt = USER_PROMPT_TEMPLATE.format(names_block=names_block)

    print(f"Researching {len(names)} names using {MODEL}...")
    print("This may take a few minutes as the model performs web research...\n")

    # Ask the model with web search enabled and a strict JSON schema
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        tools=[{"type": "web_search"}],  # require web research
        tool_choice="auto",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "tiktok_username_batch",
                "schema": {
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "top_5": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 5,
                                        "maxItems": 5
                                    }
                                },
                                "required": ["name", "top_5"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["results"],
                    "additionalProperties": False
                },
                "strict": True
            }
        },
    )

    # Extract JSON string from the Responses API payload
    content = resp.output[0].content[0].text
    data = json.loads(content)

    # Defensive cleanup: strip any leading '@' just in case and validate format
    for item in data.get("results", []):
        cleaned = []
        for username in item.get("top_5", []):
            # Remove '@' and any invalid characters
            clean = username.lstrip("@").strip()
            # Ensure only valid characters
            clean = "".join(c for c in clean if c.isalnum() or c in "._")
            # Limit length to 24 chars
            clean = clean[:24]
            if clean and len(clean) >= 2:  # Minimum 2 characters
                cleaned.append(clean)
        
        # Ensure exactly 5 usernames (pad if necessary)
        while len(cleaned) < 5:
            cleaned.append("")
        item["top_5"] = cleaned[:5]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved results for {len(data.get('results', []))} names to {out_path}\n")
    print("Results:")
    print("="*70)
    for item in data.get("results", []):
        print(f"\n{item.get('name', 'Unknown')}:")
        for i, username in enumerate(item.get("top_5", []), 1):
            if username:
                print(f"  {i}. @{username}")
    print("\n" + "="*70)

    return data

def main():
    """Test main with sample deputy names"""
    test_names = [
        "Antoine Léaument",
        "Nadège Abomangoli",
        "Ludovic Pajot",
        "Typhanie Degois"
    ]
    
    output_path = "tiktok_usernames_test.json"
    
    print("="*70)
    print("Deep Research TikTok Username Finder")
    print("="*70)
    print(f"\nSearching for TikTok accounts of {len(test_names)} French deputies:")
    for name in test_names:
        print(f"  - {name}")
    print()
    
    run(test_names, output_path)

if __name__ == "__main__":
    main()
