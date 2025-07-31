"""
CRUD helper utilities for the AR trading application.

This module provides base CRUD operations and common database patterns
to reduce code duplication across different CRUD modules.
"""

import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session, Query
from sqlalchemy import desc, asc
from fastapi import HTTPException, status
from database.base import BaseModel

logger = logging.getLogger(__name__)

# Generic type for SQLAlchemy models
T = TypeVar('T', bound=BaseModel)

class BaseCRUDHelper(Generic[T]):
    """
    Base CRUD helper class providing common database operations.
    
    This class can be extended by specific CRUD modules to inherit
    common functionality while adding model-specific operations.
    """
    
    def __init__(self, model: Type[T]):
        """
        Initialize the CRUD helper with a specific model.
        
        Args:
            model: The SQLAlchemy model class
        """
        self.model = model
    
    def create(self, db: Session, obj_in: Dict[str, Any]) -> T:
        """
        Create a new record in the database.
        
        Args:
            db: Database session
            obj_in: Dictionary containing the data to create
            
        Returns:
            The created model instance
        """
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.debug(f"Created {self.model.__name__} with ID: {db_obj.id}")
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {self.model.__name__.lower()}: {str(e)}"
            )
    
    def get_by_id(self, db: Session, id: int) -> Optional[T]:
        """
        Get a record by its ID.
        
        Args:
            db: Database session
            id: The record ID
            
        Returns:
            The model instance or None if not found
        """
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_id_or_404(self, db: Session, id: int) -> T:
        """
        Get a record by its ID or raise 404 if not found.
        
        Args:
            db: Database session
            id: The record ID
            
        Returns:
            The model instance
            
        Raises:
            HTTPException: If the record is not found
        """
        obj = self.get_by_id(db, id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model.__name__} with ID {id} not found"
            )
        return obj
    
    def update(self, db: Session, id: int, obj_in: Dict[str, Any]) -> Optional[T]:
        """
        Update a record by its ID.
        
        Args:
            db: Database session
            id: The record ID
            obj_in: Dictionary containing the data to update
            
        Returns:
            The updated model instance or None if not found
        """
        try:
            db_obj = self.get_by_id(db, id)
            if not db_obj:
                return None
            
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            db.commit()
            db.refresh(db_obj)
            logger.debug(f"Updated {self.model.__name__} with ID: {id}")
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update {self.model.__name__.lower()}: {str(e)}"
            )
    
    def delete(self, db: Session, id: int) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            db: Database session
            id: The record ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            db_obj = self.get_by_id(db, id)
            if not db_obj:
                return False
            
            db.delete(db_obj)
            db.commit()
            logger.debug(f"Deleted {self.model.__name__} with ID: {id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete {self.model.__name__.lower()}: {str(e)}"
            )
    
    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[T]:
        """
        Get multiple records with pagination and ordering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by (defaults to 'id')
            order_desc: Whether to order in descending order
            
        Returns:
            List of model instances
        """
        query = db.query(self.model)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(desc(order_field) if order_desc else asc(order_field))
        else:
            # Default ordering by ID
            query = query.order_by(desc(self.model.id) if order_desc else asc(self.model.id))
        
        return query.offset(skip).limit(limit).all()
    
    def get_multi_with_filters(
        self,
        db: Session,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[T]:
        """
        Get multiple records with filters, pagination, and ordering.
        
        Args:
            db: Database session
            filters: Dictionary of field-value pairs to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by (defaults to 'id')
            order_desc: Whether to order in descending order
            
        Returns:
            List of model instances
        """
        query = db.query(self.model)
        
        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(desc(order_field) if order_desc else asc(order_field))
        else:
            # Default ordering by ID
            query = query.order_by(desc(self.model.id) if order_desc else asc(self.model.id))
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filters.
        
        Args:
            db: Database session
            filters: Optional dictionary of field-value pairs to filter by
            
        Returns:
            Number of records
        """
        query = db.query(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        
        return query.count()

def create_base_crud(model: Type[T]) -> BaseCRUDHelper[T]:
    """
    Factory function to create a base CRUD helper for a model.
    
    Args:
        model: The SQLAlchemy model class
        
    Returns:
        BaseCRUDHelper instance for the model
    """
    return BaseCRUDHelper(model)

def validate_pagination_params(skip: int, limit: int, max_limit: int = 1000) -> None:
    """
    Validate pagination parameters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        max_limit: Maximum allowed limit
        
    Raises:
        HTTPException: If parameters are invalid
    """
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be positive"
        )
    
    if limit > max_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limit parameter cannot exceed {max_limit}"
        )

def apply_date_range_filter(
    query: Query,
    model: Type[T],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_field: str = "timestamp"
) -> Query:
    """
    Apply date range filter to a query.
    
    Args:
        query: The SQLAlchemy query
        model: The model class
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)
        date_field: Name of the date field to filter on
        
    Returns:
        Modified query with date filters applied
    """
    from datetime import datetime
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(getattr(model, date_field) >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {start_date}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(getattr(model, date_field) <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {end_date}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    return query 