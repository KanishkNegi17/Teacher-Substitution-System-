import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime


conn = sqlite3.connect("teachers.db", check_same_thread=False)
cursor = conn.cursor()


cursor.execute('''CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS timetable (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER,
                    day TEXT,
                    period INTEGER,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS absentees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER,
                    date TEXT,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id))''')

conn.commit()


def get_available_teachers(day, period):
    absent_teachers = [row[0] for row in cursor.execute("SELECT teacher_id FROM absentees WHERE date = ?", (datetime.today().strftime('%Y-%m-%d'),)).fetchall()]
    busy_teachers = [row[0] for row in cursor.execute("SELECT teacher_id FROM timetable WHERE day = ? AND period = ?", (day, period)).fetchall()]
    available_teachers = cursor.execute("SELECT id, name FROM teachers WHERE id NOT IN ({})".format(
        ','.join('?'*len(absent_teachers + busy_teachers))), tuple(absent_teachers + busy_teachers)).fetchall()
    return available_teachers

st.title("Teacher Substitution System")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ""
    st.session_state.user_id = None

if not st.session_state.logged_in:
    menu = st.sidebar.selectbox("Menu", ["Login", "Register Teacher"])
    
    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = cursor.execute("SELECT id, role FROM teachers WHERE username = ? AND password = ?", (username, password)).fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.user_role = user[1]
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    
    elif menu == "Register Teacher":
        name = st.text_input("Teacher Name")
        dept = st.text_input("Department")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Teacher", "HOD"])
        if st.button("Register"):
            cursor.execute("INSERT INTO teachers (name, department, username, password, role) VALUES (?, ?, ?, ?, ?)", (name, dept, username, password, role))
            conn.commit()
            st.success("Teacher Registered Successfully!")
else:
    menu_options = ["Mark Absent/Present", "Manage Own Timetable", "Logout"]
    if st.session_state.user_role == "HOD":
        menu_options.extend(["View Timetable", "Find Substitute","All Teachers","Absentees"])
    menu = st.sidebar.selectbox("Menu", menu_options)
    
    if menu == "Mark Absent/Present":
        today = datetime.today().strftime('%Y-%m-%d')
        is_absent = cursor.execute("SELECT id FROM absentees WHERE teacher_id = ? AND date = ?", (st.session_state.user_id, today)).fetchone()
        if is_absent:
            if st.button("Mark Present"):
                cursor.execute("DELETE FROM absentees WHERE teacher_id = ? AND date = ?", (st.session_state.user_id, today))
                conn.commit()
                st.success("Marked Present!")
        else:
            if st.button("Mark Absent"):
                cursor.execute("INSERT INTO absentees (teacher_id, date) VALUES (?, ?)", (st.session_state.user_id, today))
                conn.commit()
                st.success("Marked Absent!")

    elif menu == "Manage Own Timetable":
        day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
        period = st.number_input("Enter Period Number", min_value=1, max_value=8, step=1)
        if st.button("Add Period"):
            cursor.execute("INSERT INTO timetable (teacher_id, day, period) VALUES (?, ?, ?)", (st.session_state.user_id, day, period))
            conn.commit()
            st.success("Period Added Successfully!")
    
    elif menu == "View Timetable" and st.session_state.user_role == "HOD":
        timetable = pd.read_sql_query("SELECT teachers.name, timetable.day, timetable.period FROM timetable JOIN teachers ON timetable.teacher_id = teachers.id", conn)
        st.dataframe(timetable)
    elif menu == "All Teachers" and st.session_state.user_role == "HOD":
         al = pd.read_sql_query("SELECT name,department from teachers", conn)
         st.dataframe(al)
    elif menu == "Absentees" and st.session_state.user_role == "HOD":
         ab = pd.read_sql_query("SELECT teachers.name, teachers.department from teachers JOIN absentees ON teachers.id = absentees.id", conn)
         st.dataframe(ab)
    
    elif menu == "Find Substitute" and st.session_state.user_role == "HOD":
        day = st.selectbox("Select Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
        period = st.number_input("Enter Period Number", min_value=1, max_value=8, step=1)
        if st.button("Find Substitute"):
            available_teachers = get_available_teachers(day, period)
            if available_teachers:
                st.success("Available Teachers:")
                for tid, tname in available_teachers:
                    st.write(f"✅ {tname}")
            else:
                st.error("No available teachers for this period!")
    
    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.user_role = ""
        st.session_state.user_id = None
        st.rerun()

conn.close()
