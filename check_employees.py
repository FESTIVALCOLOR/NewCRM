import sqlite3

conn = sqlite3.connect('interior_studio.db')
c = conn.cursor()
c.execute('SELECT id, full_name, login FROM employees WHERE login != "admin"')
for row in c.fetchall():
    print(f'ID={row[0]}, Name={row[1]}, Login={row[2]}')
conn.close()
