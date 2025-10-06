from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import io
import csv

from models import Deputy, get_db, init_db

app = FastAPI(title="TikTok Deputy Verification")

# Initialize database
init_db()


# Pydantic models for API
class DeputyResponse(BaseModel):
    id: int
    name: str
    legislatures: List[str]
    found: bool
    best_match_username: Optional[str] = None
    best_match_url: Optional[str] = None
    best_match_subscribers: Optional[int] = None
    best_match_confidence: Optional[float] = None
    best_match_raw_score: Optional[int] = None
    best_match_sources: Optional[List[str]] = None
    best_match_num_sources: Optional[int] = None
    best_match_verified: Optional[bool] = None
    best_match_bio: Optional[str] = None
    best_match_mentions_depute: Optional[bool] = None
    best_match_mentions_assemblee: Optional[bool] = None
    best_match_mentions_party: Optional[bool] = None
    best_match_mentions_region: Optional[bool] = None
    best_match_party_name: Optional[str] = None
    top_3_matches: Optional[List[dict]] = None
    username_tested: Optional[List[str]] = []
    username_to_test: Optional[List[str]] = []
    verified_by_human: bool = False
    human_verified_username: Optional[str] = None
    no_tiktok_account: bool = False

    class Config:
        from_attributes = True


class VerificationUpdate(BaseModel):
    verified_by_human: bool
    human_verified_username: Optional[str] = None
    no_tiktok_account: Optional[bool] = None


class ManualAccountAdd(BaseModel):
    tiktok_url: str


class UsernameUpdate(BaseModel):
    username_tested: Optional[List[str]] = None
    username_to_test: Optional[List[str]] = None


# API Routes
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


@app.post("/api/initialize-database")
async def initialize_database(db: Session = Depends(get_db)):
    """Initialize database from JSON file - only use once on deployment"""
    import json
    
    # Check if already initialized
    count = db.query(Deputy).count()
    if count > 0:
        return {"message": f"Database already initialized with {count} deputies", "already_initialized": True}
    
    # Load from JSON
    try:
        with open("tiktok_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Insert deputies (same logic as load_data.py)
        for item in data:
            best_match = item.get("best_match", {})
            
            # Enrich top_3_matches with bio and mentions data from best_match
            top_matches = item.get("top_3_matches", [])
            enriched_matches = []
            
            for match in top_matches:
                enriched_match = match.copy()
                
                if match.get("username") == best_match.get("username"):
                    enriched_match["bio"] = best_match.get("bio", "")
                    enriched_match["verified"] = best_match.get("verified", False)
                    enriched_match["mentions_depute"] = best_match.get("mentions_depute", False)
                    enriched_match["mentions_assemblee"] = best_match.get("mentions_assemblee", False)
                    enriched_match["mentions_party"] = best_match.get("mentions_party", False)
                    enriched_match["mentions_region"] = best_match.get("mentions_region", False)
                    enriched_match["party_name"] = best_match.get("party_name", "")
                else:
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
                top_3_matches=enriched_matches,
                username_tested=[],
                username_to_test=[],
                verified_by_human=False,
                human_verified_username=None,
                no_tiktok_account=False
            )
            
            db.add(deputy)
        
        db.commit()
        return {"message": f"Successfully loaded {len(data)} deputies into the database", "count": len(data)}
    
    except Exception as e:
        return {"error": str(e)}, 500


@app.post("/api/initialize-with-verifications")
async def initialize_with_verifications(db: Session = Depends(get_db)):
    """Initialize database from JSON and apply verifications from CSV"""
    import json
    import csv
    
    try:
        # Step 1: Clear existing data
        db.query(Deputy).delete()
        db.commit()
        
        # Step 2: Load deputies from JSON
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
                
                if match.get("username") == best_match.get("username"):
                    enriched_match["bio"] = best_match.get("bio", "")
                    enriched_match["verified"] = best_match.get("verified", False)
                    enriched_match["mentions_depute"] = best_match.get("mentions_depute", False)
                    enriched_match["mentions_assemblee"] = best_match.get("mentions_assemblee", False)
                    enriched_match["mentions_party"] = best_match.get("mentions_party", False)
                    enriched_match["mentions_region"] = best_match.get("mentions_region", False)
                    enriched_match["party_name"] = best_match.get("party_name", "")
                else:
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
                top_3_matches=enriched_matches,
                username_tested=[],
                username_to_test=[],
                verified_by_human=False,
                human_verified_username=None,
                no_tiktok_account=False
            )
            
            db.add(deputy)
        
        db.commit()
        
        # Step 3: Apply verifications from CSV
        verification_count = 0
        try:
            with open("deputes_tiktok_verified.csv", "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Nom')
                    username = row.get('Username TikTok')
                    status = row.get('Statut')
                    
                    if not name:
                        continue
                    
                    # Find deputy by name
                    deputy = db.query(Deputy).filter(Deputy.name == name).first()
                    if not deputy:
                        continue
                    
                    # Apply verification
                    if status == "Aucun compte TikTok":
                        deputy.verified_by_human = True
                        deputy.no_tiktok_account = True
                        deputy.human_verified_username = None
                        verification_count += 1
                    elif status == "Compte vérifié" and username:
                        deputy.verified_by_human = True
                        deputy.no_tiktok_account = False
                        deputy.human_verified_username = username
                        verification_count += 1
                
                db.commit()
        except FileNotFoundError:
            # CSV file not found, skip verification step
            pass
        
        return {
            "message": f"Successfully loaded {len(data)} deputies with {verification_count} verifications",
            "deputies_count": len(data),
            "verifications_count": verification_count
        }
    
    except Exception as e:
        db.rollback()
        return {"error": str(e)}, 500


@app.get("/api/deputies", response_model=List[DeputyResponse])
async def get_deputies(
    verified: Optional[bool] = None,
    legislature: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all deputies with optional filters"""
    query = db.query(Deputy)
    
    if verified is not None:
        query = query.filter(Deputy.verified_by_human == verified)
    
    if legislature:
        query = query.filter(Deputy.legislature == legislature)
    
    deputies = query.all()
    return deputies


@app.get("/api/deputies/{deputy_id}", response_model=DeputyResponse)
async def get_deputy(deputy_id: int, db: Session = Depends(get_db)):
    """Get a specific deputy by ID"""
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
    if not deputy:
        raise HTTPException(status_code=404, detail="Deputy not found")
    return deputy


@app.put("/api/deputies/{deputy_id}/verify")
async def verify_deputy(
    deputy_id: int,
    verification: VerificationUpdate,
    db: Session = Depends(get_db)
):
    """Mark a deputy's TikTok account as verified by human"""
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
    if not deputy:
        raise HTTPException(status_code=404, detail="Deputy not found")
    
    deputy.verified_by_human = verification.verified_by_human
    deputy.human_verified_username = verification.human_verified_username
    
    # Handle no_tiktok_account flag
    if verification.no_tiktok_account is not None:
        deputy.no_tiktok_account = verification.no_tiktok_account
        # If marking as no account, ensure verified and clear username
        if verification.no_tiktok_account:
            deputy.verified_by_human = True
            deputy.human_verified_username = None
    
    db.commit()
    db.refresh(deputy)
    return {"message": "Verification updated", "deputy": deputy}


@app.post("/api/deputies/{deputy_id}/add-manual")
async def add_manual_account(
    deputy_id: int,
    account: ManualAccountAdd,
    db: Session = Depends(get_db)
):
    """Add a manual TikTok account for a deputy and automatically verify it"""
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
    if not deputy:
        raise HTTPException(status_code=404, detail="Deputy not found")
    
    # Extract username from URL
    username = account.tiktok_url.split('@')[-1].strip('/')
    
    # Create a new manual match entry
    manual_match = {
        "username": username,
        "subscribers": 0,
        "raw_score": 0,
        "confidence": 1.0,  # Manual = 100% confidence
        "sources": ["manual"],
        "num_sources": 1,
        "is_manual": True,
        "bio": "",
        "verified": False,
        "mentions_depute": False,
        "mentions_assemblee": False,
        "mentions_party": False,
        "mentions_region": False,
        "party_name": ""
    }
    
    # Add to top_3_matches if not already there
    if deputy.top_3_matches is None:
        deputy.top_3_matches = []
    
    deputy.top_3_matches.append(manual_match)
    
    # Automatically verify this account as the official one
    deputy.verified_by_human = True
    deputy.human_verified_username = username
    
    # If this is the first account, set it as best match too
    if not deputy.best_match_username:
        deputy.best_match_username = username
        deputy.best_match_url = f"https://www.tiktok.com/@{username}"
        deputy.found = True
    
    db.commit()
    db.refresh(deputy)
    return {"message": "Manual account added and verified", "deputy": deputy}


@app.put("/api/deputies/{deputy_id}/usernames")
async def update_usernames(
    deputy_id: int,
    usernames: UsernameUpdate,
    db: Session = Depends(get_db)
):
    """Update username lists for testing"""
    deputy = db.query(Deputy).filter(Deputy.id == deputy_id).first()
    if not deputy:
        raise HTTPException(status_code=404, detail="Deputy not found")
    
    if usernames.username_tested is not None:
        deputy.username_tested = usernames.username_tested
    
    if usernames.username_to_test is not None:
        deputy.username_to_test = usernames.username_to_test
    
    db.commit()
    db.refresh(deputy)
    return {"message": "Usernames updated", "deputy": deputy}


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get verification statistics"""
    total = db.query(Deputy).count()
    verified = db.query(Deputy).filter(Deputy.verified_by_human == True).count()
    with_tiktok = db.query(Deputy).filter(Deputy.found == True).count()
    
    return {
        "total": total,
        "verified": verified,
        "unverified": total - verified,
        "with_tiktok": with_tiktok,
        "without_tiktok": total - with_tiktok
    }


@app.get("/api/export/verified-accounts")
async def export_verified_accounts(db: Session = Depends(get_db)):
    """Export all verified deputies (with or without TikTok accounts) to CSV"""
    # Query all verified deputies
    deputies = db.query(Deputy).filter(
        Deputy.verified_by_human == True
    ).order_by(Deputy.name).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Nom', 'Législatures', 'Username TikTok', 'Lien TikTok', 'Statut'])
    
    # Write data
    for deputy in deputies:
        legislatures_str = ', '.join(deputy.legislatures) if deputy.legislatures else ''
        
        if deputy.no_tiktok_account:
            # Deputy has no TikTok account
            writer.writerow([
                deputy.name,
                legislatures_str,
                '',
                '',
                'Aucun compte TikTok'
            ])
        elif deputy.human_verified_username:
            # Deputy has verified TikTok account
            tiktok_url = f"https://www.tiktok.com/@{deputy.human_verified_username}"
            writer.writerow([
                deputy.name,
                legislatures_str,
                deputy.human_verified_username,
                tiktok_url,
                'Compte vérifié'
            ])
    
    # Prepare response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=deputes_tiktok_verified.csv"
        }
    )


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    # host="0.0.0.0" makes the server accessible from other computers on your network
    uvicorn.run(app, host="0.0.0.0", port=8000)
