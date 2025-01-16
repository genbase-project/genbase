import os
import psycopg2
from typing import Dict, Any

def validate_connection(config: Dict[str, Any]) -> bool:
    """
    Validates PostgreSQL connection using provided configuration.
    Returns True if connection is successful, raises exception otherwise.
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
        conn.close()
        return True
    except Exception as e:
        raise Exception(f"Failed to connect to PostgreSQL: {str(e)}")