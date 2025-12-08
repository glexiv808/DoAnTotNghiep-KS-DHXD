"""
Script khởi tạo database cho ML Prediction Service
Chạy: python init_db.py
"""

import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Cấu hình
DATABASE_URL = "sqlite:///./ml_service.db"  # Hoặc PostgreSQL, MySQL
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# ============================================================
# MODELS (Copy từ app.py)
# ============================================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

# ============================================================
# FUNCTIONS
# ============================================================

def check_database_exists():
    """Kiểm tra database có tồn tại không"""
    if "sqlite" in DATABASE_URL:
        db_file = DATABASE_URL.replace("sqlite:///", "").replace("./", "")
        return os.path.exists(db_file)
    return True  # Với PostgreSQL/MySQL, giả định đã tạo DB

def create_tables(engine):
    """Tạo tất cả bảng"""
    print("📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

def check_tables(engine):
    """Kiểm tra các bảng đã tồn tại"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📋 Tables in database: {tables}")
    return tables

def create_admin_user(session):
    """Tạo user admin mặc định"""
    try:
        # Kiểm tra admin đã tồn tại chưa
        existing_admin = session.query(User).filter_by(username="admin").first()
        if existing_admin:
            print("⚠️  Admin user already exists!")
            return
        
        # Tạo admin user
        admin = User(
            username="admin",
            email="admin@mlservice.com",
            password = "admin123",  # <= 72 ký tự
            hashed_password = pwd_context.hash(password),
            full_name="Administrator",
            is_active=True
        )
        
        session.add(admin)
        session.commit()
        
        print("✅ Admin user created!")
        print("   Username: admin")
        print("   Password: admin123")
        print("   ⚠️  PLEASE CHANGE PASSWORD IN PRODUCTION!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating admin user: {e}")

def create_sample_users(session):
    """Tạo users mẫu"""
    try:
        sample_users = [
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "john123",
                "full_name": "John Doe"
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "jane123",
                "full_name": "Jane Smith"
            }
        ]
        
        for user_data in sample_users:
            # Kiểm tra user đã tồn tại chưa
            existing = session.query(User).filter_by(
                username=user_data["username"]
            ).first()
            
            if not existing:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=pwd_context.hash(user_data["password"]),
                    full_name=user_data["full_name"],
                    is_active=True
                )
                session.add(user)
                print(f"✅ Created user: {user_data['username']}")
            else:
                print(f"⚠️  User {user_data['username']} already exists")
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating sample users: {e}")

def show_all_users(session):
    """Hiển thị tất cả users"""
    users = session.query(User).all()
    
    if not users:
        print("📭 No users in database")
        return
    
    print("\n" + "=" * 80)
    print("👥 ALL USERS IN DATABASE")
    print("=" * 80)
    print(f"{'ID':<5} {'Username':<15} {'Email':<30} {'Full Name':<20} {'Active':<8}")
    print("-" * 80)
    
    for user in users:
        print(f"{user.id:<5} {user.username:<15} {user.email:<30} "
              f"{user.full_name or 'N/A':<20} {'Yes' if user.is_active else 'No':<8}")
    
    print("=" * 80)

def reset_database(engine):
    """Xóa và tạo lại database"""
    print("⚠️  WARNING: This will DELETE all data!")
    confirm = input("Type 'YES' to confirm: ")
    
    if confirm == "YES":
        print("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("📦 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database reset successfully!")
    else:
        print("❌ Reset cancelled")

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("🗄️  ML PREDICTION SERVICE - DATABASE INITIALIZATION")
    print("=" * 80)
    
    # Tạo engine
    print(f"\n📍 Database URL: {DATABASE_URL}")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    
    # Tạo session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        # Menu
        print("\n" + "=" * 80)
        print("CHOOSE AN OPTION:")
        print("=" * 80)
        print("1. Initialize database (create tables)")
        print("2. Create admin user")
        print("3. Create sample users")
        print("4. Show all users")
        print("5. Reset database (⚠️  DANGER)")
        print("6. Full setup (1 + 2 + 3)")
        print("=" * 80)
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            create_tables(engine)
            check_tables(engine)
            
        elif choice == "2":
            create_tables(engine)
            create_admin_user(session)
            
        elif choice == "3":
            create_tables(engine)
            create_sample_users(session)
            
        elif choice == "4":
            show_all_users(session)
            
        elif choice == "5":
            reset_database(engine)
            
        elif choice == "6":
            print("\n🚀 Full setup starting...\n")
            create_tables(engine)
            check_tables(engine)
            create_admin_user(session)
            create_sample_users(session)
            show_all_users(session)
            print("\n✅ Full setup completed!")
            
        else:
            print("❌ Invalid choice!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        session.close()
        print("\n👋 Done!")

# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload.username).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not pwd_context.verify(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        # update last login
        user.last_login = datetime.utcnow()
        db.add(user)
        db.commit()
        return {"success": True, "username": user.username, "full_name": user.full_name or user.username}
    finally:
        db.close()