from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_a3GpUdvXS0WO@ep-lucky-field-a19xu8ps-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

engine = create_engine(DATABASE_URL)
Base = declarative_base()