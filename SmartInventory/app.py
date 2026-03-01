import streamlit as st
import sqlite3
import pandas as pd

# ---------- CUSTOM BACKGROUND ----------
st.markdown(
    """
    <style>
    /* App background */
    .stApp {
        background: linear-gradient(135deg, #f0f2f6 0%, #d6e4ff 100%);
        color: #000000;
    }
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #c8defc;
    }
    /* Table scroll background */
    .css-1lcbmhc {
        background-color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Smart Inventory", layout="wide")

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    quantity INTEGER,
    price REAL
)
""")
conn.commit()

# ---------- SESSION STATE ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "refresh" not in st.session_state:
    st.session_state.refresh = False

# ---------- USERS ----------
users = {
    "admin": {"password": "1234", "role": "admin"},
    "staff": {"password": "staff123", "role": "staff"}
}

# ---------- LOGIN ----------
st.sidebar.header("Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if username in users and password == users[username]["password"]:
        st.session_state.logged_in = True
        st.session_state.role = users[username]["role"]
        st.session_state.refresh = True
        st.sidebar.success(f"Login successful! Role: {st.session_state.role.capitalize()}")
    else:
        st.sidebar.error("Invalid credentials")
        st.session_state.logged_in = False

if st.session_state.logged_in:
    st.title("🗄 Smart Inventory / Catalog Management")
    st.write(f"**Logged in as:** {st.session_state.role.capitalize()}")

    # ---------- FETCH INVENTORY ----------
    if st.session_state.refresh:
        st.session_state.refresh = False
    df = pd.read_sql_query("SELECT * FROM items", conn)
    filtered_df = df.copy()

    # ---------- SEARCH / FILTER ----------
    st.header("Search / Filter Items")
    search_name = st.text_input("Search by Name")
    search_category = st.text_input("Search by Category")
    if search_name.strip() != "":
        filtered_df = filtered_df[filtered_df['name'].str.contains(search_name, case=False)]
    if search_category.strip() != "":
        filtered_df = filtered_df[filtered_df['category'].str.contains(search_category, case=False)]

    # ---------- TABS ----------
    tab1, tab2, tab3 = st.tabs(["🗄 Inventory", "📊 Analytics", "💾 Export"])

    # ---------- TAB 1: Inventory ----------
    with tab1:
        # Metrics cards
        total_items = cursor.execute("SELECT SUM(quantity) FROM items").fetchone()[0] or 0
        low_stock_count = cursor.execute("SELECT COUNT(*) FROM items WHERE quantity <5").fetchone()[0]
        max_capacity = 500

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Items", total_items)
        col2.metric("Low Stock Items", low_stock_count)
        col3.metric("Remaining Capacity", max_capacity - total_items)

        # Admin-only: Add / Update
        if st.session_state.role == "admin":
            st.subheader("Add New Item")
            with st.form("add_item_form", clear_on_submit=True):
                name = st.text_input("Item Name")
                category = st.text_input("Category")
                quantity = st.number_input("Quantity", min_value=0, step=1)
                price = st.number_input("Price", min_value=0.0, step=0.01)
                submit = st.form_submit_button("Add Item")
                if submit:
                    if name.strip() != "":
                        cursor.execute(
                            "INSERT INTO items (name, category, quantity, price) VALUES (?, ?, ?, ?)",
                            (name, category, quantity, price)
                        )
                        conn.commit()
                        st.success(f"Item '{name}' added successfully!")
                        st.session_state.refresh = True
                    else:
                        st.error("Item name cannot be empty.")

            st.subheader("Update Item Quantity")
            if len(df) > 0:
                item_list = [f"{row['id']} - {row['name']}" for index, row in df.iterrows()]
                selected_item = st.selectbox("Select Item to Update", item_list)
                new_qty = st.number_input("New Quantity", min_value=0, step=1)
                if st.button("Update Quantity"):
                    item_id = int(selected_item.split(" - ")[0])
                    cursor.execute("UPDATE items SET quantity=? WHERE id=?", (new_qty, item_id))
                    conn.commit()
                    st.success("Quantity updated successfully!")
                    st.session_state.refresh = True

        # Inventory Table + Low Stock chart side by side
        st.subheader("Inventory Catalog")
        col1, col2 = st.columns([2, 1])
        with col1:
            def highlight_low_stock(row):
                return ['background-color: yellow' if row['quantity'] < 5 else '' for _ in row]
            if len(filtered_df) > 0:
                st.dataframe(filtered_df.style.apply(highlight_low_stock, axis=1))
            else:
                st.info("No items match the search/filter criteria.")
        with col2:
            low_stock_df = df[df['quantity'] < 5]
            if len(low_stock_df) > 0:
                st.bar_chart(low_stock_df.set_index('name')['quantity'])
            else:
                st.write("No low stock items!")

    # ---------- TAB 2: Analytics ----------
    with tab2:
        st.subheader("Low Stock Analytics")
        if len(low_stock_df) > 0:
            st.bar_chart(low_stock_df.set_index('name')['quantity'])
        else:
            st.write("No low stock items!")
        st.write("Inventory Summary:")
        st.write(f"Total Items: {total_items}")
        st.write(f"Low Stock Items (<5): {low_stock_count}")
        st.write(f"Remaining Capacity: {max_capacity - total_items}")

    # ---------- TAB 3: Export ----------
    with tab3:
        if st.session_state.role == "admin":
            st.subheader("Export Inventory CSV")
            if len(df) > 0:
                st.download_button(
                    "Download Inventory CSV",
                    df.to_csv(index=False),
                    "inventory.csv"
                )
            else:
                st.write("No items to export yet.")
        else:
            st.write("Only admin can export inventory.")
