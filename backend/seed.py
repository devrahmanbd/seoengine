"""
Database seeding script for ZenSEO Admin
Run: python seed.py
"""

from app.core.database import SessionLocal, init_db
from app.core.db_models import User, Website, APIKey, Admin
from app.core.auth import get_password_hash
import uuid


def seed():
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    
    # Check if admin exists
    existing_admin = db.query(Admin).first()
    if not existing_admin:
        print("Creating admin user...")
        admin = Admin(
            id=str(uuid.uuid4()),
            email="admin@zenseo.ai",
            name="Admin",
            password_hash=get_password_hash("admin123")
        )
        db.add(admin)
        print("Admin created: admin@zenseo.ai / admin123")
    else:
        print("Admin already exists")
    
    # Check if demo users exist
    if db.query(User).count() == 0:
        print("Creating demo users...")
        
        users = [
            User(
                id=str(uuid.uuid4()),
                email="john@example.com",
                name="John Doe",
                password_hash=get_password_hash("password"),
                plan="pro",
                subscription_status="active",
                api_calls_used=7234,
                api_calls_limit=10000,
            ),
            User(
                id=str(uuid.uuid4()),
                email="jane@example.com",
                name="Jane Smith",
                password_hash=get_password_hash("password"),
                plan="free",
                subscription_status="active",
                api_calls_used=234,
                api_calls_limit=1000,
            ),
            User(
                id=str(uuid.uuid4()),
                email="mike@example.com",
                name="Mike Wilson",
                password_hash=get_password_hash("password"),
                plan="enterprise",
                subscription_status="active",
                api_calls_used=45000,
                api_calls_limit=50000,
            ),
        ]
        
        for user in users:
            db.add(user)
        
        db.commit()
        
        # Create websites for users
        print("Creating demo websites...")
        websites = [
            Website(
                id=str(uuid.uuid4()),
                user_id=users[0].id,
                url="https://acme.com/blog",
                name="Acme Corp Blog",
                platform="wordpress",
                api_key=f"zenseo_wp_{uuid.uuid4().hex[:12]}",
                status="connected",
                seo_score=78,
            ),
            Website(
                id=str(uuid.uuid4()),
                user_id=users[1].id,
                url="https://techstart.io",
                name="TechStart Landing",
                platform="custom",
                api_key=f"zenseo_wp_{uuid.uuid4().hex[:12]}",
                status="connected",
                seo_score=92,
            ),
            Website(
                id=str(uuid.uuid4()),
                user_id=users[2].id,
                url="https://mystore.myshopify.com",
                name="Shopify Store",
                platform="shopify",
                api_key=f"zenseo_wp_{uuid.uuid4().hex[:12]}",
                status="error",
                seo_score=34,
            ),
        ]
        
        for site in websites:
            db.add(site)
        
        db.commit()
        print(f"Created {len(users)} users and {len(websites)} websites")
    else:
        print("Demo data already exists")
    
    db.close()
    print("\n✅ Database seeded successfully!")
    print("\nLogin credentials:")
    print("  Email: admin@zenseo.ai")
    print("  Password: admin123")


if __name__ == "__main__":
    seed()