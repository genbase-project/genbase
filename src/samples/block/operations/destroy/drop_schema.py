import os
import psycopg2
from typing import Dict, Any

def drop_schema(config: Dict[str, Any]) -> None:
    """
    Drops PostgreSQL schema and all its objects.
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
        
        # Extract schema name from schema.sql
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
            # Simple parsing to find schema name - in practice, you'd want more robust parsing
            import re
            schema_match = re.search(r'CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', schema_sql, re.IGNORECASE)
            if not schema_match:
                raise Exception("Could not determine schema name from schema.sql")
            
            schema_name = schema_match.group(1)
        
        # Drop schema with CASCADE to remove all objects
        cursor.execute(f'DROP SCHEMA IF EXISTS {schema_name} CASCADE')
        conn.commit()
        
        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Failed to drop schema: {str(e)}")
