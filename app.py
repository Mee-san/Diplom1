from flask import Flask, render_template, request, redirect, url_for, session, flash, current_app, Response
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_session import Session
import sqlite3
import os
import shutil
from sqlalchemy.orm import joinedload
from sqlalchemy import ForeignKey, or_
from sqlalchemy.orm import relationship
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import uuid
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'smort'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)
print("Attempting to create SQLAlchemy database object")
db = SQLAlchemy(app)
migrate = Migrate(app, db)


UPLOAD_FOLDER = 'static/avatars'
allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'jfif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    avatar = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship('News', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_post_user_id'), nullable=False)
    comments = db.relationship('Comment', backref='news_comments', cascade='all, delete-orphan', lazy=True)

    @property
    def image_file_path(self):
        return self._image_file_path

    @image_file_path.setter
    def image_file_path(self, value):
        self._image_file_path = value if value else None

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'))

    def __repr__(self):
        return f'<Comment {self.id}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'jfif'}
    print(f"Проверка файла {filename} на допустимость: {'.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions}")
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


# Проверяем, создается ли корректно путь к аватарке при загрузке
def save_avatar(avatar, username):
    try:
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            avatar.save(filepath)
            return filename
    except Exception as e:
        print(f"Error saving avatar: {e}")
    return None

@app.route('/')
def index():
    random_news = News.query.order_by(db.func.random()).limit(4).all()
    return render_template("index.html", random_news=random_news)


@app.route('/Cab', methods=['GET', 'POST'])
def Cab():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        avatar = request.files['avatar'] if 'avatar' in request.files else None

        if not username or not password or not email:
            return render_template('Cab.html', error='Введите имя, пароль и почту')

        if len(password) < 8 or len(password) > 32:
            return render_template('Cab.html', error="Пароль должен быть от 8 до 32 символов")

        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('Cab.html', error='Имя уже занято')

        new_avatar_filename = None
        if avatar and allowed_file(avatar.filename):
            new_avatar_filename = save_avatar(avatar, username)
            if not new_avatar_filename:
                return render_template('Cab.html', error='Ошибка при сохранении аватара')

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, email=email, avatar=new_avatar_filename)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    # Добавляем возврат шаблона в случае GET-запроса
    return render_template('Cab.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return render_template('login.html', error='Введите имя пользователя и пароль')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Неверные имя пользователя или пароль')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Получаем имя пользователя и его ID для передачи в шаблон
    username = current_user.username
    user_id = current_user.id
    # Получаем ссылку на аватар пользователя
    avatar = current_user.avatar
    return render_template('dashboard.html', username=username, user_id=user_id, avatar=avatar)

@app.route('/admin_panel', methods=['GET', 'POST'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    genres = Genre.query.all()
    categories = Category.query.all()  # Запрос всех категорий
    products_query = Product.query

    # Handle product search
    products_query = Product.query
    product_search_query = request.form.get('search_product')
    if product_search_query:
        products_query = products_query.filter(Product.name.contains(product_search_query) | Product.description.contains(product_search_query))
    products = products_query.limit(3).all()  # Ограничение до 3 товаров

    # Handle user search
    user_query = User.query
    user_search_query = request.form.get('search_user')
    if user_search_query:
        user_query = user_query.filter(User.username.contains(user_search_query) | User.email.contains(user_search_query))
    all_users = user_query.all()
    random_users = user_query.order_by(db.func.random()).limit(10).all()

    # Handle group search and filter
    group_query = Group.query
    group_search_query = request.form.get('search_group')
    genre_filter = request.form.get('genre_filter')
    if group_search_query:
        group_query = group_query.filter(Group.name.contains(group_search_query))
    if genre_filter:
        group_query = group_query.filter_by(genre_id=genre_filter)
    groups = group_query.limit(5).all()  # Ограничение до 5 групп

    # Handle news search
    news_query = News.query
    news_search_query = request.form.get('search_news')
    if news_search_query:
        news_query = news_query.filter(News.title.contains(news_search_query) | News.content.contains(news_search_query))
    all_news = news_query.all()
    random_news = news_query.order_by(db.func.random()).limit(3).all()

    # Handle order search
    order_query = Order.query.join(User).add_columns(Order.id, Order.order_number, User.username, Order.total_price, Order.created_at)
    order_search_query = request.form.get('search_order')
    if order_search_query:
        order_query = order_query.filter(Order.order_number.contains(order_search_query))
    all_orders = order_query.all()
    orders = Order.query.join(User).all()

    return render_template('admin_panel.html', 
                           random_users=random_users,
                           all_users=all_users,
                           genres=genres,
                           groups=groups,
                           random_news=random_news,
                           all_news=all_news,
                           categories=categories,
                           products=products,
                           orders=orders,
                           all_orders=all_orders)


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.is_admin = True if request.form.get('is_admin') == 'on' else False
        
        # Проверяем, был ли отправлен новый пароль
        if request.form.get('password'):
            if len(request.form['password']) < 8 or len(request.form['password']) > 32:
                flash("Пароль должен быть от 8 до 32 символов.")
                return redirect(url_for('edit_user', user_id=user.id))
            user.password = generate_password_hash(request.form['password'])

        db.session.commit()
        flash('Пользователь успешно отредактирован.')
        return redirect(url_for('admin_panel'))

    return render_template('edit_user.html', user=user)

    
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_admin = True if request.form.get('is_admin') == 'on' else False

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, email=email, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()

        flash('Новый пользователь успешно добавлен.')
        return redirect(url_for('admin_panel'))

    return render_template('add_user.html')

@app.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    if 'avatar' in request.files:
        avatar = request.files['avatar']
        if avatar.filename != '' and allowed_file(avatar.filename):
            # Удаление старого файла
            if current_user.avatar:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar))
                except Exception as e:
                    print(f"Error deleting old avatar file: {e}")
            
            # Сохранение новой картинки профиля
            filename = secure_filename(avatar.filename)
            avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Обновление поля avatar в объекте пользователя
            current_user.avatar = filename
            db.session.commit()
            flash('Avatar updated successfully.')
        else:
            flash('Invalid file type. Allowed file types are png, jpg, jpeg, gif.')
    else:
        flash('No avatar uploaded.')
    return redirect(url_for('dashboard'))

@app.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'POST':
        new_username = request.form['new_username']

        # Проверяем, чтобы новое имя пользователя не совпадало с существующими именами
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            flash('Это имя пользователя уже занято. Пожалуйста, выберите другое имя.')
            return redirect(url_for('change_username'))

        current_user.username = new_username
        db.session.commit()
        flash('Имя пользователя успешно обновлено.')
        return redirect(url_for('dashboard'))

    return render_template('change_username.html')

@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_file = request.files['image']

        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'newsimg', filename)
            image_file.save(image_path)
            image_path = os.path.join('newsimg', filename).replace("\\", "/")

        # Получение идентификатора текущего пользователя
        user_id = current_user.id if current_user.is_authenticated else None

        new_news = News(title=title, content=content, image_path=image_path, user_id=user_id)
        db.session.add(new_news)
        db.session.commit()

        return redirect(url_for('news'))

    return render_template('add_news.html')


@app.route('/edit_news/<int:news_id>', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    news = News.query.get(news_id)
    if not news:
        flash('Новость не найдена.')
        return redirect(url_for('news'))  # Перенаправление на страницу новостей

    if not current_user.is_admin and current_user.id != news.user_id:
        flash('Вы не можете редактировать эту новость.')
        return redirect(url_for('news'))  # Перенаправление на страницу новостей

    if request.method == 'POST':
        news.title = request.form['title']
        news.content = request.form['content']
        image_file = request.files['image']

        if image_file and allowed_file(image_file.filename):
            # Удаление старой картинки из базы данных и файла
            if news.image_path:
                try:
                    os.remove(os.path.join(app.static_folder, news.image_path))
                except Exception as e:
                    print(f"Error deleting old image file: {e}")
                news.image_path = None  # Обнуляем путь к изображению в базе данных

            # Сохранение новой картинки в файловой системе
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'newsimg', filename)
            image_file.save(image_path)
            news.image_path = os.path.join('newsimg', filename).replace("\\", "/")  # Обновляем путь к новой картинке в базе данных

            db.session.commit()
            flash('Новость успешно отредактирована.')
            return redirect(url_for('news'))  # Перенаправление на страницу новостей

    return render_template('edit_news.html', news=news)



@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('admin_panel'))

    user = User.query.get(user_id)
    if not user:
        flash('Пользователь не найден.')
        return redirect(url_for('admin_panel'))

    db.session.delete(user)
    db.session.commit()
    flash('Пользователь успешно удален.')
    return redirect(url_for('admin_panel'))


@app.route('/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    news = News.query.get(news_id)
    if not news:
        flash('Новость не найдена.')
        return redirect(url_for('news'))

    if not current_user.is_admin and current_user.id != news.user_id:
        flash('Вы не можете удалить эту новость.')
        return redirect(url_for('news'))

    # Удаление картинки из базы данных и файла
    if news.image_path:
        try:
            os.remove(os.path.join(app.static_folder, news.image_path))
        except Exception as e:
            print(f"Error deleting image file: {e}")

    db.session.delete(news)
    db.session.commit()
    flash('Новость успешно удалена.')
    return redirect(url_for('news'))



@app.route('/news', methods=['GET', 'POST'])
def news():
    search_query = request.args.get('search_query', '')
    if search_query:
        all_news = News.query.join(User).options(joinedload(News.author)).filter(
            or_(
                News.title.ilike(f"%{search_query}%"),
                News.content.ilike(f"%{search_query}%"),
                User.username.ilike(f"%{search_query}%")
            )
        ).all()
    else:
        all_news = News.query.all()
    return render_template('news.html', all_news=all_news)


@app.route('/comments/<int:news_id>')
def comments(news_id):
    comments = Comment.query.filter_by(news_id=news_id).all()
    news = News.query.get(news_id)  # Получаем объект новости
    image_path = news.image_path
    return render_template('comments.html', comments=comments, news=news, image_path=image_path)  # Передаем новость в шаблон


@app.route('/add_comment/<int:news_id>', methods=['POST'])
def add_comment(news_id):
    content = request.form['content']
    new_comment = Comment(content=content, user_id=current_user.id, news_id=news_id)  # Используем news_id
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('comments', news_id=news_id))

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if not comment:
        flash('Комментарий не найден.')
        return redirect(url_for('news'))

    # Проверяем, имеет ли пользователь право удалять этот комментарий
    if not current_user.is_admin and current_user.id != comment.user_id:
        flash('Вы не можете удалить этот комментарий.')
        return redirect(url_for('news'))

    db.session.delete(comment)
    db.session.commit()
    flash('Комментарий успешно удален.')
    return redirect(url_for('comments', news_id=comment.news_id))

@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if not comment:
        flash('Комментарий не найден.')
        return redirect(url_for('news'))

    # Проверяем, имеет ли текущий пользователь право редактировать этот комментарий
    if current_user.id != comment.user_id:
        flash('Вы можете редактировать только свой комментарий.')
        return redirect(url_for('news'))

    if request.method == 'POST':
        comment.content = request.form['content']
        db.session.commit()
        flash('Комментарий успешно отредактирован.')
        return redirect(url_for('comments', news_id=comment.news_id))

    return render_template('edit_comment.html', comment=comment)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Genre {self.name}>'

groups_genres = db.Table('groups_genres',
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True)
)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)  # Поле для описания группы
    image_path = db.Column(db.String(200))  # Поле для пути к изображению группы
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=False)  # Добавляем внешний ключ

    # Добавляем связь с объектом Genre
    genre = db.relationship('Genre', backref=db.backref('groups', lazy='dynamic'))

@app.route('/add_genre', methods=['GET', 'POST'])
@login_required
def add_genre():
    if not current_user.is_admin:
        flash('Доступ к добавлению жанров разрешен только администраторам.')
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        genre_name = request.form['genre_name']

        if not genre_name:
            flash('Введите название жанра.')
            return redirect(url_for('add_genre'))

        new_genre = Genre(name=genre_name)
        db.session.add(new_genre)
        db.session.commit()

        flash('Жанр успешно добавлен.')
        return redirect(url_for('admin_panel'))

    return render_template('add_genre.html')

@app.route('/delete_genre/<int:genre_id>', methods=['POST'])
@login_required
def delete_genre(genre_id):
    if not current_user.is_admin:
        flash('Доступ к удалению жанров разрешен только администраторам.')
        return redirect(url_for('admin_panel'))

    genre = Genre.query.get(genre_id)
    if not genre:
        flash('Жанр не найден.')
        return redirect(url_for('admin_panel'))

    db.session.delete(genre)
    db.session.commit()
    flash('Жанр успешно удален.')
    return redirect(url_for('admin_panel'))

@app.route('/genre/<int:genre_id>')
def genre(genre_id):
    genre = Genre.query.get_or_404(genre_id)
    groups = Group.query.filter_by(genre_id=genre_id).all()
    return render_template('genre.html', genre=genre, groups=groups)

@app.route('/search_genre/<int:genre_id>', methods=['POST'])
def search_genre(genre_id):
    search_query = request.form.get('search_group', '')
    genre = Genre.query.get_or_404(genre_id)
    if search_query:
        groups = Group.query.filter(
            Group.genre_id == genre_id,
            Group.name.ilike(f'%{search_query}%')
        ).all()
    else:
        groups = Group.query.filter_by(genre_id=genre_id).all()
    return render_template('genre.html', genre=genre, groups=groups)

@app.route('/genres')
def genres():
    # Получаем список всех жанров из базы данных
    genres = Genre.query.all()
    return render_template('genres.html', genres=genres)

@app.route('/search_genres', methods=['POST'])
def search_genres():
    search_query = request.form.get('search_genre', '')
    if search_query:
        genres = Genre.query.filter(Genre.name.ilike(f'%{search_query}%')).all()
    else:
        genres = Genre.query.all()
    return render_template('genres.html', genres=genres)


@app.route('/add_group', methods=['GET', 'POST'])
@login_required
def add_group():
    if not current_user.is_admin:
        flash('Access to admin panel is allowed only for administrators.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        genre_id = request.form['genre']
        image_file = request.files['image']

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'group_images', filename)
            image_file.save(image_path)

            # Сохранение относительного пути с прямыми слэшами
            image_relative_path = os.path.join('group_images', filename).replace("\\", "/")

            new_group = Group(name=name, description=description, image_path=image_relative_path, genre_id=genre_id)
            db.session.add(new_group)
            db.session.commit()

            flash('New group successfully added.')
            return redirect(url_for('group_details', group_id=new_group.id))
        else:
            flash('Invalid file type. Allowed file types are png, jpg, jpeg, gif.')

    genres = Genre.query.all()
    return render_template('add_group.html', genres=genres)



@app.route('/delete_group/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    group = Group.query.get(group_id)
    if not group:
        flash('Группа не найдена.')
        return redirect(url_for('admin_panel'))

    try:
        # Удаление картинки из папки
        if group.image_path:
            try:
                os.remove(os.path.join(app.static_folder, group.image_path))
            except Exception as e:
                print(f"Error deleting image file: {e}")

        # Удаление записи о группе из базы данных
        db.session.delete(group)
        db.session.commit()
        flash('Группа успешно удалена.')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении группы: {str(e)}')

    return redirect(url_for('admin_panel'))




@app.route('/group/<int:group_id>')
def group_details(group_id):
    group = Group.query.get(group_id)
    if group:
        return render_template('group_details.html', group=group)
    else:
        flash('Group not found.')
        return redirect(url_for('index'))
    
    
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200), nullable=True)  # Новое поле
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

    # Добавьте связь с объектом Group, если это необходимо
    group = db.relationship('Group', backref=db.backref('articles', lazy='dynamic'))

@app.route('/group/<int:group_id>/article/add', methods=['GET', 'POST'])
@login_required
def add_article(group_id):
    if not current_user.is_admin:
        flash('Доступ разрешен только администраторам.')
        return redirect(url_for('index'))

    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_file = request.files.get('image')


        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'article_images', filename)
            image_file.save(image_path)
            image_path = os.path.join('article_images', filename).replace("\\", "/")

        new_article = Article(title=title, content=content, image_path=image_path, group_id=group_id)
        db.session.add(new_article)
        db.session.commit()

        flash('Статья успешно добавлена.')
        return redirect(url_for('group_details', group_id=group_id))

    return render_template('edit_article.html', group=group, article=None)




@app.route('/group/<int:group_id>/article/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_article(group_id, article_id):
    if not current_user.is_admin:
        flash('Доступ разрешен только администраторам.')
        return redirect(url_for('index'))

    group = Group.query.get_or_404(group_id)
    article = Article.query.get_or_404(article_id)

    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']

        image_file = request.files.get('image')

        if image_file and allowed_file(image_file.filename):
            # Удаление прошлой картинки из базы данных и файла
            if article.image_path:
                try:
                    os.remove(os.path.join(app.static_folder, article.image_path))
                except Exception as e:
                    print(f"Error deleting old image file: {e}")
                article.image_path = None  # Обнуляем путь к изображению в базе данных

            # Сохранение новой картинки в файловой системе
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'article_images', filename)
            image_file.save(image_path)
            article.image_path = os.path.join('article_images', filename).replace("\\", "/")  # Обновляем путь к новой картинке в базе данных

        db.session.commit()

        flash('Статья успешно обновлена.')
        return redirect(url_for('group_details', group_id=group_id))

    return render_template('edit_article.html', group=group, article=article)




@app.route('/group/<int:group_id>/article/add_image', methods=['POST'])
@login_required
def add_image(group_id):
    if not current_user.is_admin:
        flash('Доступ разрешен только администраторам.')
        return redirect(url_for('index'))

    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        image_file = request.files['image']

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'article_images', filename)
            image_file.save(image_path)
            image_path = os.path.join('article_images', filename).replace("\\", "/")
            flash('Изображение успешно добавлено.')
            return redirect(url_for('group_details', group_id=group_id))

    flash('Ошибка при загрузке изображения.')
    return redirect(url_for('group_details', group_id=group_id))


@app.route('/group/<int:group_id>/article/<int:article_id>/delete', methods=['POST'])
@login_required
def delete_article(group_id, article_id):
    if not current_user.is_admin:
        flash('Доступ разрешен только администраторам.')
        return redirect(url_for('index'))

    article = Article.query.get_or_404(article_id)
    
    # Удаление картинки из базы данных и файла
    if article.image_path:
        try:
            os.remove(os.path.join(app.static_folder, article.image_path))
        except Exception as e:
            print(f"Error deleting image file: {e}")

    db.session.delete(article)
    db.session.commit()
    flash('Статья успешно удалена.')
    return redirect(url_for('group_details', group_id=group_id))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_path = db.Column(db.String(200))
    products = db.relationship('Product', backref='category', lazy=True)



class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    product = db.relationship('Product', backref='cart_items')
    user = db.relationship('User', backref='cart_items')


@app.route('/admin/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        
        # Обработка загрузки изображения
        image_file = request.files['image']
        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'category_images', filename)
            image_file.save(image_path)
            image_path = os.path.join('category_images', filename).replace("\\", "/")

        category = Category(name=name, image_path=image_path)
        db.session.add(category)
        db.session.commit()
        flash('Категория успешно добавлена.')
        return redirect(url_for('shop'))

    return render_template('add_category.html')


@app.route('/admin/edit_category/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        category.name = request.form['name']

        # Обработка загрузки нового изображения
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                # Удаляем старое изображение, если оно существует
                if category.image_path:
                    delete_image(category.image_path)
                
                # Сохраняем новое изображение
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.static_folder, 'category_images', filename)
                image_file.save(image_path)
                category.image_path = os.path.join('category_images', filename).replace("\\", "/")

        db.session.commit()
        flash('Категория успешно отредактирована.')
        return redirect(url_for('shop'))

    return render_template('edit_category.html', category=category)



@app.route('/admin/delete_category/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    category = Category.query.get_or_404(category_id)
    
    if category.image_path:
        delete_image(category.image_path)
        
    db.session.delete(category)
    db.session.commit()
    
    flash('Категория успешно удалена.')
    return redirect(url_for('admin_panel'))


@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    categories = Category.query.all()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category_id = request.form['category']
        image_file = request.files['image']

        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'product_images', filename)
            image_file.save(image_path)
            image_path = os.path.join('product_images', filename).replace("\\", "/")

        product = Product(name=name, description=description, price=price, image_path=image_path, category_id=category_id)
        db.session.add(product)
        db.session.commit()
        flash('Товар успешно добавлен.')
        return redirect(url_for('shop'))

    return render_template('add_product.html', categories=categories)

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = request.form['price']
        product.category_id = request.form['category']
        image_file = request.files['image']

        if image_file and allowed_file(image_file.filename):
            # Remove old image if exists
            if product.image_path:
                try:
                    os.remove(os.path.join(app.static_folder, product.image_path))
                except Exception as e:
                    print(f"Error deleting old image file: {e}")
            # Save new image
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.static_folder, 'product_images', filename)
            image_file.save(image_path)
            product.image_path = os.path.join('product_images', filename).replace("\\", "/")

        db.session.commit()
        flash('Товар успешно отредактирован.')
        return redirect(url_for('admin_panel'))

    return render_template('edit_product.html', product=product, categories=categories)


@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    # Remove image file if exists
    if product.image_path:
        try:
            os.remove(os.path.join(app.static_folder, product.image_path))
        except Exception as e:
            print(f"Error deleting image file: {e}")
    
    db.session.delete(product)
    db.session.commit()
    flash('Товар успешно удален.')
    return redirect(url_for('admin_panel'))

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    flash('Товар добавлен в корзину.')
    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)

    if cart_item.user_id != current_user.id:
        flash('Вы не можете удалить этот товар из корзины.')
        return redirect(url_for('cart'))

    db.session.delete(cart_item)
    db.session.commit()
    flash('Товар удален из корзины.')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def update_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)

    if cart_item.user_id != current_user.id:
        flash('Вы не можете обновить этот товар в корзине.')
        return redirect(url_for('cart'))

    new_quantity = int(request.form['quantity'])
    if new_quantity < 1:
        flash('Количество товара должно быть больше 0.')
    else:
        cart_item.quantity = new_quantity
        db.session.commit()
        flash('Количество товара в корзине обновлено.')

    return redirect(url_for('cart'))



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='order_items')

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Ваша корзина пуста.')
        return redirect(url_for('cart'))

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(user_id=current_user.id, total_price=total_price)
    db.session.add(order)
    db.session.commit()

    for item in cart_items:
        order_item = OrderItem(order_id=order.id, product_id=item.product.id, quantity=item.quantity)
        db.session.add(order_item)
        db.session.delete(item)

    db.session.commit()
    
    flash(f'Ваш заказ №{order.id} успешно оформлен на сумму {total_price} руб.')
    return redirect(url_for('order_confirmation', order_id=order.id))

@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Вы не можете просматривать этот заказ.')
        return redirect(url_for('index'))

    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    return render_template('order_confirmation.html', order=order, order_items=order_items)

    # Модель для обратной связи
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

# Форма обратной связи
class FeedbackForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Сообщение', validators=[DataRequired()])
    submit = SubmitField('Отправить')

# Маршрут для отправки обратной связи
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data

        # Сохранение обратной связи в базе данных
        feedback_entry = Feedback(name=name, email=email, message=message)
        db.session.add(feedback_entry)
        db.session.commit()

        flash('Ваше сообщение успешно отправлено!', 'success')
        return redirect(url_for('feedback'))

    return render_template('feedback.html', form=form)

# Маршрут для просмотра всех сообщений обратной связи (для администратора)
@app.route('/admin/feedback', methods=['GET'])
def admin_feedback():
    feedback_messages = Feedback.query.all()
    return render_template('admin_feedback.html', feedback_messages=feedback_messages)

@app.route('/search', methods=['GET'])
def search_products():
    search_query = request.args.get('search_query', '')
    # Выполнение поиска по `search_query`
    if search_query:
        # Используем ilike для выполнения частичного сопоставления
        products = Product.query.filter(or_(Product.name.ilike(f"%{search_query}%"), Product.description.ilike(f"%{search_query}%"))).all()
    else:
        products = Product.query.all()  # Если search_query пустой, вернуть все товары

    return render_template('category_products.html', category=None, products=products)


@app.route('/Shop')
def shop():
    categories = Category.query.all()
    return render_template('Shop.html', categories=categories)


@app.route('/shop/category/<int:category_id>')
def category_products(category_id):
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id).all()
    return render_template('category_products.html', category=category, products=products)


@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', product=product)

def delete_image(image_path):
    full_path = os.path.join(app.static_folder, image_path)
    if os.path.exists(full_path):
        os.remove(full_path)

@app.route('/backup_database')
@login_required
def manual_backup_database():
    return create_backup(is_manual=True)

def create_backup(is_manual=False):
    try:
        backup_folder = 'backups'
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        prefix = "Manual_" if is_manual else "Auto_"
        backup_filename = f"{prefix}Database_backup_{current_time}.db"
        
        source_file = os.path.join(app.root_path, 'instance/Database.db')
        destination_file = os.path.join(app.root_path, backup_folder, backup_filename)

        current_app.logger.info(f"Source file: {source_file}")
        current_app.logger.info(f"Destination file: {destination_file}")
        
        shutil.copy(source_file, destination_file)
        
        if is_manual:
            flash(f'База данных успешно сохранена как {backup_filename}')
            return redirect(url_for('admin_panel'))
        
        return Response(status=200)
    except Exception as e:
        if is_manual:
            flash(f'Произошла ошибка при сохранении базы данных: {str(e)}', 'error')
            return redirect(url_for('admin_panel'))
        
        current_app.logger.error(f'Ошибка сохранения базы данных: {str(e)}')
        return Response(status=500)

def scheduled_backup():
    with app.app_context():
        create_backup(is_manual=False)

# Scheduler setup
scheduler = BackgroundScheduler()

if __name__ == '__main__':
    with app.app_context():
        print("Attempting to create all tables")
        db.create_all()
    
    if not scheduler.running:
        scheduler.add_job(scheduled_backup, 'interval', minutes=12)
        scheduler.start()
    
    try:
        app.run(host= '0.0.0.0')
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        scheduler.shutdown()
    
