"""
Script to load initial data from tiktok_results.json into the database

WARNING: This script will DELETE all existing data in the database and reload it from the JSON file.
If you have made manual verifications, they will be lost.
Use this only for initial setup or when you want to completely refresh the data.
"""
import json
from models import Deputy, SessionLocal, init_db

def load_json_data():
    # Initialize database
    init_db()
    
    # Create session
    db = SessionLocal()
    
    # Clear existing data (THIS DELETES ALL CURRENT DATA INCLUDING VERIFICATIONS)
    print("WARNING: Deleting all existing data from database...")
    db.query(Deputy).delete()
    db.commit()
    
    # Load JSON data
    with open("tiktok_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Insert deputies
    for item in data:
        best_match = item.get("best_match", {})
        
        # Enrich top_3_matches with bio and mentions data from best_match
        top_matches = item.get("top_3_matches", [])
        enriched_matches = []
        
        for match in top_matches:
            enriched_match = match.copy()
            
            # If this match username equals the best_match username, add the bio/mentions data
            if match.get("username") == best_match.get("username"):
                enriched_match["bio"] = best_match.get("bio", "")
                enriched_match["verified"] = best_match.get("verified", False)
                enriched_match["mentions_depute"] = best_match.get("mentions_depute", False)
                enriched_match["mentions_assemblee"] = best_match.get("mentions_assemblee", False)
                enriched_match["mentions_party"] = best_match.get("mentions_party", False)
                enriched_match["mentions_region"] = best_match.get("mentions_region", False)
                enriched_match["party_name"] = best_match.get("party_name", "")
            else:
                # For non-best matches, set default values
                enriched_match["bio"] = ""
                enriched_match["verified"] = False
                enriched_match["mentions_depute"] = False
                enriched_match["mentions_assemblee"] = False
                enriched_match["mentions_party"] = False
                enriched_match["mentions_region"] = False
                enriched_match["party_name"] = ""
            
            enriched_matches.append(enriched_match)
        
        deputy = Deputy(
            name=item["name"],
            legislatures=item.get("legislatures", []),
            found=item.get("found", False),
            
            # Best match fields
            best_match_username=best_match.get("username"),
            best_match_url=best_match.get("url"),
            best_match_subscribers=best_match.get("subscribers"),
            best_match_confidence=best_match.get("confidence"),
            best_match_raw_score=best_match.get("raw_score"),
            best_match_sources=best_match.get("sources"),
            best_match_num_sources=best_match.get("num_sources"),
            best_match_verified=best_match.get("verified"),
            best_match_bio=best_match.get("bio"),
            best_match_mentions_depute=best_match.get("mentions_depute"),
            best_match_mentions_assemblee=best_match.get("mentions_assemblee"),
            best_match_mentions_party=best_match.get("mentions_party"),
            best_match_mentions_region=best_match.get("mentions_region"),
            best_match_party_name=best_match.get("party_name"),
            
            # Top matches with enriched data
            top_3_matches=enriched_matches,
            
            # Initialize new fields
            username_tested=[],
            username_to_test=[],
            verified_by_human=False,
            human_verified_username=None,
            no_tiktok_account=False
        )
        
        db.add(deputy)
    
    db.commit()
    print(f"Loaded {len(data)} deputies into the database")
    db.close()


if __name__ == "__main__":
    load_json_data()

