from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import re
import os

# -------------------- Конфигурация приложения --------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Замени на свой секретный ключ! Очень важно!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance', 'users.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Отключаем warnings от SQLAlchemy

# Конфигурация для загрузки файлов
UPLOAD_FOLDER = 'static/news_img/'  # Папка для хранения загруженных изображений
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Разрешенные расширения файлов

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Максимальный размер файла (16MB)

# Создаем папку для загрузок, если она не существует
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# -------------------- Настройка Flask-Login --------------------

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Функция для входа
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
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# -------------------- Функции --------------------

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\-]+', '', text)
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------- Маршруты (Routes) --------------------

# --- Index, About, Contact ---
@app.route('/')
def index():
    news_list = News.query.filter(News.is_published == True).order_by(News.date_created.desc()).limit(3).all() # Отображать последние 3 новости
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
            return redirect(url_for('admin_panel' if current_user.is_admin else 'index'))  # Redirect to admin panel if admin
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

        image = request.files['image']  # Get the image file from the request
        filename = None

        if image and image.filename != '' and allowed_file(image.filename):
            filename = secure_filename(image.filename)  # Make the filename safe
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) # Save the image

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
            # Delete old file
            if news_item.image:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], news_item.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            news_item.image = filename  # Store the filename in the database

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

# -------------------- Маршруты для существующего функционала --------------------

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

@app.route('/subscribe', methods=['POST'])
def subscribe():
    from db.emails_create import create_connection as create_email_connection, add_email
    conn = create_email_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500

    email = request.form.get('email')

    if not re.match(EMAIL_REGEX, email):
        conn.close()
        return jsonify({"error": "Неверный формат email"}), 400

    success = add_email(conn, email)
    conn.close()

    if success:
        return jsonify({"message": "Успешная подписка"}), 200
    return jsonify({"error": "Email уже существует"}), 409

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    from db.feedbacks_create import create_connection as create_feedback_connection, add_feedback
    conn = create_feedback_connection()
    if not conn:
        return jsonify({"error": "Database error"}), 500

    data = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'message': request.form.get('message')
    }

    if not data['message'] or len(data['message']) < 10:
        conn.close()
        return jsonify({"error": "Сообщение должно содержать минимум 10 символов"}), 400

    success = add_feedback(conn, data)
    conn.close()

    if success:
        return jsonify({"message": "Фидбек успешно отправлен"}), 200
    return jsonify({"error": "Ошибка сохранения"}), 500

# -------------------- Обработчики ошибок --------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# -------------------- Запуск приложения --------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)