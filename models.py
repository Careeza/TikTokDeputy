from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Deputy(Base):
    __tablename__ = "deputies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    legislatures = Column(JSON, nullable=False)  # Array of legislatures ["XV", "XVI", "XVII"]
    found = Column(Boolean, default=False)
    
    # Best match information
    best_match_username = Column(String)
    best_match_url = Column(String)
    best_match_subscribers = Column(Integer)
    best_match_confidence = Column(Float)
    best_match_raw_score = Column(Integer)
    best_match_sources = Column(JSON)
    best_match_num_sources = Column(Integer)
    best_match_verified = Column(Boolean)
    best_match_bio = Column(String)
    best_match_mentions_depute = Column(Boolean)
    best_match_mentions_assemblee = Column(Boolean)
    best_match_mentions_party = Column(Boolean)
    best_match_mentions_region = Column(Boolean)
    best_match_party_name = Column(String)
    
    # Additional matches
    top_3_matches = Column(JSON)
    
    # New fields for manual verification
    username_tested = Column(JSON, default=list)  # List of usernames already tested
    username_to_test = Column(JSON, default=list)  # List of usernames to test
    verified_by_human = Column(Boolean, default=False)
    human_verified_username = Column(String)  # The username confirmed by human
    no_tiktok_account = Column(Boolean, default=False)  # User confirmed no TikTok exists


# Database setup
DATABASE_URL = "sqlite:///./tiktok_verification.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

