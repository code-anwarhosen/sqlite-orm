"""
Comprehensive ORM usage examples
Demonstrates all features with real-world scenarios
"""

from models.models import *
from datetime import datetime
import threading

def demo_basic_crud():
    """Basic Create, Read, Update, Delete operations"""
    print("=== BASIC CRUD OPERATIONS ===")
    
    # Initialize database
    initialize_database('demo.db')
    
    # CREATE - Create a new user
    user = User.create(
        username="john_doe",
        email="john@example.com",
        first_name="John",
        last_name="Doe",
        password_hash=User.make_password("securepassword123"),
        is_admin=True
    )
    
    if user:
        print(f"✅ User created: {user.username} (ID: {user.id})")
        print(f"✅ Full name: {user.full_name}")  # Access model properties!
        
        # READ - Retrieve user by different methods
        same_user = User.get(id=user.id)
        user_by_username = User.get(username="john_doe")
        print(f"✅ User retrieved: {same_user.email}")
        print(f"✅ User by username: {user_by_username.email}")
        
        # UPDATE - Modify and save
        user.last_name = "Smith"
        user.save()
        print(f"✅ User updated: {user.full_name}")
        
        # Check existence
        exists = User.exists(username="john_doe")
        print(f"✅ User exists: {exists}")
        
        # CREATE - Add a category
        category = Category.create(
            name="Technology",
            slug="technology",
            description="Posts about technology and programming"
        )
        print(f"✅ Category created: {category.name}")
        
        # CREATE - Add a post
        post = Post.create(
            title="Getting Started with Python",
            slug="getting-started-with-python",
            content="Python is a powerful programming language that's easy to learn...",
            excerpt="Learn the basics of Python programming",
            author_id=user.id,
            category_id=category.id,
            status="published",
            published_at=datetime.now()
        )
        print(f"✅ Post created: {post.title}")
        print(f"✅ Reading time: {post.reading_time} minutes")
        
        # DELETE - Remove a record
        temp_user = User.create(
            username="temp_user",
            email="temp@example.com",
            first_name="Temp",
            last_name="User",
            password_hash=User.make_password("temp")
        )
        deleted_count = User.delete(username="temp_user")
        print(f"✅ Temporary user deleted: {deleted_count} rows affected")
    
    print()

def demo_query_operations():
    """Demonstrate query operations with filters"""
    print("=== QUERY OPERATIONS ===")
    
    initialize_database('demo.db')
    
    # Get all users
    all_users = User.all()
    print(f"✅ All users: {len(all_users)} found")
    
    # Filter with conditions
    admin_users = User.objects.filter(is_admin=True).all()
    print(f"✅ Admin users: {len(admin_users)} found")
    
    # Multiple filters
    active_admins = User.objects.filter(is_admin=True, is_active=True).all()
    print(f"✅ Active admin users: {len(active_admins)} found")
    
    # Ordering and limiting
    recent_users = User.objects.order_by("date_joined", descending=True).limit(3).all()
    print(f"✅ Recent users: {len(recent_users)} found")
    
    # Complex query
    featured_posts = (Post.objects
                     .filter(status="published", is_featured=True)
                     .order_by("published_at", descending=True)
                     .limit(5)
                     .all())
    print(f"✅ Featured posts: {len(featured_posts)} found")
    
    # Count operations
    user_count = User.count()
    active_user_count = User.objects.filter(is_active=True).count()
    print(f"✅ Total users: {user_count}")
    print(f"✅ Active users: {active_user_count}")
    
    # Exclude operations
    non_admin_users = User.objects.exclude(is_admin=True).all()
    print(f"✅ Non-admin users: {len(non_admin_users)} found")
    
    print()

def demo_advanced_lookups():
    """Demonstrate Django-style field lookups"""
    print("=== ADVANCED FIELD LOOKUPS ===")
    
    initialize_database('demo.db')
    
    # Create test data
    for i in range(5):
        User.create(
            username=f"user_{i}",
            email=f"user{i}@example.com",
            first_name=f"User{i}",
            last_name="Test",
            password_hash=User.make_password("password"),
            is_admin=(i % 2 == 0)
        )
    
    # String contains (case-sensitive)
    users_with_1 = User.objects.filter(username__contains="1").all()
    print(f"✅ Users with '1' in username: {len(users_with_1)}")
    
    # String contains (case-insensitive)
    users_with_user = User.objects.filter(username__icontains="USER").all()
    print(f"✅ Users with 'USER' (case-insensitive): {len(users_with_user)}")
    
    # Greater than
    users_gt = User.objects.filter(id__gt=1).all()
    print(f"✅ Users with ID > 1: {len(users_gt)}")
    
    # In list
    specific_users = User.objects.filter(username__in=["user_1", "user_2"]).all()
    print(f"✅ Specific users: {len(specific_users)}")
    
    # Starts with
    users_starting_with_u = User.objects.filter(username__startswith="user_").all()
    print(f"✅ Users starting with 'user_': {len(users_starting_with_u)}")
    
    # Clean up
    User.delete(username__startswith="user_")
    print("✅ Test users cleaned up")
    print()

def demo_relationships():
    """Demonstrate relationship operations"""
    print("=== RELATIONSHIP OPERATIONS ===")
    
    initialize_database('demo.db')
    
    # Get existing user
    user = User.get(username="john_doe")
    category = Category.get(name="Technology")
    
    if user and category:
        # Create posts for the user
        post1 = Post.create(
            title="Python Web Development",
            slug="python-web-development",
            content="Building web applications with Python and Django...",
            excerpt="Web development with Python frameworks",
            author_id=user.id,
            category_id=category.id,
            status="published",
            published_at=datetime.now()
        )
        
        post2 = Post.create(
            title="Database Design",
            slug="database-design",
            content="Best practices for database design and optimization...",
            excerpt="Database design patterns",
            author_id=user.id,
            category_id=category.id,
            status="published",
            published_at=datetime.now()
        )
        
        # Create comments
        comment1 = Comment.create(
            post_id=post1.id,
            author_id=user.id,
            content="Great article! Very helpful for beginners.",
            is_approved=True
        )
        
        comment2 = Comment.create(
            post_id=post1.id,
            author_id=user.id,
            content="Thanks for sharing these insights!",
            is_approved=True
        )
        
        # Nested comment (reply)
        reply_comment = Comment.create(
            post_id=post1.id,
            author_id=user.id,
            parent_id=comment1.id,
            content="Glad you found it helpful!",
            is_approved=True
        )
        
        # Query relationships
        user_posts = Post.objects.filter(author_id=user.id).all()
        print(f"✅ User '{user.username}' has {len(user_posts)} posts")
        
        post_comments = Comment.objects.filter(post_id=post1.id).all()
        print(f"✅ Post '{post1.title}' has {len(post_comments)} comments")
        
        approved_comments = Comment.objects.filter(is_approved=True).count()
        print(f"✅ Total approved comments: {approved_comments}")
    
    print()

def demo_bulk_operations():
    """Demonstrate bulk operations"""
    print("=== BULK OPERATIONS ===")
    
    initialize_database('demo.db')
    
    # Bulk create
    new_users = []
    for i in range(3):
        user = User.create(
            username=f"bulk_user_{i}",
            email=f"bulk{i}@example.com",
            first_name=f"Bulk{i}",
            last_name="User",
            password_hash=User.make_password("password"),
            is_active=True
        )
        if user:
            new_users.append(user)
    
    print(f"✅ Created {len(new_users)} users in bulk")
    
    # Bulk update
    updated_count = User.update(
        filters={"username__startswith": "bulk_user_"},
        values={"is_active": False}
    )
    print(f"✅ Bulk updated {updated_count} users")
    
    # Bulk delete
    deleted_count = User.delete(username__startswith="bulk_user_")
    print(f"✅ Bulk deleted {deleted_count} users")
    print()

def demo_model_methods():
    """Demonstrate model instance methods"""
    print("=== MODEL INSTANCE METHODS ===")
    
    initialize_database('demo.db')
    
    user = User.get(username="john_doe")
    if user:
        # Use model methods
        user.set_password("newsecurepassword456")
        print("✅ Password updated using model method")
        
        # Check password
        password_correct = user.check_password("newsecurepassword456")
        print(f"✅ Password verification: {password_correct}")
        
        # Convert to dictionary
        user_dict = user.to_dict()
        print(f"✅ User as dictionary: {list(user_dict.keys())}")
        
    
    print()

def demo_thread_safety():
    """Demonstrate thread-safe operations"""
    print("=== THREAD-SAFE OPERATIONS ===")
    
    initialize_database('thread_test.db')
    
    results = []
    lock = threading.Lock()
    
    def create_user(thread_id):
        """Function to create user from different threads"""
        try:
            user = User.create(
                username=f"thread_user_{thread_id}",
                email=f"thread{thread_id}@example.com",
                first_name=f"Thread{thread_id}",
                last_name="User",
                password_hash=User.make_password("password")
            )
            if user:
                with lock:
                    results.append(user.username)
                print(f"✅ Thread {thread_id}: Created user {user.username}")
        except Exception as e:
            print(f"❌ Thread {thread_id}: Error - {e}")
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=create_user, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all users were created
    user_count = User.count()
    print(f"✅ Total users created across threads: {user_count}")
    print(f"✅ Unique users: {len(results)}")
    
    # Clean up
    User.delete(username__startswith="thread_user_")
    print("✅ Thread test users cleaned up")
    print()

def demo_error_handling():
    """Demonstrate error handling"""
    print("=== ERROR HANDLING ===")
    
    initialize_database('demo.db')
    
    # Try to create user with duplicate username
    try:
        duplicate_user = User.create(
            username="john_doe",  # Already exists
            email="new@example.com",
            first_name="New",
            last_name="User",
            password_hash=User.make_password("password")
        )
        if duplicate_user:
            print("❌ Duplicate user created (unexpected)")
        else:
            print("✅ Duplicate username correctly rejected")
    except Exception as e:
        print(f"✅ Duplicate username error handled: {str(e)[:50]}...")
    
    # Try to create user with invalid data
    try:
        invalid_user = User.create(
            username="",  # Empty username
            email="invalid-email",
            first_name="Test",
            last_name="User",
            password_hash=User.make_password("password")
        )
        if invalid_user:
            print("❌ Invalid user created (unexpected)")
        else:
            print("✅ Invalid data correctly rejected")
    except Exception as e:
        print(f"✅ Invalid data error handled: {str(e)[:50]}...")
    
    # Try to get non-existent record
    non_existent = User.get(username="nonexistent_user")
    if non_existent is None:
        print("✅ Non-existent record correctly returns None")
    
    print()

def main():
    """Run all demonstrations"""
    print("🚀 SQLite ORM Comprehensive Demonstration")
    print("=" * 50 + "\n")
    
    try:
        demo_basic_crud()
        demo_query_operations()
        demo_advanced_lookups()
        demo_relationships()
        demo_bulk_operations()
        demo_model_methods()
        demo_thread_safety()
        demo_error_handling()
        
        print("🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\n" + "=" * 50)
        print("📊 FEATURES DEMONSTRATED:")
        print("  • Basic CRUD operations")
        print("  • Advanced querying with Django-style lookups")
        print("  • Relationship management")
        print("  • Bulk operations")
        print("  • Model methods and properties")
        print("  • Thread-safe operations")
        print("  • Comprehensive error handling")
        print("  • Real-world blogging system scenario")
        print("\n💡 The ORM is now ready for your project!")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()