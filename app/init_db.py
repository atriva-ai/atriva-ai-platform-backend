# init_db.py
from app.database import engine, SessionLocal, Base
from app.db.models.store import Store
from app.db.models.settings import Settings
from app.db.models.camera import Camera

def seed():
    db = SessionLocal()
    # Seed store
    if not db.query(Store).first():
        db.add(Store(name="Default Store"))

    # Seed settings
    if not db.query(Settings).first():
        db.add(Settings(
            store_name="Default Store",
            store_description="Welcome to our store",
            store_timezone="UTC",
            store_language="en",
            store_theme="light",
            store_notifications_enabled=True,
            store_analytics_enabled=True
        ))

    db.commit()
    db.close()

def init():
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")
    seed()
    print("✅ Seed data added")

if __name__ == "__main__":
    init()
