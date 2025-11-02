import sqlite3
import os
from tabulate import tabulate
from config import Config

def view_database():
    db_path = Config.DATABASE_PATH
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print(f"📊 Opening database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("📋 Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 60)
    
    # Show data from each table
    for table in tables:
        table_name = table[0]
        print(f"\n📁 Table: {table_name}")
        print("-" * 50)
        
        try:
            # Get table columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Get all data from table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                # Display data in table format
                print(f"Columns: {', '.join(column_names)}")
                print(f"Total rows: {len(rows)}")
                print()
                
                # Use tabulate for nice table formatting
                print(tabulate(rows, headers=column_names, tablefmt='grid', maxcolwidths=30))
            else:
                print("  (No data)")
                
        except Exception as e:
            print(f"  Error reading table: {e}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Database view complete!")

# Alternative version without external dependencies
def view_database_simple():
    db_path = Config.DATABASE_PATH
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print(f"📊 Opening database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("📋 Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 60)
    
    # Show data from each table
    for table in tables:
        table_name = table[0]
        print(f"\n📁 Table: {table_name}")
        print("-" * 50)
        
        try:
            # Get table columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Get all data from table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            if rows:
                print(f"Columns: {', '.join(column_names)}")
                print(f"Total rows: {len(rows)}")
                print()
                
                # Calculate column widths
                col_widths = []
                for i, col_name in enumerate(column_names):
                    max_width = len(str(col_name))
                    for row in rows:
                        max_width = max(max_width, len(str(row[i] if i < len(row) else '')))
                    col_widths.append(min(max_width + 2, 30))  # Limit max width
                
                # Print header
                header = ""
                for i, col_name in enumerate(column_names):
                    header += f"{str(col_name)[:col_widths[i]-2]:<{col_widths[i]}}"
                print(header)
                print("-" * sum(col_widths))
                
                # Print rows
                for row in rows:
                    row_str = ""
                    for i, cell in enumerate(row):
                        cell_str = str(cell) if cell is not None else "NULL"
                        row_str += f"{cell_str[:col_widths[i]-2]:<{col_widths[i]}}"
                    print(row_str)
                    
            else:
                print("  (No data)")
                
        except Exception as e:
            print(f"  Error reading table: {e}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Database view complete!")

# Enhanced version with more details
def view_database_detailed():
    db_path = Config.DATABASE_PATH
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print(f"📊 Opening database: {db_path}")
    print("=" * 70)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get database info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"📋 Total tables: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 70)
    
    # Show detailed info for each table
    for table in tables:
        table_name = table[0]
        print(f"\n📊 Table: {table_name}")
        print("=" * 50)
        
        try:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("🔍 Table Structure:")
            print("-" * 30)
            col_info = []
            for col in columns:
                col_id, name, type_, notnull, default_value, pk = col
                col_info.append([name, type_, "YES" if notnull else "NO", "PK" if pk else ""])
            
            # Print column info in table format
            if col_info:
                try:
                    from tabulate import tabulate
                    print(tabulate(col_info, headers=["Column", "Type", "Nullable", "Key"], tablefmt="simple"))
                except ImportError:
                    # Fallback without tabulate
                    print(f"{'Column':<15} {'Type':<10} {'Nullable':<8} {'Key':<5}")
                    print("-" * 40)
                    for info in col_info:
                        print(f"{info[0]:<15} {info[1]:<10} {info[2]:<8} {info[3]:<5}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            print(f"\n📈 Total rows: {row_count}")
            
            if row_count > 0:
                print(f"\n📄 Table Data (showing first 10 rows):")
                print("-" * 50)
                
                # Get sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
                rows = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # Display data
                try:
                    from tabulate import tabulate
                    print(tabulate(rows, headers=column_names, tablefmt='grid', maxcolwidths=25))
                except ImportError:
                    # Simple table formatting
                    col_widths = [min(max(len(str(name)), *[len(str(row[i])) for row in rows]), 25) + 2 
                                 for i, name in enumerate(column_names)]
                    
                    # Header
                    header = ""
                    for i, name in enumerate(column_names):
                        header += f"{str(name):<{col_widths[i]}}"
                    print(header)
                    print("-" * sum(col_widths))
                    
                    # Rows
                    for row in rows:
                        row_str = ""
                        for i, cell in enumerate(row):
                            cell_str = str(cell) if cell is not None else "NULL"
                            row_str += f"{cell_str:<{col_widths[i]}}"
                        print(row_str)
                
                if row_count > 10:
                    print(f"\n... and {row_count - 10} more rows")
                    
        except Exception as e:
            print(f"  ❌ Error reading table: {e}")
    
    # Show indexes
    print("\n" + "=" * 70)
    print("🔗 Database Indexes:")
    print("-" * 30)
    cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index';")
    indexes = cursor.fetchall()
    
    if indexes:
        for index in indexes:
            print(f"  - {index[0]} (on {index[1]})")
    else:
        print("  (No indexes)")
    
    conn.close()
    print("\n" + "=" * 70)
    print("✅ Database inspection complete!")

if __name__ == "__main__":
    # Try the detailed version first, fall back to simple if tabulate is not available
    try:
        import tabulate
        view_database_detailed()
    except ImportError:
        print("⚠️  'tabulate' package not installed. Using simple table format.")
        print("💡 Install with: pip install tabulate")
        print()
        view_database_simple()