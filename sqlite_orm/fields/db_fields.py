"""
Field type definitions for model attributes
Provides type validation, conversion, and SQL schema generation
"""

from typing import Any, Type, Optional, List, Union


class Field:
    """Base field class for all model fields"""
    
    def __init__(self, 
                 primary_key: bool = False,
                 unique: bool = False, 
                 nullable: bool = True,
                 default: Any = None):
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable
        self.default = default
        self.column_name = None
        self.model_class = None
    
    def get_sql_type(self) -> str:
        raise NotImplementedError("Subclasses must implement get_sql_type()")
    
    def to_python(self, value: Any) -> Any:
        return value
    
    def to_database(self, value: Any) -> Any:
        return value
    
    def validate(self, value: Any) -> bool:
        if value is None:
            return self.nullable
        return True
    
    def get_sql_constraints(self) -> List[str]:
        constraints = []
        if self.unique and not self.primary_key:
            constraints.append("UNIQUE")
        if not self.nullable:
            constraints.append("NOT NULL")
        return constraints


class CharField(Field):
    def __init__(self, max_length: int = 255, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length
    
    def get_sql_type(self) -> str:
        return f"VARCHAR({self.max_length})"
    
    def validate(self, value: Any) -> bool:
        if not super().validate(value):
            return False
        if value is not None and len(str(value)) > self.max_length:
            return False
        return True


class IntegerField(Field):
    def get_sql_type(self) -> str:
        if self.primary_key:
            return "INTEGER PRIMARY KEY AUTOINCREMENT"
        return "INTEGER"
    
    def to_python(self, value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None


class BooleanField(Field):
    def __init__(self, default: bool = False, **kwargs):
        super().__init__(default=default, **kwargs)
    
    def get_sql_type(self) -> str:
        return "INTEGER"
    
    def to_python(self, value: Any) -> Optional[bool]:
        if value is None:
            return None
        return bool(int(value))
    
    def to_database(self, value: Any) -> int:
        return 1 if value else 0


class DateTimeField(Field):
    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
    
    def get_sql_type(self) -> str:
        return "TIMESTAMP"


class TextField(Field):
    def get_sql_type(self) -> str:
        return "TEXT"


class FloatField(Field):
    def get_sql_type(self) -> str:
        return "REAL"
    
    def to_python(self, value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None


class ForeignKey(Field):
    def __init__(self, to: Union[str, Type], **kwargs):
        super().__init__(**kwargs)
        self.to = to
    
    def get_sql_type(self) -> str:
        return "INTEGER"