import sqlite3

conn = sqlite3.connect('meridian.db')
cursor = conn.cursor()

results = cursor.execute('''
    SELECT * FROM Customers
''')
print(results.fetchall())
cursor.close()