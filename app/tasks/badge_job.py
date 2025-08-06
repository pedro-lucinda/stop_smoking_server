from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.badge import Badge
from app.models.preference import Preference
from app.models.user import User


def assign_due_badges() -> None:
    """
    Award badges whose condition_time has elapsed since
    the user's quit date stored on their Preference.
    """
    now = datetime.utcnow()
    db: Session = SessionLocal()
    try:
        print("Start ------------------------------------")
        # 1) Find all users who have a preference with a quit_date
        users = (
            db.query(User)
            .join(User.preference)  # inner‐join to Preference
            .filter(Preference.quit_date.isnot(None))
            .all()
        )

        # 2) Load all badges that have a positive threshold
        badges = db.query(Badge).filter(Badge.condition_time > 0).all()

        # 3) For each user, compute minutes since quit and award badges
        for user in users:
            quit_dt = user.preference.quit_date
            # convert quit_date (a date) to a datetime at midnight UTC
            quit_dt = datetime(quit_dt.year, quit_dt.month, quit_dt.day)
            minutes_since_quit = int((now - quit_dt).total_seconds() // 60)

            for badge in badges:
                if (
                    badge not in user.badges
                    and minutes_since_quit >= badge.condition_time
                ):
                    user.badges.append(badge)

        db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
