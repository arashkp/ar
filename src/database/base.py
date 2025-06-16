from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True  # This ensures that SQLAlchemy doesn't try to create a table for BaseModel
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
