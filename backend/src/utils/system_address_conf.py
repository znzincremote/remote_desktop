from datetime import datetime
import random

from sqlalchemy.orm import Session

from models import SystemInfo

def generate_unique_address(db: Session):
    """ Generate a unique 10-digit address for the system """
    while True:
        unique_address = random.randint(1000000000, 9999999999)  # Generate a 10-digit number
        # Check if this address already exists in the database
        existing = db.query(SystemInfo).filter(SystemInfo.remote_desktop_address == unique_address).first()
        if not existing:
            return unique_address


def get_system_by_unique_system_id(db : Session, unique_system_id : str):
    """ Get existing system in database with unique_system_id or None """
    result = db.query(SystemInfo).filter(SystemInfo.unique_system_id == unique_system_id).first()
    if result:
        result.last_online = datetime.now()
        db.commit()
        db.refresh(result)
    return result


def create_new_system(db: Session, data):
    """ Create a new system in database """
    new_system = SystemInfo(**data)
    new_system.remote_desktop_address = generate_unique_address(db)
    db.add(new_system)
    db.commit()
    db.refresh(new_system)
    return new_system


def get_system_from_database(db : Session, unique_system_id : str, data : dict):
    """ Get or create the system from database. 
        - Return system if it already exist 
        - Create and return system if does not exist
    """
    system = get_system_by_unique_system_id(db, unique_system_id=unique_system_id)
    if system:
        return system
    new_system = create_new_system(db, data)
    return new_system


def get_address(db : Session, unique_system_id : str, data : dict):
    """ Get or create unique, static address for the system in the database """
    address = get_system_from_database(db, unique_system_id=unique_system_id, data=data).remote_desktop_address
    return address
