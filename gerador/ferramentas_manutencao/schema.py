import sqlite3
c = sqlite3.connect('database.db').cursor()
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cadastros';")
res = c.fetchone()
print(res[0] if res else 'Table not found')
