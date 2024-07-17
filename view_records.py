import sqlite3
import os
from prettytable import PrettyTable

def show_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def describe_table(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    return columns

def show_all_records(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    records = cursor.fetchall()
    return records

def show_selected_records(conn, table_name, column_name, value):
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name} WHERE LOWER({column_name}) = LOWER(?)"
    cursor.execute(query, (value,))
    records = cursor.fetchall()
    return records

def print_table(column_names, rows):
    table = PrettyTable()
    table.field_names = column_names
    for row in rows:
        table.add_row(row)
    print(table)

def main():
    db_path = 'D:/angularflask472/Cloned-Projects/flask-merges-changes/instance/test.db'

    # Check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return

    # Connect to the SQLite database
    try:
        conn = sqlite3.connect(db_path)
        print(f"Connected to database: {db_path}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    while True:
        # Show available tables
        tables = show_tables(conn)
        if not tables:
            print("No tables found in the database.")
            return

        print("Available tables:")
        for i, table in enumerate(tables):
            print(f"{i + 1}. {table}")

        # Ask user to select a table
        try:
            table_index = int(input("Select a table by number: ")) - 1
            if table_index < 0 or table_index >= len(tables):
                print("Invalid table selection.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        selected_table = tables[table_index]

        # Ask user if they want to see the table description, all records, or selected records
        view_option = input("Do you want to see (d)escription, (a)ll records, or (s)elected records? (d/a/s): ").strip().lower()

        if view_option == 'd':
            # Display table description
            columns = describe_table(conn, selected_table)
            if not columns:
                print(f"No description found for table {selected_table}.")
            else:
                print(f"Description for table {selected_table}:")
                print_table(['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'], columns)
        elif view_option == 'a':
            # Display all records
            records = show_all_records(conn, selected_table)
            if not records:
                print(f"No records found in table {selected_table}.")
            else:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({selected_table});")
                columns = [column[1] for column in cursor.fetchall()]
                print_table(columns, records)
        elif view_option == 's':
            # Ask for column name and value to filter records
            column_name = input("Enter the column name to filter by: ").strip()
            value = input(f"Enter the value for {column_name}: ").strip()

            # Display selected records
            records = show_selected_records(conn, selected_table, column_name, value)
            if not records:
                print(f"No records found in table {selected_table} with {column_name} = {value}.")
            else:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({selected_table});")
                columns = [column[1] for column in cursor.fetchall()]
                print_table(columns, records)
        else:
            print("Invalid option selected.")

        # Ask user if they want to continue or exit
        continue_option = input("Do you want to continue? (y/n): ").strip().lower()
        if continue_option != 'y':
            print("Exiting...")
            break

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
