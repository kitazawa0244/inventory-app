from flask import Flask, render_template, request, redirect
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
    
    conn.close()
    return render_template('index.html', items=items)

# ★ 追加：商品登録フォームの表示
@app.route('/add')
def add():
    return render_template('add.html')

# ★ 追加：フォームから商品を追加（POST）
@app.route('/add', methods=['POST'])
def add_post():
    name = request.form['name']
    category = request.form['category']
    quantity = int(request.form['quantity'])

    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # itemsテーブルに商品を追加
    c.execute('INSERT INTO items (name, category) VALUES (?, ?)', (name, category))
    item_id = c.lastrowid  # 最後に追加された商品のIDを取得

    # inventoryテーブルに在庫数を登録
    c.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))
    
    conn.commit()
    conn.close()
    return redirect('/')

#追加：在庫数を直接編集
@app.route('/update/<int:item_id>/<string:action>')
def update_quantity(item_id, action):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    c.execute('SELECT quantity FROM inventory WHERE id = ?', (item_id,))
    row = c.fetchone()

    if row is None:
        conn.close()
        return redirect('/')

    quantity = row[0]

    if action == 'increase':
        quantity += 1
    elif action == 'decrease' and quantity > 0:
        quantity -= 1

    c.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (quantity, item_id))
    conn.commit()
    conn.close()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
