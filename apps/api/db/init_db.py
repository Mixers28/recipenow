"""
Initialize the database schema by creating all tables.
This should be run once on deployment or development setup.
"""
from db.models import Base
from db.session import engine


def init_db():
    """Create all tables defined in models."""
    print("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema initialized successfully!")


if __name__ == "__main__":
    init_db()
