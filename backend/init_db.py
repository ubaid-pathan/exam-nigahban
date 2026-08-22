from app.db.base import Base
from app.db.session import engine
import app.db.models


def init_database():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    init_database()