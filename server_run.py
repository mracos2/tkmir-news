from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import re
import os
import sqlite3
from datetime import datetime

# -------------------- Конфигурация приложения --------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance', 'users.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Конфигурация для загрузки файлов
UPLOAD_FOLDER = 'static/news_img/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
db = SQLAlchemy(app)

# -------------------- Настройка Flask-Login --------------------

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Требуется авторизация для доступа к этой странице."
login_manager.login_message_category = "info"

# -------------------- Модели данных --------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.username}>'

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.now())
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('news', lazy=True))
    slug = db.Column(db.String(255), unique=True, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    image = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<News {self.title}>'

# -------------------- Функции Flask-Login --------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- Декораторы --------------------

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# -------------------- Вспомогательные функции --------------------

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\-]+', '', text)
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_path(filename):
    """Возвращает абсолютный путь к файлу базы данных"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

def fetch_from_db(db_path, table_name, columns):
    """Универсальная функция для получения данных из SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"Table '{table_name}' not found in database")
            return []
        
        # Получаем данные
        column_str = ", ".join(columns)
        cursor.execute(f"SELECT {column_str} FROM {table_name}")
        rows = cursor.fetchall()
        
        # Форматируем результат
        return [dict(zip(columns, row)) for row in rows]
    
    except sqlite3.Error as e:
        print(f"Database error ({table_name}): {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_emails_from_db():
    db_path = get_db_path('emails.db')
    print(f"Accessing emails database at: {db_path}")  # Для отладки
    return fetch_from_db(db_path, "emails", ["id", "email", "created_at"])

def get_feedbacks_from_db():
    db_path = get_db_path('feedbacks.db')
    print(f"Accessing feedbacks database at: {db_path}")  # Для отладки
    return fetch_from_db(db_path, "feedbacks", ["id", "created_at", "name", "email", "phone", "message"])

# -------------------- Маршруты (Routes) --------------------

@app.route('/')
def index():
    news_list = News.query.filter(News.is_published == True).order_by(News.date_created.desc()).limit(3).all()
    return render_template('index.html', news=news_list)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- Authentication routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('admin_panel' if current_user.is_admin else 'index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Имя пользователя уже занято.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Вы успешно зарегистрировались! Теперь войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# --- News routes ---
@app.route('/news')
def news():
    news_list = News.query.filter(News.is_published == True).all()
    return render_template('news.html', news=news_list)

@app.route('/news/<slug>')
def view_news(slug):
    news_item = News.query.filter_by(slug=slug, is_published=True).first_or_404()
    return render_template('view_news.html', news_item=news_item)

# --- Admin routes ---
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    news_list = News.query.order_by(News.date_created.desc()).all()
    return render_template('admin_panel.html', news=news_list)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        is_published = 'is_published' in request.form
        slug = slugify(title)

        image = request.files['image']
        filename = None

        if image and image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_news = News(title=title, content=content, author=current_user, slug=slug, is_published=is_published, image=filename)
        db.session.add(new_news)
        db.session.commit()
        flash('Новость успешно добавлена!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('add_news.html')

@app.route('/admin/news/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(id):
    news_item = News.query.get_or_404(id)

    if request.method == 'POST':
        news_item.title = request.form['title']
        news_item.content = request.form['content']
        news_item.is_published = 'is_published' in request.form
        news_item.slug = slugify(news_item.title)

        image = request.files['image']
        if image and image.filename != '' and allowed_file(image.filename):
            if news_item.image:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], news_item.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            news_item.image = filename

        db.session.commit()
        flash('Новость успешно обновлена!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('edit_news.html', news_item=news_item)

@app.route('/admin/news/delete/<int:id>')
@login_required
@admin_required
def delete_news(id):
    news_item = News.query.get_or_404(id)
    db.session.delete(news_item)
    db.session.commit()
    flash('Новость успешно удалена!', 'success')
    return redirect(url_for('admin_panel'))

# --- API endpoints ---
@app.route('/admin/emails')
@login_required
@admin_required
def admin_emails():
    return render_template('emails.html')

@app.route('/admin/feedbacks')
@login_required
@admin_required
def admin_feedbacks():
    return render_template('feedbacks.html')

@app.route('/api/emails')
@login_required
@admin_required
def api_emails():
    emails = get_emails_from_db()
    return jsonify(emails)

@app.route('/api/feedbacks')
@login_required
@admin_required
def api_feedbacks():
    feedbacks = get_feedbacks_from_db()
    return jsonify(feedbacks)

@app.route('/admin/feedbacks/data')
@login_required
@admin_required
def admin_feedbacks_data():
    feedbacks = get_feedbacks_from_db()
    return jsonify(feedbacks)

@app.route('/admin/emails/data')
@login_required
@admin_required
def admin_emails_data():
    emails = get_emails_from_db()
    return jsonify(emails)

# -------------------- Обработчики форм --------------------

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')

    if not re.match(EMAIL_REGEX, email):
        return jsonify({"error": "Неверный формат email"}), 400

    try:
        db_path = get_db_path('emails.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Проверяем существование email
        cursor.execute("SELECT id FROM emails WHERE email=?", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Email уже существует"}), 409

        # Добавляем email
        cursor.execute("INSERT INTO emails (email) VALUES (?)", (email,))
        conn.commit()
        return jsonify({"message": "Успешная подписка"}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'message': request.form.get('message')
    }

    if not data['message'] or len(data['message']) < 10:
        return jsonify({"error": "Сообщение должно содержать минимум 10 символов"}), 400

    try:
        db_path = get_db_path('feedbacks.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем существование таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedbacks'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    message TEXT NOT NULL
                )
            """)

        # Добавляем feedback
        cursor.execute("""
            INSERT INTO feedbacks (name, email, phone, message)
            VALUES (?, ?, ?, ?)
        """, (data['name'], data['email'], data['phone'], data['message']))
        
        conn.commit()
        return jsonify({"message": "Фидбек успешно отправлен"}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# -------------------- Обработчики ошибок --------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/clear_flashes", methods=["POST"])
def clear_flashes():
    session.pop("_flashes", None)
    return "", 204

# -------------------- Запуск приложения --------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создаем тестового администратора, если его нет
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin', method='pbkdf2:sha256'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Создан тестовый администратор: admin/admin")
    
    app.run(debug=True)