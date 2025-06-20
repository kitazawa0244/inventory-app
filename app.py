from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps



app = Flask(__name__)
app.secret_key = 'gFks@pLq93df!!Jdks09akLPiWz'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return 'アクセス権限がありません🙅‍♂️'
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def insert_log(user_id, action, item_id, item_name, category, quantity, note=""):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''
        INSERT INTO log_inventory (
            timestamp, user_id, action, item_id, item_name, category, quantity, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, user_id, action, item_id, item_name, category, quantity, note))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')  # ← ログインしてなければリダイレクト

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
        WHERE items.delete_flag = 0      
    ''')
    items = c.fetchall()  # → list of tuples
    
    conn.close()
    return render_template('index.html', items=items)

# ★ 追加：商品登録フォームの表示
@app.route('/add')
@login_required
@admin_required
def add():
    return render_template('add.html')


# ★ 追加：フォームから商品を追加（POST）
@app.route('/add', methods=['POST'])
@login_required
@admin_required
def add_post():
    name = request.form['name']
    category = request.form['category']
    quantity = int(request.form['quantity'])

    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 同じ商品名＋カテゴリがあるか確認
    c.execute('SELECT id FROM items WHERE name = ? AND category = ?', (name, category))
    item = c.fetchone()

    if item:
        # 既存商品があれば在庫を加算
        item_id = item[0]
        c.execute('SELECT quantity FROM inventory WHERE item_id = ?', (item_id,))
        current_quantity = c.fetchone()[0]
        new_quantity = current_quantity + quantity
        c.execute('UPDATE inventory SET quantity = ? WHERE item_id = ?', (new_quantity, item_id))
    else:
        # なければ新規登録
        c.execute('INSERT INTO items (name, category) VALUES (?, ?)', (name, category))
        item_id = c.lastrowid
        c.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))

    conn.commit()
    conn.close()

    insert_log(
        user_id=session.get('user_id'),
        action='add',
        item_id=item_id,
        item_name=name,
        category=category,
        quantity=quantity,
        note='新規登録' if not item else '在庫加算'
    )
    return redirect('/')


@app.route('/update/<int:item_id>/<string:action>')
@login_required
@admin_required
def update_quantity(item_id, action):
    
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # 在庫数取得
    c.execute('SELECT quantity FROM inventory WHERE id = ?', (item_id,))
    row = c.fetchone()

    if row is None:
        conn.close()
        return redirect('/')

    quantity = row[0]

    # 数量更新
    if action == 'increase':
        quantity += 1
    elif action == 'decrease' and quantity > 0:
        quantity -= 1

    c.execute('UPDATE inventory SET quantity = ? WHERE id = ?', (quantity, item_id))

    # 🔍 商品情報をここで取得（items.id, name, category）
    c.execute('''
        SELECT items.id, items.name, items.category 
        FROM inventory 
        JOIN items ON inventory.item_id = items.id 
        WHERE inventory.id = ?
    ''', (item_id,))
    item_info = c.fetchone()

    conn.commit()
    conn.close()

    # ✅ ログ記録（← item_info を使ってログ）
    if item_info:
        insert_log(
            user_id=session.get('user_id'),
            action='increase' if action == 'increase' else 'decrease',
            item_id=item_info[0],
            item_name=item_info[1],
            category=item_info[2],
            quantity=1,
            note=''
        )

    return redirect('/')

# 追加：論理削除
@app.route('/delete/<int:item_id>')
@login_required
@admin_required
def delete_item(item_id):
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    # ✅ 商品情報を削除前に取得
    c.execute('SELECT name, category FROM items WHERE id = ?', (item_id,))
    item = c.fetchone()

    # 論理削除実行
    c.execute('UPDATE items SET delete_flag = 1 WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    # ✅ ログ記録（削除）
    if item:
        insert_log(
            user_id=session.get('user_id'),
            action='delete',
            item_id=item_id,
            item_name=item[0],
            category=item[1],
            quantity=0,
            note='論理削除'
        )

    return redirect('/')


@app.route('/log')
def view_log():
    if 'user_id' not in session:
        return redirect('/login')  # ← ログインしてなければリダイレクト
    conn = sqlite3.connect('inventory.db')
    c = conn.cursor()

    c.execute('''
        SELECT 
            log_inventory.timestamp,
            users.name,
            log_inventory.action,
            log_inventory.item_name,
            log_inventory.category,
            log_inventory.quantity,
            log_inventory.note
        FROM log_inventory
        JOIN users ON log_inventory.user_id = users.id
        ORDER BY log_inventory.timestamp DESC
    ''')

    logs = c.fetchall()
    conn.close()
    return render_template('log.html', logs=logs)


from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' not in session:
        return redirect('/login')  # ← ログインしてなければリダイレクト
    if request.method == 'POST':
        name = request.form['name'].strip()
        password = request.form['password'].strip()

        # パスワードをハッシュ化
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('inventory.db')
        c = conn.cursor()

        # 重複チェック（おすすめ）
        c.execute('SELECT id FROM users WHERE name = ?', (name,))
        if c.fetchone():
            conn.close()
            return 'このユーザー名はすでに使われています！'

        c.execute('INSERT INTO users (name, password) VALUES (?, ?)', (name, hashed_password))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name'].strip()
        password = request.form['password'].strip()

        conn = sqlite3.connect('inventory.db')
        try:
            c = conn.cursor()
            c.execute('SELECT id, name, password,role FROM users WHERE name = ?', (name,))
            user = c.fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[3]  # ← role をセッションに追加
            return redirect('/')
        else:
            return 'ログイン失敗〜！ユーザー名かパスワードがちがうっぽい！'

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # ログイン情報を消す
    return redirect('/login')  # ← ログアウト後にログイン画面へ飛ばす✨


if __name__ == '__main__':
      app.run(debug=True, threaded=False)


