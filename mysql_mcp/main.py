from fastmcp import FastMCP
import mysql.connector
from mysql.connector import Error
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = FastMCP("mysql-manager")

# Get credentials from .env file
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "8***")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")

# ----------------- DB HELPERS -----------------
def get_db_config(db_name=None):
    config = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD
    }
    if db_name:
        config["database"] = db_name
    return config

def sanitize_name(name: str):
    """Simple check to prevent basic SQL injection on identifiers."""
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        raise ValueError(f"Invalid identifier: {name}")
    return name

# ----------------- MCP TOOLS -----------------

@app.tool()
def create_database(db_name: str) -> str:
    """Creates a new MySQL database."""
    try:
        db_name = sanitize_name(db_name)
        with mysql.connector.connect(**get_db_config()) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                return f"✅ Database '{db_name}' ready."
    except Exception as e:
        return f"❌ Database Error: {str(e)}"

@app.tool()
def create_table(db_name: str, table_name: str, columns: dict) -> str:
    """
    Creates a new table. 
    Example for columns: {"id": "INT AUTO_INCREMENT PRIMARY KEY", "name": "VARCHAR(255)", "age": "INT"}
    """
    try:
        db_name = sanitize_name(db_name)
        table_name = sanitize_name(table_name)
        
        col_definitions = ", ".join([f"{col} {dtype}" for col, dtype in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_definitions})"
        
        with mysql.connector.connect(**get_db_config(db_name)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return f"✅ Table '{table_name}' created in '{db_name}'."
    except Exception as e:
        return f"❌ Table Creation Error: {str(e)}"

@app.tool()
def insert_data(db_name: str, table_name: str, data: dict) -> str:
    """Inserts a dictionary of data into a table securely."""
    try:
        db_name = sanitize_name(db_name)
        table_name = sanitize_name(table_name)
        
        with mysql.connector.connect(**get_db_config(db_name)) as conn:
            with conn.cursor() as cursor:
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                values = tuple(data.values())
                
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cursor.execute(query, values)
                conn.commit()
                return f"✅ Data inserted into {table_name}."
    except Exception as e:
        return f"❌ Insert Error: {str(e)}"

@app.tool()
def fetch_table_data(db_name: str, table_name: str, limit: int = 10) -> list:
    """Fetches records from a table. Returns list of rows."""
    try:
        db_name = sanitize_name(db_name)
        table_name = sanitize_name(table_name)
        with mysql.connector.connect(**get_db_config(db_name)) as conn:
            with conn.cursor(dictionary=True) as cursor:
                query = f"SELECT * FROM {table_name} LIMIT %s"
                cursor.execute(query, (limit,))
                return cursor.fetchall()
    except Exception as e:
        return [{"error": str(e)}]

@app.tool()
def update_data(db_name: str, table_name: str, updates: dict, condition_col: str, condition_val: str) -> str:
    """
    Updates records securely. 
    Example: updates={"age": 21}, condition_col="name", condition_val="Alice"
    """
    try:
        db_name = sanitize_name(db_name)
        table_name = sanitize_name(table_name)
        condition_col = sanitize_name(condition_col)
        
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [condition_val]
        
        query = f"UPDATE {table_name} SET {set_clause} WHERE {condition_col} = %s"
        
        with mysql.connector.connect(**get_db_config(db_name)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, values)
                conn.commit()
                return f"✅ Updated {cursor.rowcount} row(s) in {table_name}."
    except Exception as e:
        return f"❌ Update Error: {str(e)}"

@app.tool()
def delete_data(db_name: str, table_name: str, condition_col: str, condition_val: str) -> str:
    """Deletes records securely where condition_col = condition_val."""
    try:
        db_name = sanitize_name(db_name)
        table_name = sanitize_name(table_name)
        condition_col = sanitize_name(condition_col)
        
        query = f"DELETE FROM {table_name} WHERE {condition_col} = %s"
        
        with mysql.connector.connect(**get_db_config(db_name)) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (condition_val,))
                conn.commit()
                return f"✅ Deleted {cursor.rowcount} row(s) from {table_name}."
    except Exception as e:
        return f"❌ Delete Error: {str(e)}"

if __name__ == "__main__":
    app.run()
