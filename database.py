"""
Database management module for Library Management System
Handles SQLite tables, relations, queries, seed data, and business logic.
"""
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd

DB_PATH = "library.db"

BORROW_LIMITS = {
    "Student": 3,
    "Teacher": 5
}

DEFAULT_FINE_PER_DAY = 1.0  # $1.00 per late day
DEFAULT_LOAN_DAYS = 14     # 14 days standard period

def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = 1")
    return conn

def init_db(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()

    # Books Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT 'General',
            total_copies INTEGER NOT NULL CHECK(total_copies >= 1),
            available_copies INTEGER NOT NULL CHECK(available_copies >= 0)
        )
    """)

    # Members Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            member_type TEXT NOT NULL CHECK(member_type IN ('Student', 'Teacher')),
            join_date TEXT NOT NULL
        )
    """)

    # Transactions Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL DEFAULT 0.0,
            status TEXT NOT NULL CHECK(status IN ('Issued', 'Returned')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT
        )
    """)

    conn.commit()
    conn.close()

# ----------------- BOOK FUNCTIONS -----------------
def add_book(title, author, isbn, total_copies, category="General", db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO books (title, author, isbn, category, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), author.strip(), isbn.strip(), category.strip(), int(total_copies), int(total_copies)))
        conn.commit()
        return True, f"Book '{title}' added successfully!"
    except sqlite3.IntegrityError:
        return False, f"A book with ISBN '{isbn}' already exists in the catalog."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def delete_book(book_id, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        # Check if copies are currently issued
        cur.execute("SELECT COUNT(*) FROM transactions WHERE book_id = ? AND status = 'Issued'", (book_id,))
        active_count = cur.fetchone()[0]
        if active_count > 0:
            return False, f"Cannot delete book: {active_count} copy/copies currently issued out."

        # Delete any historical returned transactions to maintain integrity
        cur.execute("DELETE FROM transactions WHERE book_id = ?", (book_id,))
        cur.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return True, "Book deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def search_books(query="", filter_by="All", db_path=DB_PATH):
    conn = get_connection(db_path)
    query_str = f"%{query.strip()}%"
    
    if not query.strip():
        sql = "SELECT id, title, author, isbn, category, total_copies, available_copies FROM books ORDER BY id DESC"
        df = pd.read_sql_query(sql, conn)
    elif filter_by == "Title":
        sql = """SELECT id, title, author, isbn, category, total_copies, available_copies 
                 FROM books WHERE title LIKE ? ORDER BY title ASC"""
        df = pd.read_sql_query(sql, conn, params=(query_str,))
    elif filter_by == "Author":
        sql = """SELECT id, title, author, isbn, category, total_copies, available_copies 
                 FROM books WHERE author LIKE ? ORDER BY author ASC"""
        df = pd.read_sql_query(sql, conn, params=(query_str,))
    else:  # All
        sql = """SELECT id, title, author, isbn, category, total_copies, available_copies 
                 FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? ORDER BY id DESC"""
        df = pd.read_sql_query(sql, conn, params=(query_str, query_str, query_str))
    
    conn.close()
    return df

# ----------------- MEMBER FUNCTIONS -----------------
def register_member(name, email, member_type, phone="", db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        join_dt = date.today().isoformat()
        cur.execute("""
            INSERT INTO members (name, email, phone, member_type, join_date)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), email.strip().lower(), phone.strip(), member_type, join_dt))
        conn.commit()
        return True, f"{member_type} '{name}' registered successfully!"
    except sqlite3.IntegrityError:
        return False, f"Member with email '{email}' is already registered."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def delete_member(member_id, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND status = 'Issued'", (member_id,))
        active_loans = cur.fetchone()[0]
        if active_loans > 0:
            return False, f"Cannot delete member: Member has {active_loans} book(s) currently borrowed."

        cur.execute("DELETE FROM transactions WHERE member_id = ?", (member_id,))
        cur.execute("DELETE FROM members WHERE id = ?", (member_id,))
        conn.commit()
        return True, "Member deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_members_with_stats(db_path=DB_PATH):
    conn = get_connection(db_path)
    sql = """
        SELECT 
            m.id,
            m.name,
            m.email,
            m.phone,
            m.member_type,
            m.join_date,
            CASE WHEN m.member_type = 'Student' THEN 3 ELSE 5 END AS borrow_limit,
            COUNT(t.id) AS current_borrowed
        FROM members m
        LEFT JOIN transactions t ON m.id = t.member_id AND t.status = 'Issued'
        GROUP BY m.id
        ORDER BY m.id DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ----------------- ISSUE & RETURN FUNCTIONS -----------------
def issue_book(book_id, member_id, issue_date_val=None, loan_days=DEFAULT_LOAN_DAYS, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        # Check member and their current borrow count
        cur.execute("SELECT name, member_type FROM members WHERE id = ?", (member_id,))
        member = cur.fetchone()
        if not member:
            return False, "Member not found."
        m_name, m_type = member
        limit = BORROW_LIMITS.get(m_type, 3)

        cur.execute("SELECT COUNT(*) FROM transactions WHERE member_id = ? AND status = 'Issued'", (member_id,))
        active_loans = cur.fetchone()[0]

        if active_loans >= limit:
            return False, f"Borrow limit reached! {m_type} '{m_name}' has already borrowed {active_loans}/{limit} books."

        # Check book availability
        cur.execute("SELECT title, available_copies FROM books WHERE id = ?", (book_id,))
        book = cur.fetchone()
        if not book:
            return False, "Book not found."
        b_title, avail_copies = book

        if avail_copies <= 0:
            return False, f"'{b_title}' has no copies available to borrow right now."

        # Compute dates
        if issue_date_val is None:
            issue_date_val = date.today()
        due_date_val = issue_date_val + timedelta(days=loan_days)

        # Record transaction and update inventory
        cur.execute("""
            INSERT INTO transactions (book_id, member_id, issue_date, due_date, status)
            VALUES (?, ?, ?, ?, 'Issued')
        """, (book_id, member_id, issue_date_val.isoformat(), due_date_val.isoformat()))

        cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = ?", (book_id,))
        conn.commit()
        return True, f"'{b_title}' successfully issued to {m_name}. Due on {due_date_val.isoformat()}."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def calculate_fine(due_date_str, return_date_val, fine_per_day=DEFAULT_FINE_PER_DAY):
    due_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    if return_date_val > due_dt:
        days_late = (return_date_val - due_dt).days
        return days_late, round(days_late * fine_per_day, 2)
    return 0, 0.0

def return_book(transaction_id, return_date_val=None, fine_per_day=DEFAULT_FINE_PER_DAY, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.book_id, t.issue_date, t.due_date, b.title, m.name
            FROM transactions t
            JOIN books b ON t.book_id = b.id
            JOIN members m ON t.member_id = m.id
            WHERE t.id = ? AND t.status = 'Issued'
        """, (transaction_id,))
        row = cur.fetchone()
        if not row:
            return False, "Active transaction not found."

        book_id, issue_date_str, due_date_str, book_title, member_name = row
        issue_dt = datetime.strptime(issue_date_str, "%Y-%m-%d").date()

        if return_date_val is None:
            return_date_val = date.today()

        if return_date_val < issue_dt:
            return False, f"Return date cannot be earlier than issue date ({issue_date_str})."

        days_late, fine_amount = calculate_fine(due_date_str, return_date_val, fine_per_day)

        cur.execute("""
            UPDATE transactions
            SET return_date = ?, fine = ?, status = 'Returned'
            WHERE id = ?
        """, (return_date_val.isoformat(), fine_amount, transaction_id))

        cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (book_id,))
        conn.commit()

        if fine_amount > 0:
            msg = f"'{book_title}' returned by {member_name}. Late by {days_late} day(s). Fine incurred: ${fine_amount:.2f}."
        else:
            msg = f"'{book_title}' returned on time by {member_name}. No fine."
        return True, msg
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# ----------------- REPORTING & QUERIES -----------------
def get_overdue_books(ref_date=None, fine_per_day=DEFAULT_FINE_PER_DAY, db_path=DB_PATH):
    if ref_date is None:
        ref_date = date.today()
    conn = get_connection(db_path)
    sql = """
        SELECT 
            t.id AS tx_id,
            b.id AS book_id,
            b.title AS book_title,
            m.id AS member_id,
            m.name AS member_name,
            m.member_type,
            m.email,
            t.issue_date,
            t.due_date
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN members m ON t.member_id = m.id
        WHERE t.status = 'Issued' AND date(t.due_date) < date(?)
        ORDER BY t.due_date ASC
    """
    df = pd.read_sql_query(sql, conn, params=(ref_date.isoformat(),))
    conn.close()

    if not df.empty:
        days_late_list = []
        fine_list = []
        for due_str in df["due_date"]:
            days_late, fine = calculate_fine(due_str, ref_date, fine_per_day)
            days_late_list.append(days_late)
            fine_list.append(fine)
        df["days_overdue"] = days_late_list
        df["accrued_fine"] = fine_list
    return df

def get_active_loans(db_path=DB_PATH):
    conn = get_connection(db_path)
    sql = """
        SELECT 
            t.id AS tx_id,
            b.title AS book_title,
            m.name AS member_name,
            m.member_type,
            t.issue_date,
            t.due_date
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN members m ON t.member_id = m.id
        WHERE t.status = 'Issued'
        ORDER BY t.due_date ASC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def get_all_transactions(db_path=DB_PATH):
    conn = get_connection(db_path)
    sql = """
        SELECT 
            t.id AS tx_id,
            b.title AS book_title,
            m.name AS member_name,
            m.member_type,
            t.issue_date,
            t.due_date,
            COALESCE(t.return_date, '—') AS return_date,
            t.fine,
            t.status
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN members m ON t.member_id = m.id
        ORDER BY t.id DESC
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def get_stats(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_copies), 0), COALESCE(SUM(available_copies), 0) FROM books")
    total_titles, total_copies, avail_copies = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM members")
    total_members = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions WHERE status = 'Issued'")
    issued_books = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(fine), 0.0) FROM transactions WHERE status = 'Returned'")
    total_fines_collected = cur.fetchone()[0]

    conn.close()
    return {
        "total_titles": total_titles,
        "total_copies": total_copies,
        "avail_copies": avail_copies,
        "total_members": total_members,
        "issued_books": issued_books,
        "fines_collected": total_fines_collected
    }

# ----------------- SEED DATA -----------------
def seed_sample_data(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] > 0:
        conn.close()
        return False, "Database already contains data."

    sample_books = [
        ("Clean Code", "Robert C. Martin", "978-0132350884", "Software Engineering", 4),
        ("The Pragmatic Programmer", "David Thomas & Andrew Hunt", "978-0135957059", "Software Engineering", 3),
        ("Introduction to Algorithms (CLRS)", "Thomas H. Cormen", "978-0262033848", "Computer Science", 5),
        ("Designing Data-Intensive Applications", "Martin Kleppmann", "978-1449373320", "Databases", 3),
        ("To Kill a Mockingbird", "Harper Lee", "978-0061120084", "Literature", 4),
        ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "978-0062316097", "History", 5),
        ("Deep Learning", "Ian Goodfellow", "978-0262035613", "Artificial Intelligence", 2),
    ]

    for title, author, isbn, cat, copies in sample_books:
        cur.execute("""
            INSERT INTO books (title, author, isbn, category, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, author, isbn, cat, copies, copies))

    sample_members = [
        ("Alice Johnson", "alice.johnson@university.edu", "+1-555-0101", "Student", "2024-01-15"),
        ("Bob Smith", "bob.smith@university.edu", "+1-555-0102", "Student", "2024-02-10"),
        ("Dr. Eleanor Vance", "eleanor.vance@university.edu", "+1-555-0201", "Teacher", "2023-09-01"),
        ("Prof. Marcus Brody", "marcus.brody@university.edu", "+1-555-0202", "Teacher", "2023-10-15"),
        ("Charlie Brown", "charlie.b@university.edu", "+1-555-0103", "Student", "2024-03-01"),
    ]

    for name, email, phone, m_type, j_date in sample_members:
        cur.execute("""
            INSERT INTO members (name, email, phone, member_type, join_date)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, phone, m_type, j_date))

    conn.commit()

    # Seed sample transactions: 1 on-time returned, 1 normal active loan, 1 overdue loan
    today = date.today()

    # Loan 1: Alice has an overdue book (Issued 24 days ago, due 10 days ago)
    issue_overdue = today - timedelta(days=24)
    due_overdue = issue_overdue + timedelta(days=14)
    cur.execute("""
        INSERT INTO transactions (book_id, member_id, issue_date, due_date, status)
        VALUES (1, 1, ?, ?, 'Issued')
    """, (issue_overdue.isoformat(), due_overdue.isoformat()))
    cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = 1")

    # Loan 2: Dr. Eleanor Vance has an active loan within due date (Issued 4 days ago)
    issue_active = today - timedelta(days=4)
    due_active = issue_active + timedelta(days=14)
    cur.execute("""
        INSERT INTO transactions (book_id, member_id, issue_date, due_date, status)
        VALUES (2, 3, ?, ?, 'Issued')
    """, (issue_active.isoformat(), due_active.isoformat()))
    cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id = 2")

    # Loan 3: Charlie Brown returned a book late and paid fine
    ret_issue = today - timedelta(days=30)
    ret_due = ret_issue + timedelta(days=14)
    ret_date = today - timedelta(days=10) # 6 days late => $6.00
    cur.execute("""
        INSERT INTO transactions (book_id, member_id, issue_date, due_date, return_date, fine, status)
        VALUES (3, 5, ?, ?, ?, 6.00, 'Returned')
    """, (ret_issue.isoformat(), ret_due.isoformat(), ret_date.isoformat()))

    conn.commit()
    conn.close()
    return True, "Sample data populated successfully with books, members, active loans, and overdue records!"
