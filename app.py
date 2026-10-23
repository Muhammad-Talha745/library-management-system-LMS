"""
Streamlit Web Application for Library Management System
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database as db

# Page Config
st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #2b5c8f;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .badge-student {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-teacher {
        background-color: #f3e5f5;
        color: #4a148c;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database
db.init_db()

# Auto-seed sample data on first run if database is empty
stats = db.get_stats()
if stats["total_titles"] == 0 and stats["total_members"] == 0:
    db.seed_sample_data()
    stats = db.get_stats()

# ----------------- SIDEBAR -----------------
st.sidebar.markdown("## 📚 Library Portal")
st.sidebar.caption("Modern Library Management & Circulation System")

menu = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Dashboard",
        "📖 Book Management",
        "👥 Member Registration",
        "🔄 Issue & Return",
        "🚨 Overdue & Fine Tracker",
        "📜 Transaction History",
        "⚙️ Database & Seed Settings"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Lending Policies")
st.sidebar.info(
    f"• **Student Limit:** {db.BORROW_LIMITS['Student']} books\n\n"
    f"• **Teacher Limit:** {db.BORROW_LIMITS['Teacher']} books\n\n"
    f"• **Standard Loan:** {db.DEFAULT_LOAN_DAYS} days\n\n"
    f"• **Overdue Fine:** ${db.DEFAULT_FINE_PER_DAY:.2f} per day late"
)

# ----------------- 1. DASHBOARD -----------------
if menu == "📊 Dashboard":
    st.title("📊 Library Overview Dashboard")
    st.markdown("Real-time snapshot of library circulation, inventory, and pending fines.")

    stats = db.get_stats()
    overdue_df = db.get_overdue_books()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📚 Unique Titles", stats["total_titles"])
    c2.metric("📦 Total Copies", stats["total_copies"])
    c3.metric("✅ Available on Shelves", stats["avail_copies"])
    c4.metric("👥 Registered Members", stats["total_members"])
    c5.metric("🚨 Overdue Books", len(overdue_df), delta=f"{len(overdue_df)} late", delta_color="inverse")

    st.markdown("---")

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("🚨 Overdue Book Alerts")
        if overdue_df.empty:
            st.success("🎉 Wonderful! There are currently no overdue books.")
        else:
            display_overdue = overdue_df[[
                "tx_id", "book_title", "member_name", "member_type", "due_date", "days_overdue", "accrued_fine"
            ]].copy()
            display_overdue.columns = [
                "Tx ID", "Book Title", "Member", "Role", "Due Date", "Days Late", "Accrued Fine ($)"
            ]
            display_overdue["Accrued Fine ($)"] = display_overdue["Accrued Fine ($)"].apply(lambda x: f"${x:.2f}")
            st.dataframe(display_overdue, use_container_width=True, hide_index=True)
            st.warning("Go to **🚨 Overdue & Fine Tracker** or **🔄 Issue & Return** to process returns and collect fines.")

    with col_right:
        st.subheader("📈 Quick Inventory Metrics")
        if stats["total_copies"] > 0:
            borrowed_copies = stats["total_copies"] - stats["avail_copies"]
            inv_df = pd.DataFrame({
                "Category": ["Available", "Issued Out"],
                "Count": [stats["avail_copies"], borrowed_copies]
            }).set_index("Category")
            st.bar_chart(inv_df, color="#1f77b4")
        
        st.metric("💰 Total Fines Collected", f"${stats['fines_collected']:.2f}")

# ----------------- 2. BOOK MANAGEMENT -----------------
elif menu == "📖 Book Management":
    st.title("📖 Book Catalog Management")
    st.markdown("Add, search, inspect, and remove books from the library.")

    tab1, tab2, tab3 = st.tabs(["🔍 Search & Catalog", "➕ Add New Book", "🗑️ Delete Book"])

    with tab1:
        st.subheader("Search Book Inventory")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search_term = st.text_input("Enter search keywords", placeholder="Search by title, author, or ISBN...")
        with col_s2:
            filter_mode = st.selectbox("Search In", ["All", "Title", "Author"])

        books_df = db.search_books(search_term, filter_mode)
        st.caption(f"Found {len(books_df)} record(s)")

        if not books_df.empty:
            clean_df = books_df.rename(columns={
                "id": "Book ID",
                "title": "Title",
                "author": "Author",
                "isbn": "ISBN",
                "category": "Category",
                "total_copies": "Total Copies",
                "available_copies": "Available Copies"
            })
            st.dataframe(clean_df, use_container_width=True, hide_index=True)
        else:
            st.info("No matching books found.")

    with tab2:
        st.subheader("Register a New Book")
        with st.form("add_book_form", clear_on_submit=True):
            col_b1, col_b2 = st.columns(2)
            title = col_b1.text_input("Book Title *", placeholder="e.g. Clean Architecture")
            author = col_b2.text_input("Author Name *", placeholder="e.g. Robert C. Martin")

            col_b3, col_b4, col_b5 = st.columns([2, 2, 1])
            isbn = col_b3.text_input("ISBN *", placeholder="e.g. 978-0134494166")
            category = col_b4.selectbox("Category", [
                "General", "Computer Science", "Software Engineering", "Mathematics",
                "Physics", "Literature", "History", "Business", "Other"
            ])
            copies = col_b5.number_input("Copies *", min_value=1, max_value=200, value=3)

            submitted = st.form_submit_button("➕ Add Book to Catalog", type="primary")
            if submitted:
                if not title.strip() or not author.strip() or not isbn.strip():
                    st.error("Please provide Title, Author, and ISBN.")
                else:
                    success, message = db.add_book(title, author, isbn, copies, category)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

    with tab3:
        st.subheader("Delete a Book from Catalog")
        all_books = db.search_books()
        if all_books.empty:
            st.info("Catalog is empty.")
        else:
            book_opts = {
                f"ID #{r['id']} - {r['title']} by {r['author']} (Copies: {r['available_copies']}/{r['total_copies']})": r["id"]
                for _, r in all_books.iterrows()
            }
            selected_book_label = st.selectbox("Select Book to Remove", list(book_opts.keys()))
            selected_book_id = book_opts[selected_book_label]

            st.warning("⚠️ Deleting a book will remove it permanently. It cannot be deleted if any copy is currently issued.")
            if st.button("🗑️ Delete Selected Book", type="primary"):
                success, msg = db.delete_book(selected_book_id)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ----------------- 3. MEMBER REGISTRATION -----------------
elif menu == "👥 Member Registration":
    st.title("👥 Member Directory & Registration")
    st.markdown("Register students and teachers with automatic borrow limits enforced.")

    tab_m1, tab_m2 = st.tabs(["📋 View & Manage Members", "➕ Register New Member"])

    with tab_m1:
        members_df = db.get_members_with_stats()
        st.subheader(f"Registered Members ({len(members_df)})")

        if not members_df.empty:
            styled_m = members_df.rename(columns={
                "id": "Member ID",
                "name": "Full Name",
                "email": "Email",
                "phone": "Phone",
                "member_type": "Role",
                "join_date": "Joined On",
                "borrow_limit": "Borrow Limit",
                "current_borrowed": "Current Loans"
            })
            st.dataframe(styled_m, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Remove a Member")
            del_opts = {
                f"ID #{r['id']}: {r['name']} ({r['member_type']}) - {r['email']} [Active Loans: {r['current_borrowed']}]": r["id"]
                for _, r in members_df.iterrows()
            }
            sel_del_label = st.selectbox("Select Member to Delete", list(del_opts.keys()))
            if st.button("Delete Member", type="secondary"):
                success, msg = db.delete_member(del_opts[sel_del_label])
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info("No members registered yet.")

    with tab_m2:
        st.subheader("Register a Student or Teacher")
        with st.form("reg_member_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            name = col_m1.text_input("Full Name *", placeholder="e.g. John Doe")
            email = col_m2.text_input("Email Address *", placeholder="e.g. john.doe@university.edu")

            col_m3, col_m4 = st.columns(2)
            phone = col_m3.text_input("Phone Number", placeholder="e.g. +1-555-0199")
            member_type = col_m4.selectbox("Member Role *", ["Student", "Teacher"])

            limit = db.BORROW_LIMITS[member_type]
            st.caption(f"📌 Policy Notice: **{member_type}s** have a maximum borrow quota of **{limit} books** simultaneously.")

            btn_reg = st.form_submit_button("Register Member", type="primary")
            if btn_reg:
                if not name.strip() or not email.strip():
                    st.error("Name and Email are required.")
                else:
                    success, msg = db.register_member(name, email, member_type, phone)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

# ----------------- 4. ISSUE & RETURN -----------------
elif menu == "🔄 Issue & Return":
    st.title("🔄 Book Issue & Return Circulation")

    tab_issue, tab_return = st.tabs(["📤 Issue Book to Member", "📥 Return Book & Calculate Fine"])

    with tab_issue:
        st.subheader("Issue Book")
        # Load available books and members
        conn = db.get_connection()
        avail_books = pd.read_sql_query(
            "SELECT id, title, author, available_copies FROM books WHERE available_copies > 0 ORDER BY title ASC",
            conn
        )
        members = db.get_members_with_stats()
        conn.close()

        if avail_books.empty:
            st.warning("⚠️ No books are currently available in inventory. Please add new books or wait for returns.")
        elif members.empty:
            st.warning("⚠️ No members found. Please register members first.")
        else:
            book_dict = {
                f"#{r['id']} - {r['title']} (by {r['author']}) [{r['available_copies']} left]": r['id']
                for _, r in avail_books.iterrows()
            }
            member_dict = {
                f"#{r['id']} - {r['name']} ({r['member_type']}) [Borrowed: {r['current_borrowed']}/{r['borrow_limit']}]": (
                    r['id'], r['current_borrowed'], r['borrow_limit'], r['name'], r['member_type']
                )
                for _, r in members.iterrows()
            }

            with st.form("issue_form"):
                col_i1, col_i2 = st.columns(2)
                selected_book_str = col_i1.selectbox("Select Available Book *", list(book_dict.keys()))
                selected_member_str = col_i2.selectbox("Select Member *", list(member_dict.keys()))

                col_i3, col_i4 = st.columns(2)
                issue_date_val = col_i3.date_input("Issue Date", value=date.today())
                loan_duration = col_i4.number_input(
                    "Loan Period (Days)", min_value=1, max_value=90, value=db.DEFAULT_LOAN_DAYS
                )

                expected_due = issue_date_val + timedelta(days=int(loan_duration))
                st.info(f"📅 Due Date for this loan will be: **{expected_due.isoformat()}**")

                submit_issue = st.form_submit_button("📤 Confirm Book Issue", type="primary")
                if submit_issue:
                    b_id = book_dict[selected_book_str]
                    m_id, cur_b, m_lim, m_name, m_type = member_dict[selected_member_str]

                    if cur_b >= m_lim:
                        st.error(f"❌ Cannot issue: {m_name} ({m_type}) has reached their quota of {m_lim} books!")
                    else:
                        success, msg = db.issue_book(b_id, m_id, issue_date_val, int(loan_duration))
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)

    with tab_return:
        st.subheader("Return Book & Calculate Fine")
        active_loans = db.get_active_loans()

        if active_loans.empty:
            st.info("✅ All books are currently accounted for on the shelves. No active loans!")
        else:
            tx_dict = {
                f"Tx #{r['tx_id']} | '{r['book_title']}' borrowed by {r['member_name']} (Due: {r['due_date']})": (
                    r['tx_id'], r['due_date'], r['book_title'], r['member_name']
                )
                for _, r in active_loans.iterrows()
            }

            selected_tx_str = st.selectbox("Select Active Borrow Transaction *", list(tx_dict.keys()))
            tx_id, due_str, b_title, m_name = tx_dict[selected_tx_str]

            col_r1, col_r2 = st.columns(2)
            return_date_val = col_r1.date_input("Return Date", value=date.today())
            fine_rate = col_r2.number_input("Fine Rate per Late Day ($)", min_value=0.0, value=db.DEFAULT_FINE_PER_DAY, step=0.5)

            # Live preview of calculation
            days_late, calculated_fine = db.calculate_fine(due_str, return_date_val, fine_rate)

            if calculated_fine > 0:
                st.error(
                    f"⚠️ **OVERDUE!** The book is **{days_late} day(s)** late (Due: {due_str}).\n\n"
                    f"**Fine to Collect: ${calculated_fine:.2f}**"
                )
            else:
                st.success(f"✅ On time! (Due: {due_str}). No fine due.")

            if st.button("📥 Process Book Return & Update Stock", type="primary"):
                success, msg = db.return_book(tx_id, return_date_val, fine_rate)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ----------------- 5. OVERDUE & FINE TRACKER -----------------
elif menu == "🚨 Overdue & Fine Tracker":
    st.title("🚨 Overdue Books & Fine Management")
    st.markdown("Monitor overdue loans, see days elapsed, and inspect accumulated penalty fines.")

    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        ref_date = st.date_input("Calculation As-Of Date", value=date.today(), help="Test or view fines for past or future dates")
    with col_t2:
        fine_rate = st.number_input("Fine Rate per Day ($)", value=db.DEFAULT_FINE_PER_DAY, min_value=0.0, step=0.25)

    overdue_df = db.get_overdue_books(ref_date, fine_rate)

    if overdue_df.empty:
        st.success(f"🎉 No overdue books as of {ref_date.isoformat()}!")
    else:
        st.warning(f"Found **{len(overdue_df)}** overdue loan(s) as of {ref_date.isoformat()}.")

        total_pending_fine = overdue_df["accrued_fine"].sum()
        st.metric("Total Pending Fines", f"${total_pending_fine:.2f}")

        clean_overdue = overdue_df.rename(columns={
            "tx_id": "Tx ID",
            "book_title": "Book Title",
            "member_name": "Member Name",
            "member_type": "Role",
            "email": "Email",
            "issue_date": "Issued On",
            "due_date": "Due Date",
            "days_overdue": "Days Overdue",
            "accrued_fine": "Accrued Fine ($)"
        })
        clean_overdue["Accrued Fine ($)"] = clean_overdue["Accrued Fine ($)"].apply(lambda x: f"${x:.2f}")

        st.dataframe(clean_overdue, use_container_width=True, hide_index=True)

        # Quick Return Section from Overdue Tab
        st.markdown("---")
        st.subheader("⚡ Quick Return an Overdue Book")
        quick_tx_opts = {
            f"Tx #{r['tx_id']}: '{r['book_title']}' - {r['member_name']} ({r['days_overdue']} days late - Fine: ${r['accrued_fine']:.2f})": r['tx_id']
            for _, r in overdue_df.iterrows()
        }
        selected_quick_tx = st.selectbox("Select Overdue Loan to Process Return", list(quick_tx_opts.keys()))
        if st.button("Complete Return & Record Fine", type="primary"):
            success, msg = db.return_book(quick_tx_opts[selected_quick_tx], ref_date, fine_rate)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ----------------- 6. TRANSACTION HISTORY -----------------
elif menu == "📜 Transaction History":
    st.title("📜 Circulation Audit & Transaction History")
    st.markdown("Complete audit trail of all book issues, returns, and fines collected.")

    status_filter = st.selectbox("Filter by Status", ["All Transactions", "Currently Issued", "Returned"])

    tx_df = db.get_all_transactions()

    if status_filter == "Currently Issued":
        filtered_df = tx_df[tx_df["status"] == "Issued"]
    elif status_filter == "Returned":
        filtered_df = tx_df[tx_df["status"] == "Returned"]
    else:
        filtered_df = tx_df

    st.caption(f"Displaying {len(filtered_df)} transaction(s)")

    if not filtered_df.empty:
        display_tx = filtered_df.rename(columns={
            "tx_id": "Tx ID",
            "book_title": "Book Title",
            "member_name": "Member Name",
            "member_type": "Role",
            "issue_date": "Issue Date",
            "due_date": "Due Date",
            "return_date": "Return Date",
            "fine": "Fine ($)",
            "status": "Status"
        })
        display_tx["Fine ($)"] = display_tx["Fine ($)"].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "$0.00")
        st.dataframe(display_tx, use_container_width=True, hide_index=True)

        # CSV Export
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Transactions as CSV",
            data=csv_data,
            file_name=f"library_transactions_{date.today().isoformat()}.csv",
            mime="text/csv"
        )
    else:
        st.info("No transaction records found matching the filter.")

# ----------------- 7. SETTINGS & DEMO DATA -----------------
elif menu == "⚙️ Database & Seed Settings":
    st.title("⚙️ System Settings & Data Management")
    st.markdown("Manage sample demo data, database reset, and review configuration.")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🌱 Demo Seed Data")
        st.write("Populate the database with pre-configured books, student/teacher accounts, and sample overdue loans for quick demonstration.")
        if st.button("Load Demo Sample Data", type="primary"):
            success, msg = db.seed_sample_data()
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.info(msg)

    with c2:
        st.subheader("🧹 Reset Database")
        st.write("Wipes all tables and re-creates a clean database.")
        if st.button("Reset Entire Database", type="secondary"):
            import os
            conn = db.get_connection()
            conn.close()
            if os.path.exists(db.DB_PATH):
                os.remove(db.DB_PATH)
            db.init_db()
            st.success("Database has been reset completely.")
            st.rerun()
