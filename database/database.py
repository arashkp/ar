from sqlalchemy import create_engine
# Make sure Base is imported if models are in a separate file and inherit from it.
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.config import DATABASE_URL

# If models are defined in another file (e.g., models.py)
# they need to be imported so Base knows about them.
# Also, Base should be defined here or imported if defined elsewhere (e.g. models.py)
# For this example, let's assume Base is defined here and models.py imports it.
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base() # Defined above now

def init_db():
    # Import all modules here that might define models so that
    # they will be registered properly on the metadata.
    # This import is crucial for create_all to see the models.
    from . import models # Assuming models.py is in the same directory
    Base.metadata.create_all(bind=engine)
    print("Database tables created (if they didn't exist).")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
