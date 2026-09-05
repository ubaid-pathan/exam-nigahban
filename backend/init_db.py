from app.db.base import Base
from app.db.seed_monitoring_rules import seed_monitoring_rules
from app.db.session import SessionLocal, engine
import app.db.models


def init_database():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

    db = SessionLocal()
    try:
        inserted, updated = seed_monitoring_rules(db)
        print(f"Monitoring rules seeded: {inserted} inserted, {updated} updated")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()