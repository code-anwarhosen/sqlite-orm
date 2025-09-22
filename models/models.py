from sqlite_orm.db import BaseModel
from sqlite_orm.fields import CharField, IntegerField, BooleanField, DateTimeField, TextField, ForeignKey
import os
import base64
import hashlib

class PasswordManager:
    """Password hashing utility"""
    
    iterations: int = 100_000

    @classmethod
    def make_password(cls, password: str) -> str:
        salt = os.urandom(16)
        pwd = password.encode("utf-8")
        dk = hashlib.pbkdf2_hmac("sha256", pwd, salt, cls.iterations)
        return f"{cls.iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

    @classmethod
    def _check_password(cls, password: str, stored_hash: str) -> bool:
        try:
            iterations_str, salt_b64, hash_b64 = stored_hash.split("$")
            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64)
            old_hash = base64.b64decode(hash_b64)
            pwd = password.encode("utf-8")
            new_hash = hashlib.pbkdf2_hmac("sha256", pwd, salt, iterations)
            return new_hash == old_hash
        except Exception:
            return False

class User(BaseModel, PasswordManager):
    """User model with authentication support"""
    
    id = IntegerField(primary_key=True)
    username = CharField(max_length=50, unique=True, nullable=False)
    email = CharField(max_length=100, unique=True, nullable=False)
    first_name = CharField(max_length=30, nullable=False)
    last_name = CharField(max_length=30, nullable=False)
    password_hash = TextField(nullable=False)
    is_active = BooleanField(default=True)
    is_admin = BooleanField(default=False)
    date_joined = DateTimeField(auto_now_add=True)
    last_login = DateTimeField(nullable=True)
    
    table_name = 'users'
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def set_password(self, password: str) -> None:
        """Set password hash for the user"""
        self.password_hash = self.make_password(password)
        self.save()
    
    def check_password(self, password: str) -> bool:
        """Verify user password"""
        return PasswordManager._check_password(password, self.password_hash) # type: ignore

class Category(BaseModel):
    """Category model for content organization"""
    
    id = IntegerField(primary_key=True)
    name = CharField(max_length=50, unique=True, nullable=False)
    slug = CharField(max_length=60, unique=True, nullable=False)
    description = TextField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    
    table_name = 'categories'

class Post(BaseModel):
    """Post model with author relationship"""
    
    id = IntegerField(primary_key=True)
    title = CharField(max_length=200, nullable=False)
    slug = CharField(max_length=220, unique=True, nullable=False)
    content = TextField()
    excerpt = TextField()
    author_id = ForeignKey(User)
    category_id = ForeignKey(Category, nullable=True)
    status = CharField(max_length=20, default='draft')  # draft, published, archived
    is_featured = BooleanField(default=False)
    view_count = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    published_at = DateTimeField(nullable=True)
    
    table_name = 'posts'
    
    @property
    def reading_time(self) -> int:
        """Calculate approximate reading time in minutes"""
        words_per_minute = 200
        word_count = len(str(self.content).split()) if self.content else 0
        return max(1, word_count // words_per_minute)

class Comment(BaseModel):
    """Comment model with post relationship"""
    
    id = IntegerField(primary_key=True)
    post_id = ForeignKey(Post)
    author_id = ForeignKey(User)
    parent_id = ForeignKey('self', nullable=True)  # Self-referential for nested comments
    content = TextField(nullable=False)
    is_approved = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    table_name = 'comments'

def initialize_database(db_path: str = 'app.db'):
    """Initialize all models with database"""
    User.init_db(db_path)
    Category.init_db(db_path)
    Post.init_db(db_path)
    Comment.init_db(db_path)
    print(f"Database initialized: {db_path}")
    return db_path
