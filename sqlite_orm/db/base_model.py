"""
Base model class for ORM functionality
Returns specific model instances with proper typing and thread safety
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from sqlite_orm.db.core import DatabaseConnection
from sqlite_orm.db.queryset import QuerySet
from sqlite_orm.fields import Field

logger = logging.getLogger(__name__)

# Type variable for model instances
M = TypeVar('M', bound='BaseModel')


class ModelMeta(type):
    """Metaclass to handle model field collection and table creation"""
    
    def __new__(cls, name, bases, attrs):
        if name == 'BaseModel':
            return super().__new__(cls, name, bases, attrs)
        
        if 'table_name' not in attrs or not attrs['table_name']:
            attrs['table_name'] = cls._generate_table_name(name)
        
        fields = {}
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                value.column_name = key
                value.model_class = attrs.get('__class__')
                fields[key] = value
                del attrs[key]
        
        attrs['_fields'] = fields
        
        return super().__new__(cls, name, bases, attrs)
    
    @staticmethod
    def _generate_table_name(class_name: str) -> str:
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        return f"{name}s"


class QuerySetDescriptor:
    """Descriptor that returns a typed QuerySet instance"""
    
    def __get__(self, instance, owner: Type[M]) -> QuerySet[M]:
        return QuerySet(owner, owner._db)


class BaseModel(metaclass=ModelMeta):
    """
    Abstract base class for ORM models
    Returns specific model instances for better IDE support
    """
    
    table_name: str = None # type: ignore
    _fields: Dict[str, Field] = {}

    _db: DatabaseConnection = None # type: ignore
    _table_initialized = False

    objects = QuerySetDescriptor()

    def __init__(self, **kwargs):
        self._data = {}
        self._modified = False
        
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name, field.default)
            if value is not None:
                value = field.to_python(value)
            self._data[field_name] = value

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to field data"""
        if name in self._fields:
            return self._data.get(name)
        
        # Allow access to model methods and properties
        if hasattr(self.__class__, name):
            attr = getattr(self.__class__, name)
            if isinstance(attr, property):
                return attr.__get__(self, self.__class__)
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Track modifications to field data with validation"""
        if name not in ('_data', 'table_name', 'db', '_modified', '_table_initialized'):
            if name in self._fields:
                field = self._fields[name]
                if not field.validate(value):
                    raise ValueError(f"Invalid value for field {name}")
                if value is not None:
                    value = field.to_python(value)
                self._data[name] = value
                self._modified = True
                return
        super().__setattr__(name, value)

    @classmethod
    def init_db(cls, db_path: str = 'db.sqlite3'):
        """Initialize database connection for this model"""
        if not cls._db:
            cls._db = DatabaseConnection(db_path)

    @classmethod
    def _check_initialized(cls):
        """Ensure database and table are initialized"""
        if not cls._db:
            raise ValueError("Database not initialized. Call .init_db() first.")
        if not cls._table_initialized:
            cls._init_table()

    @classmethod
    def _init_table(cls):
        """Create table if it doesn't exist"""
        if cls._table_initialized:
            return
        
        if cls._db.table_exists(cls.table_name):
            cls._table_initialized = True
            return
        
        column_defs = []
        for field_name, field in cls._fields.items():
            sql_type = field.get_sql_type()
            constraints = field.get_sql_constraints()
            column_def = f"{field_name} {sql_type}"
            if constraints:
                column_def += " " + " ".join(constraints)
            column_defs.append(column_def)
        
        sql = f"CREATE TABLE IF NOT EXISTS {cls.table_name} ({', '.join(column_defs)})"
        
        if cls._db.execute(sql):
            cls._table_initialized = True
        else:
            raise RuntimeError(f"Table creation failed for {cls.table_name}")

    @classmethod
    def create(cls: Type[M], **kwargs) -> Optional[M]:
        """Create a new record and return model instance"""
        cls._check_initialized()
        
        data = {}
        for field_name, value in kwargs.items():
            if field_name not in cls._fields:
                continue
            field = cls._fields[field_name]
            if not field.validate(value):
                raise ValueError(f"Validation failed for field {field_name}")
            data[field_name] = field.to_database(value) if value is not None else None
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = tuple(data.values())
        
        sql = f"INSERT INTO {cls.table_name} ({columns}) VALUES ({placeholders})"
        
        # Use single connection for both INSERT and SELECT
        with cls._db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            row_id = cursor.lastrowid
            
            if row_id:
                # Find primary key field
                pk_field = next((name for name, field in cls._fields.items() 
                               if field.primary_key), None)
                
                if pk_field:
                    # Fetch the created row using same connection
                    fetch_sql = f"SELECT * FROM {cls.table_name} WHERE {pk_field}=?"
                    cursor.execute(fetch_sql, (row_id,))
                    row_data = cursor.fetchone()
                    
                    if row_data:
                        return cls._instance_from_dict(dict(row_data))
        
        return None

    @classmethod
    def get(cls: Type[M], **filters) -> Optional[M]:
        """Get a single record as model instance"""
        cls._check_initialized()
        
        where, values = cls._db._build_where_clause(filters)
        sql = f"SELECT * FROM {cls.table_name} {where} LIMIT 1"
        
        row_data = cls._db.fetch_one(sql, values)
        if row_data:
            return cls._instance_from_dict(dict(row_data))
        return None

    @classmethod
    def all(cls: Type[M]) -> List[M]:
        """Get all records as model instances"""
        cls._check_initialized()
        
        sql = f"SELECT * FROM {cls.table_name}"
        rows = cls._db.fetch_all(sql)
        return [cls._instance_from_dict(dict(row)) for row in rows]

    @classmethod
    def filter(cls: Type[M], **filters) -> QuerySet[M]:
        """Start a filtered query"""
        cls._check_initialized()
        return cls.objects.filter(**filters)

    @classmethod
    def _instance_from_dict(cls: Type[M], data: Dict[str, Any]) -> M:
        """Convert database data to model instance"""
        converted_data = {}
        for key, value in data.items():
            if key in cls._fields:
                field = cls._fields[key]
                converted_data[key] = field.to_python(value) if value is not None else None
            else:
                converted_data[key] = value
        
        instance = cls.__new__(cls)
        instance._data = converted_data
        instance._modified = False
        return instance

    @classmethod
    def exists(cls, **filters) -> bool:
        """Check if record exists"""
        return cls.get(**filters) is not None

    @classmethod
    def update(cls, filters: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Update records matching filters"""
        cls._check_initialized()
        
        converted_values = {}
        for field_name, value in values.items():
            if field_name in cls._fields:
                field = cls._fields[field_name]
                if not field.validate(value):
                    raise ValueError(f"Validation failed for field {field_name}")
                converted_values[field_name] = field.to_database(value) if value is not None else None
            else:
                converted_values[field_name] = value
        
        where_clause, where_values = cls._db._build_where_clause(filters)
        set_clause = ", ".join([f"{col}=?" for col in converted_values.keys()])
        set_values = tuple(converted_values.values())
        
        sql = f"UPDATE {cls.table_name} SET {set_clause} {where_clause}"
        
        with cls._db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, set_values + where_values)
            return cursor.rowcount

    @classmethod
    def delete(cls, **filters) -> int:
        """Delete records matching filters"""
        cls._check_initialized()
        
        where, values = cls._db._build_where_clause(filters)
        sql = f"DELETE FROM {cls.table_name} {where}"
        
        with cls._db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            return cursor.rowcount

    @classmethod
    def count(cls, **filters) -> int:
        """Count records matching filters"""
        cls._check_initialized()
        
        where, values = cls._db._build_where_clause(filters)
        sql = f"SELECT COUNT(*) as count FROM {cls.table_name} {where}"
        
        result = cls._db.fetch_one(sql, values)
        return result['count'] if result else 0

    def save(self) -> bool:
        """Save model instance to database"""
        self._check_initialized()
        
        if not self._modified:
            return True
        
        # Find primary key
        pk_field = next((name for name, field in self._fields.items() 
                        if field.primary_key), None)
        pk_value = self._data.get(pk_field) if pk_field else None
        
        if pk_value:  # Update existing record
            set_parts = []
            values = []
            
            for col, val in self._data.items():
                if col != pk_field:
                    set_parts.append(f"{col}=?")
                    values.append(val)
            
            values.append(pk_value)
            set_clause = ", ".join(set_parts)
            
            sql = f"UPDATE {self.table_name} SET {set_clause} WHERE {pk_field}=?"
            
            success = self._db.execute(sql, tuple(values))
            if success:
                self._modified = False
            return success
        
        else:  # Insert new record
            data = {k: v for k, v in self._data.items() if k != pk_field}
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = tuple(data.values())
            
            sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
            
            with self._db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, values)
                row_id = cursor.lastrowid
                
                if row_id and pk_field:
                    self._data[pk_field] = row_id
                    self._modified = False
                    return True
            
            return False

    def delete_instance(self) -> bool:
        """Delete this model instance"""
        self._check_initialized()
        
        pk_field = next((name for name, field in self._fields.items() 
                        if field.primary_key), None)
        pk_value = self._data.get(pk_field) if pk_field else None
        
        if not pk_value:
            return False
        
        sql = f"DELETE FROM {self.table_name} WHERE {pk_field}=?"
        return self._db.execute(sql, (pk_value,))

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        result = {}
        for key, value in self._data.items():
            if key in self._fields:
                field = self._fields[key]
                result[key] = field.to_python(value) if value is not None else None
            else:
                result[key] = value
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._data}>"