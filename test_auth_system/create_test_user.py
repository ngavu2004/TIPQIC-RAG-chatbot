#!/usr/bin/env python3
"""
Script to create a test user for the TIPQIC RAG Chatbot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import SessionLocal, User, get_password_hash

def create_test_user():
    """Create a test user in the database"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == "sata2").first()
        if existing_user:
            print("✅ Test user 'sata2' already exists")
            return
        
        # Create test user
        hashed_password = get_password_hash("Qwertyuiop123#")
        test_user = User(
            username="sata2",
            password_hash=hashed_password,
            email="test@example.com"
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print("✅ Test user 'sata2' created successfully!")
        print(f"   Username: sata2")
        print(f"   Password: Qwertyuiop123#")
        print(f"   Email: test@example.com")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user() 