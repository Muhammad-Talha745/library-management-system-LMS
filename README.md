# 📚 Library Management System (Streamlit + SQLite)

A complete, production-ready Library Management web application built with Python 3, Streamlit, SQLite, and Pandas. Designed for librarians to easily manage book catalogs, member registrations, circulation (issue/return), borrow limits, and overdue fine calculations.

---

## ✨ Features
1. **Book Catalog Management**
   - Add new books with ISBN, category, and multi-copy tracking.
   - Search books by title, author, or ISBN in real-time.
   - Safe deletion (prohibits deleting books currently checked out).

2. **Member Registration & Quota Enforcement**
   - Distinct roles: **Students** and **Teachers**.
   - Enforced borrow limits:
     - **Student Limit:** Maximum 3 books.
     - **Teacher Limit:** Maximum 5 books.
   - Live member directory displaying active borrows vs. allowance.

3. **Circulation (Issue & Return)**
   - Issue books with dynamic loan period and automatic due date calculation.
   - Real-time stock validation (cannot issue out-of-stock books).
   - Return processing with automatic fine calculation for overdue items ($1.00/day default).
   - Live fine preview prior to submission.

4. **Overdue & Fine Tracker**
   - Instant listing of all overdue books.
   - Tracks overdue days and accumulated penalty amounts.
   - One-click overdue book return and fine collection.

5. **Circulation Audit & CSV Export**
   - Complete log of all past and active transactions.
   - One-click CSV export of transaction history.

6. **Pre-populated Demo Data**
   - Comes preloaded with books, members, active loans, and overdue records so you can test it immediately!

---

## 🚀 How to Run the Application

### 1. Requirements
Ensure you have **Python 3.9+** installed on your system.

### 2. Install Dependencies
Open your terminal inside this extracted directory and run:
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
Run the Streamlit application:
```bash
streamlit run app.py
```

The web application will open automatically in your default browser at:
`http://localhost:8501`

---

## 📁 File Structure
- `app.py`: Main Streamlit web application interface and navigation.
- `database.py`: SQLite database queries, business rules, quota checking, and seed data.
- `requirements.txt`: Python package dependencies (`streamlit`, `pandas`).
- `run.sh` / `run.bat`: Quick launch scripts for macOS/Linux and Windows.
- `library.db`: SQLite database file (created automatically on first launch).
