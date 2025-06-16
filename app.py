from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    c.execute('''
        SELECT
            inventory.id,
            items.name,
            items.category,
            inventory.quantity
        FROM inventory
        JOIN items ON inventory.item_id = items.id
    ''')
    items = c.fetchall()  # → list of tuples
    print("==========")
    print(items)
    conn.close()
    return render_template('index.html', items=items)

if __name__ == '__main__':
    app.run(debug=True)
