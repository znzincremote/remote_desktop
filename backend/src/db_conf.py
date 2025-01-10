import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


POSTGRES_USER=os.environ["POSTGRES_USER"]
POSTGRES_HOST=os.environ["DB_HOST"]
POSTGRES_DB=os.environ["POSTGRES_DB"]
POSTGRES_PASSWORD=os.environ["POSTGRES_PASSWORD"]
POSTGRES_PORT = os.environ["DB_PORT"]

SQLALCHEMY_POSTGRES_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_POSTGRES_URL)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
