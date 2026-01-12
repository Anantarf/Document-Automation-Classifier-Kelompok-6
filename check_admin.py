from app.database import SessionLocal
from app.models import User
from app.routers.auth import verify_password, get_password_hash

def check():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "pelamampang").first()
        if not user:
            print("User 'pelamampang' NOT FOUND. Creating now...")
            hashed = get_password_hash("pelamampang123")
            new_user = User(username="pelamampang", password_hash=hashed, role="admin")
            db.add(new_user)
            db.commit()
            print("User 'pelamampang' CREATED successfully.")
        else:
            print(f"User 'pelamampang' FOUND. Role: {user.role}")
            is_valid = verify_password("pelamampang123", user.password_hash)
            print(f"Password valid: {is_valid}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
