"""
Script to create a user directly in the database.

Usage:
    DATABASE_URL=postgresql://... python scripts/create_user.py

Or via Railway:
    railway run python scripts/create_user.py
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User
from app.core.security import hash_password, PasswordValidator

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

EMAIL = "felipe.espitalher@gmail.com"
PASSWORD = "Felipe@123"
FIRST_NAME = "Felipe"
LAST_NAME = "Espitalher"

is_valid, error = PasswordValidator.validate(PASSWORD)
if not is_valid:
    print(f"ERROR: Password does not meet requirements: {error}")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

try:
    existing = db.query(User).filter(User.email == EMAIL.lower()).first()
    if existing:
        print(f"User {EMAIL} already exists (id={existing.id})")
        sys.exit(0)

    user = User(
        id=uuid.uuid4(),
        email=EMAIL.lower(),
        password_hash=hash_password(PASSWORD),
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
        is_email_verified=True,
    )
    db.add(user)
    db.commit()
    print(f"User created successfully: {EMAIL} (id={user.id})")
finally:
    db.close()
