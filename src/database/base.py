from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, DECIMAL, String
from decimal import Decimal

Base = declarative_base()

class DecimalType(TypeDecorator):
    """
    Custom TypeDecorator for handling Python's Decimal objects.
    Ensures that data is stored with precision.
    - For non-SQLite backends, it uses the native DECIMAL type.
    - For SQLite, it stores the data as a string to preserve precision,
      as SQLite does not have a native DECIMAL type.
    """
    impl = DECIMAL
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(String(255))
        return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if dialect.name == 'sqlite':
                return str(value)
            return value
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return Decimal(value)
        return None

class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_onupdate=func.now())
