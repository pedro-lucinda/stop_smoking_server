from app.db.session import SessionLocal
from app.models.preference import Preference
from app.services.motivation_service import generate_and_save_for_user

def generate_and_store_daily_text():
    db = SessionLocal()
    try:
        prefs = db.query(Preference).all()
        for p in prefs:
            try:
                generate_and_save_for_user(db, p.user_id)
            except Exception as e:
                print(f"Failed for user {p.user_id}:", e)
    finally:
        db.close()
