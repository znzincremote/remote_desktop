from datetime import datetime
import bcrypt
from sqlalchemy import String, Boolean, BigInteger, Column, DateTime
from sqlalchemy.orm import Session

from db_conf import Base, engine

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, default=datetime.now())
    joined_at = Column(DateTime, default=datetime.now())

    def create_user(self, db: Session, user_data : dict):
        user = User(**user_data)
        try:
            user.set_password(user_data["password"])
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception as e:
            print("Exception in creating user", e)
            return None

    def set_password(self, password: str):
        """Hash the password and set it."""
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hashed password."""
        print(f"Stored Hash: {self.password}")  # Debug line to print the stored hash
        print(f"Password to check: {password}")
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    def set_password(self, password: str):
        """Hash the password and set it."""
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, first_name={self.first_name}, last_name={self.last_name})>"

class SystemInfo(Base):
    __tablename__ = "system_info"

    id = Column(BigInteger, primary_key=True, nullable=False)
    unique_system_id = Column(String, nullable=False, unique=True)
    operating_system = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    remote_desktop_address = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.now())
    last_online = Column(DateTime, default=datetime.now())

    def __repr__(self):
        return f"<SystemInfo(id={self.id}, unique_system_id={self.unique_system_id}, operating_system={self.operating_system})>"

Base.metadata.create_all(bind=engine)