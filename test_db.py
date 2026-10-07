import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv("jj.env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured. Add it to jj.env or set it in the environment.")

engine = create_engine(DATABASE_URL)

with engine.connect():
    print("Database Connected Successfully!")
