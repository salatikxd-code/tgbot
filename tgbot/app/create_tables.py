from app.db import Base, engine

def create_tables():
    print("🔧 Creating tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    print("✔ Tables are ready")
