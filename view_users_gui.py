import sqlite3                     # Import the sqlite3 module for database operations
import tkinter as tk               # Import tkinter for GUI
from tkinter import ttk            # Import ttk for themed widgets

# Connect to SQLite database
conn = sqlite3.connect('test.db')  # Establish a connection to the SQLite database file 'test.db'
cursor = conn.cursor()             # Create a cursor object to execute SQL commands

# Fetch all users
cursor.execute("SELECT id, username, name, email, phone, address FROM user")  # Execute SQL query to select user data
rows = cursor.fetchall()           # Fetch all rows from the executed query

# GUI Setup
root = tk.Tk()                     # Create the main application window
root.title("User Table Viewer")    # Set the window title

tree = ttk.Treeview(root)          # Create a Treeview widget for tabular data display
tree["columns"] = ("ID", "Username", "Name", "Email", "Phone", "Address")  # Define columns for the Treeview

tree.column("#0", width=0, stretch=tk.NO)         # Hide the first (implicit) column
tree.heading("#0", text="", anchor=tk.W)          # Set heading for the hidden column

for col in tree["columns"]:                       # Iterate over each column
    tree.column(col, anchor=tk.W, width=120)      # Set column alignment and width
    tree.heading(col, text=col, anchor=tk.W)      # Set column heading text and alignment

# Insert data into Treeview
for row in rows:                                  # Iterate over each row of user data
    tree.insert("", tk.END, values=row)           # Insert the row into the Treeview

tree.pack(fill=tk.BOTH, expand=True)              # Pack the Treeview widget to fill the window

root.geometry("750x400")                          # Set the window size
root.mainloop()                                   # Start the Tkinter event loop
