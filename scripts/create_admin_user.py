#!/usr/bin/env python3
"""
Script to make the test user an admin for the TIPQIC RAG Chatbot
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import SessionLocal, User

def make_user_admin():
    db = SessionLocal()
    try:
        # Find the test user
        user = db.query(User).filter(User.username == "sata2").first()
        if not user:
            print("❌ Test user 'sata2' not found. Please create the user first.")
            return
        
        if user.is_admin:
            print("✅ User 'sata2' is already an admin!")
            return
        
        # Make user admin
        user.is_admin = True
        db.commit()
        print("✅ User 'sata2' is now an admin!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Admin: {user.is_admin}")
        
    except Exception as e:
        print(f"❌ Error making user admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    make_user_admin() 