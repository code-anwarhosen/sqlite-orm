"""
Core database connection and SQL operations
Thread-safe connection handling with proper transaction management
"""

import sqlite3, logging, threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class LookupTypes:
    """Django-style lookup types for field comparisons"""
    EXACT = 'exact'
    IEACT = 'iexact'
    GT = 'gt'
    GTE = 'gte'
    LT = 'lt'
    LTE = 'lte'
    NE = 'ne'
    CONTAINS = 'contains'
    ICONTAINS = 'icontains'
    STARTSWITH = 'startswith'
    ISTARTSWITH = 'istartswith'
    ENDSWITH = 'endswith'
    IENDSWITH = 'iendswith'
    IN = 'in'
    NOT_IN = 'nin'
    ISNULL = 'isnull'


class DatabaseConnection:
    """
    Thread-safe SQLite database connection manager
    Uses connection pooling and locking for concurrent access
    """
    
    def __init__(self, db_path: str = 'db.sqlite3'):
        if not db_path or not isinstance(db_path, str):
            raise ValueError('Database path must be a non-empty string')
        
        self.db_path = db_path
        self._lock = threading.RLock() # Re-entrant lock for thread safety
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with optimal settings"""
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """
        Thread-safe context manager for database connections
        Uses re-entrant lock to allow same thread to re-enter
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation failed: {e}")
                raise
            finally:
                conn.close()
    
    @contextmanager
    def _get_cursor(self):
        """Thread-safe context manager for database cursor operations"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            yield cursor
    
    def execute(self, sql: str, params: Union[Tuple, None] = None) -> bool:
        """Execute a SQL command with parameters"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, params or ())
            return True
        except sqlite3.Error as e:
            logger.error(f"Execute failed: {e}")
            return False
    
    def fetch_one(self, sql: str, params: Union[Tuple, None] = None) -> Optional[sqlite3.Row]:
        """Fetch a single row thread-safely"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Fetch one failed: {e}")
            return None
    
    def fetch_all(self, sql: str, params: Union[Tuple, None] = None) -> List[sqlite3.Row]:
        """Fetch all rows thread-safely"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Fetch all failed: {e}")
            return []
    
    def table_exists(self, table: str) -> bool:
        """Check if a table exists in the database"""
        sql = "SELECT name FROM sqlite_master WHERE type=? AND name=?"
        result = self.fetch_one(sql, ('table', table))
        return result is not None
    
    def get_table_columns(self, table: str) -> List[str]:
        """Get column names for a table"""
        sql = f"PRAGMA table_info({table})"
        rows = self.fetch_all(sql)
        return [row['name'] for row in rows] if rows else []
    
    def _parse_field_lookup(self, field_name: str) -> Tuple[str, str]:
        """Parse Django-style field lookups"""
        if '__' in field_name:
            field_parts = field_name.split('__')
            if len(field_parts) > 1:
                lookup_type = field_parts[-1]
                field_name = '__'.join(field_parts[:-1])
                return field_name, lookup_type
        return field_name, LookupTypes.EXACT
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Tuple[str, tuple]:
        """Build WHERE clause from dictionary filters"""
        if not filters:
            return "", ()
        
        clauses = []
        values = []
        
        for field_name, value in filters.items():
            field, lookup_type = self._parse_field_lookup(field_name)
            
            if lookup_type == LookupTypes.EXACT:
                clauses.append(f"{field}=?")
                values.append(value)
            elif lookup_type == LookupTypes.IEACT:
                clauses.append(f"{field} LIKE ? COLLATE NOCASE")
                values.append(value)
            elif lookup_type == LookupTypes.GT:
                clauses.append(f"{field}>?")
                values.append(value)
            elif lookup_type == LookupTypes.GTE:
                clauses.append(f"{field}>=?")
                values.append(value)
            elif lookup_type == LookupTypes.LT:
                clauses.append(f"{field}<?")
                values.append(value)
            elif lookup_type == LookupTypes.LTE:
                clauses.append(f"{field}<=?")
                values.append(value)
            elif lookup_type == LookupTypes.NE:
                clauses.append(f"{field}!=?")
                values.append(value)
            elif lookup_type == LookupTypes.IN:
                if isinstance(value, (list, tuple)):
                    placeholders = ", ".join(["?" for _ in value])
                    clauses.append(f"{field} IN ({placeholders})")
                    values.extend(value)
                else:
                    clauses.append(f"{field}=?")
                    values.append(value)
            elif lookup_type == LookupTypes.NOT_IN:
                if isinstance(value, (list, tuple)):
                    placeholders = ", ".join(["?" for _ in value])
                    clauses.append(f"{field} NOT IN ({placeholders})")
                    values.extend(value)
                else:
                    clauses.append(f"{field}!=?")
                    values.append(value)
            elif lookup_type == LookupTypes.CONTAINS:
                clauses.append(f"{field} LIKE ?")
                values.append(f"%{value}%")
            elif lookup_type == LookupTypes.ICONTAINS:
                clauses.append(f"{field} LIKE ? COLLATE NOCASE")
                values.append(f"%{value}%")
            elif lookup_type == LookupTypes.STARTSWITH:
                clauses.append(f"{field} LIKE ?")
                values.append(f"{value}%")
            elif lookup_type == LookupTypes.ISTARTSWITH:
                clauses.append(f"{field} LIKE ? COLLATE NOCASE")
                values.append(f"{value}%")
            elif lookup_type == LookupTypes.ENDSWITH:
                clauses.append(f"{field} LIKE ?")
                values.append(f"%{value}")
            elif lookup_type == LookupTypes.IENDSWITH:
                clauses.append(f"{field} LIKE ? COLLATE NOCASE")
                values.append(f"%{value}")
            elif lookup_type == LookupTypes.ISNULL:
                if value:
                    clauses.append(f"{field} IS NULL")
                else:
                    clauses.append(f"{field} IS NOT NULL")
            else:
                clauses.append(f"{field}=?")
                values.append(value)
        
        where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where_clause, tuple(values)