# SQLite ORM

A lightweight Django-like ORM for SQLite with full type support and thread safety.

## Quick Start

### 1. Define Models
```python
from sqlite_orm.db import BaseModel
from sqlite_orm.fields import CharField, IntegerField, BooleanField, DateTimeField, ForeignKey

class User(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField(max_length=50, unique=True)
    email = CharField(max_length=100, unique=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    table_name = 'users'

class Post(BaseModel):
    id = IntegerField(primary_key=True)
    title = CharField(max_length=200)
    content = TextField()
    author_id = ForeignKey(User)
    table_name = 'posts'

# Initialize
User.init_db('app.db')
Post.init_db('app.db')


# Create
user = User.create(username="john", email="john@example.com")
post = Post.create(title="Hello", content="World", author_id=user.id)

# Read
user = User.get(username="john")
posts = Post.objects.filter(author_id=user.id).all()

# Update
user.username = "john_updated"
user.save()

# Delete
user.delete_instance()



## Field lookup
User.objects.filter(id__gt=5)           # Greater than
User.objects.filter(username__contains="sm")    # Contains
User.objects.filter(username__icontains="SM")   # Case-insensitive
User.objects.filter(username__in=["a","b"])     # In list
User.objects.filter(username__startswith="j")   # Starts with
User.objects.filter(username__ne="admin")       # Not equal
```


```
Model Methods
Model.create(**kwargs) → Model - Create new record

Model.get(**filters) → Model - Get single record

Model.all() → List[Model] - Get all records

Model.filter(**filters) → QuerySet - Start filtered query

Model.update(filters, values) → int - Bulk update

Model.delete(**filters) → int - Bulk delete

Model.count(**filters) → int - Count records

Model.exists(**filters) → bool - Check existence

```