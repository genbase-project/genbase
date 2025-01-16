import os
import psycopg2
from typing import Dict, Any

def create_schema(config: Dict[str, Any]) -> None:
    """
    Creates PostgreSQL schema based on schema.sql file.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB', 'postgres'),
            sslmode='require' if os.getenv('POSTGRES_SSL', 'true').lower() == 'true' else 'disable'
        )
        
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
            
        if not schema_sql.strip():
            raise Exception("schema.sql is empty")
            
        cursor.execute(schema_sql)
        conn.commit()
        
        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Failed to create schema: {str(e)}")

