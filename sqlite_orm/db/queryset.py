"""
QuerySet class for building and executing database queries
Supports chaining and returns typed model instances
"""

from typing import List, Optional, Tuple, TypeVar, Generic
from sqlite_orm.db.core import DatabaseConnection, LookupTypes

M = TypeVar('M', bound='BaseModel') # type: ignore


class QuerySet(Generic[M]):
    """
    Chainable query builder for database operations
    Returns specific model instances for better typing
    """
    
    def __init__(self, model_class, db_connection: DatabaseConnection):
        self.model_class = model_class
        self.db = db_connection
        self._filters = {}
        self._order_by = None
        self._limit = None
        self._descending = False
    
    def filter(self, **filters) -> 'QuerySet[M]':
        """Add filters to the query"""
        self._filters.update(filters)
        return self
    
    def exclude(self, **filters) -> 'QuerySet[M]':
        """Exclude records matching filters"""
        for field, value in filters.items():
            field, lookup_type = self.db._parse_field_lookup(field)
            if lookup_type == LookupTypes.EXACT:
                self._filters[f"{field}__ne"] = value
            elif lookup_type == LookupTypes.IN:
                self._filters[f"{field}__nin"] = value
            else:
                self._filters[f"NOT_{field}__{lookup_type}"] = value
        return self
    
    def order_by(self, field: str, descending: bool = False) -> 'QuerySet[M]':
        """Set ordering for the query"""
        self._order_by = field
        self._descending = descending
        return self
    
    def limit(self, count: int) -> 'QuerySet[M]':
        """Set limit for the query"""
        self._limit = count
        return self
    
    def _build_query(self) -> Tuple[str, tuple]:
        """Build the SQL query based on current state"""
        sql = f"SELECT * FROM {self.model_class.table_name}"
        
        where_clause, values = self.db._build_where_clause(self._filters)
        sql += f" {where_clause}"
        
        if self._order_by:
            direction = "DESC" if self._descending else "ASC"
            sql += f" ORDER BY {self._order_by} {direction}"
        
        if self._limit:
            sql += f" LIMIT {self._limit}"
        
        return sql, values
    
    def all(self) -> List[M]:
        """Execute query and return all results as model instances"""
        sql, values = self._build_query()
        rows = self.db.fetch_all(sql, values)
        return [self.model_class._instance_from_dict(dict(row)) for row in rows]
    
    def first(self) -> Optional[M]:
        """Execute query and return first result as model instance"""
        sql, values = self._build_query()
        if "LIMIT" not in sql:
            sql += " LIMIT 1"
        
        row = self.db.fetch_one(sql, values)
        return self.model_class._instance_from_dict(dict(row)) if row else None
    
    def count(self) -> int:
        """Return count of matching rows"""
        sql = f"SELECT COUNT(*) as count FROM {self.model_class.table_name}"
        where_clause, values = self.db._build_where_clause(self._filters)
        sql += f" {where_clause}"
        
        result = self.db.fetch_one(sql, values)
        return result['count'] if result else 0
    
    def exists(self) -> bool:
        """Check if any rows match the filters"""
        return self.count() > 0
    
    def delete(self) -> int:
        """Delete all matching rows"""
        where_clause, values = self.db._build_where_clause(self._filters)
        sql = f"DELETE FROM {self.model_class.table_name} {where_clause}"
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            return cursor.rowcount