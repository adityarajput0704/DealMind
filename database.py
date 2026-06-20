# database.py
#
# SQLAlchemy is a library that lets you talk to databases using Python objects
# instead of writing raw SQL. Think of it as a translator between Python and SQLite.
#
# "engine" = the connection to the database file
# "SessionLocal" = a factory that creates database sessions (like opening a notebook
#   to read/write, then closing it when done)
# "Base" = a base class that all our table models will inherit from

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# This tells SQLAlchemy to create a file called agent_economy.db in the current folder.
# "check_same_thread=False" is a SQLite-specific setting needed for FastAPI.
DATABASE_URL = "sqlite:///./agent_economy.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Each request to the API will get its own session (its own "notebook").
# autocommit=False means changes aren't saved until we explicitly say "commit".
# autoflush=False means SQLAlchemy won't auto-send pending changes before queries.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our table classes will inherit from Base.
# This lets SQLAlchemy know "these classes represent database tables."
Base = declarative_base()


def get_db():
    """
    This is a FastAPI "dependency" — a function FastAPI calls automatically
    to give each endpoint a fresh database session, then closes it afterward.
    The 'yield' keyword is what makes this work: code before yield = setup,
    code after yield = cleanup (runs even if there's an error).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()