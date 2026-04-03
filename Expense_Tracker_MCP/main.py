# import os
# import json
# import sqlite3
# from fastmcp import FastMCP

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "expenses.db")

# mcp = FastMCP(name="ExpenseTracker")

# def init_db():
#     with sqlite3.connect(DB_PATH) as c:
#         c.execute("""
#             CREATE TABLE IF NOT EXISTS expenses(
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 date TEXT, amount REAL, category TEXT, 
#                 subcategory TEXT, note TEXT
#             )
#         """)
# init_db()

# @mcp.tool()
# def add_expense(date: str, amount: float, category: str, subcategory: str = None, note: str = None):
#     """Add an expense. Required: date (YYYY-MM-DD), amount, category."""
#     with sqlite3.connect(DB_PATH) as c:
#         cur = c.execute(
#             "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
#             (date, amount, category, subcategory, note)
#         )
#         c.commit()
#         return {"status": "ok", "id": cur.lastrowid}

# @mcp.tool()
# def list_expenses(start_date: str, end_date: str):
#     """List expenses between two dates (YYYY-MM-DD)."""
#     with sqlite3.connect(DB_PATH) as c:
#         cur = c.execute("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date, end_date))
#         cols = [d[0] for d in cur.description]
#         return [dict(zip(cols, r)) for r in cur.fetchall()]

# if __name__ == "__main__":
#     # Do NOT print anything here; it will break the JSON-RPC communication
#     mcp.run()

import os
import json
import sqlite3
from fastmcp import FastMCP

# Setup paths relative to the script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

# Initialize FastMCP
mcp = FastMCP(name="ExpenseTracker")

# ───────── DB INIT ─────────
def init_db():
    """Creates the database and table if they don't exist."""
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                note TEXT
            )
        """)
        c.commit()

init_db()

# ───────── HELPER ─────────
def _rows_to_dict(cur):
    """Converts SQLite rows into a list of dictionaries for the LLM."""
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# ───────── ADD (CREATE) ─────────
@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = None, note: str = None):
    """
    Adds a new expense. 
    Required: date (YYYY-MM-DD), amount, category.
    Optional: subcategory, note.
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        c.commit()
        return {"status": "ok", "id": cur.lastrowid, "message": "Expense added successfully."}

# ───────── EDIT (UPDATE) ─────────
@mcp.tool()
def edit_expense(expense_id: int, amount: float = None, category: str = None, note: str = None):
    """
    Updates an existing expense by ID. 
    Only provide the fields that need changing.
    """
    fields, params = [], []

    if amount is not None:
        fields.append("amount=?")
        params.append(amount)
    if category is not None:
        fields.append("category=?")
        params.append(category)
    if note is not None:
        fields.append("note=?")
        params.append(note)

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    params.append(expense_id)
    query = f"UPDATE expenses SET {', '.join(fields)} WHERE id=?"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, params)
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"Expense ID {expense_id} not found."}
        return {"status": "ok", "message": f"Expense {expense_id} updated."}

# ───────── DELETE ─────────
@mcp.tool()
def delete_expense(expense_id: int):
    """Deletes a specific expense entry by its ID number."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        c.commit()
        if cur.rowcount == 0:
            return {"status": "error", "message": f"ID {expense_id} not found."}
        return {"status": "ok", "message": f"Deleted expense {expense_id}."}

# ───────── LIST & SEARCH (READ) ─────────
@mcp.tool()
def list_expenses(start_date: str, end_date: str, category: str = None):
    """
    Lists expenses between two dates (YYYY-MM-DD). 
    Optionally filters by category.
    """
    query = "SELECT * FROM expenses WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]

    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    query += " ORDER BY date DESC"

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, params)
        return _rows_to_dict(cur)

# ───────── SUMMARY (ANALYTICS) ─────────
@mcp.tool()
def get_spending_summary():
    """Returns a total of all spending grouped by category."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT category, SUM(amount) as total_spent FROM expenses GROUP BY category")
        return _rows_to_dict(cur)

# ───────── RUN ─────────
if __name__ == "__main__":
    # CRITICAL: No print() allowed; mcp.run() uses stdout for JSON communication.
    mcp.run()