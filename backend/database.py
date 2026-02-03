from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()

# 1. Define the Database Location
# Fallback to local SQLite if DATABASE_URL is not provided
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# 2. Create the Engine
# Only use check_same_thread for SQLite
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. Create a Session factory
# This is how our code will talk to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create a Base class
# Our future 'User' model will inherit from this class.
Base = declarative_base()

# 5. Dependency to get the database session
# This ensures each request gets its own connection and closes it when done.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
