from fileinput import filename
import os
from dotenv import load_dotenv
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user, login_required, UserMixin
from werkzeug.utils import secure_filename
from sqlalchemy import text

# --- Настройки Flask ---
app = Flask(__name__)
load_dotenv()

database_url = os.getenv('DATABASE_URL')
if database_url:
    print("Using DATABASE_URL from environment")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    print("Using local PostgreSQL database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:tucson@localhost:5432/sneaker_db'

app.config['UPLOAD_FOLDER'] = 'static/img'
app.secret_key = 'tucson'

# --- Инициализация ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Модели ---
class Client(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='client')

class Sneaker(db.Model):
    __tablename__ = 'sneakers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    brand = db.Column(db.String(50), nullable=False, default='Unknown')
    is_featured = db.Column(db.Boolean, default=False)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sneaker_id = db.Column(db.Integer, db.ForeignKey('sneakers.id'), nullable=False)
    sneaker = db.relationship('Sneaker', backref='cart_items')
    quantity = db.Column(db.Integer, default=1)
    size = db.Column(db.String(10), nullable=False)  # 👈 добавили размер
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)





@login_manager.user_loader
def load_user(client_id):
    return Client.query.get(int(client_id))

# --- Декоратор ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Маршруты ---
@app.route('/')
def home():
    selected_brand = request.args.get('brand')
    if selected_brand and selected_brand != 'All':
        sneakers = Sneaker.query.filter_by(brand=selected_brand).all()
    else:
        sneakers = Sneaker.query.all()

    brands = ['All', 'Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance']
    return render_template('sitegpt.html', sneakers=sneakers, brands=brands, selected_brand=selected_brand)

@app.route('/admin/clients', methods=['GET', 'POST'])
@login_required
def manage_clients():
    if current_user.role != 'admin':
        return render_template('403.html'), 403

    clients = Client.query.all()

    if request.method == 'POST':
        client_id = request.form['client_id']
        new_role = request.form['new_role']

        client = Client.query.get(client_id)
        if client:
            client.role = new_role
            db.session.commit()
            flash(f'Роль клиента {client.username} изменена на {new_role}', 'success')
        return redirect(url_for('manage_clients'))

    return render_template('manage_clients.html', clients=clients)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_client = Client(username=username, email=email, password=hashed_password)
        try:
            db.session.add(new_client)
            db.session.commit()
            flash('Аккаунт создан!', 'success')
            login_user(new_client)
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка регистрации: {e}', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        client = Client.query.filter_by(email=email).first()
        if client and bcrypt.check_password_hash(client.password, password):
            login_user(client)
            return redirect(url_for('home'))
        else:
            flash('Неверные данные для входа', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/add_sneaker', methods=['GET', 'POST'])
@admin_required
def add_sneaker():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        brand = request.form['brand']
        is_featured = 'is_featured' in request.form

        file = request.files['image_file']

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            name_part, ext_part = os.path.splitext(original_filename)
            unique_suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{name_part}_{unique_suffix}{ext_part}"

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            image_url = f'img/{unique_filename}'

            new_sneaker = Sneaker(
                name=name,
                description=description,
                price=price,
                image_url=image_url,
                brand=brand,
                is_featured=is_featured
            )
            try:
                db.session.add(new_sneaker)
                db.session.commit()
                flash('Кроссовок успешно добавлен!', 'success')
                return redirect(url_for('home'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении: {e}', 'danger')
        else:
            flash('Недопустимый формат файла!', 'danger')
    return render_template('add_sneaker.html')

@app.route('/edit_sneaker/<int:sneaker_id>', methods=['GET', 'POST'])
@admin_required
def edit_sneaker(sneaker_id):
    sneaker = Sneaker.query.get_or_404(sneaker_id)

    if request.method == 'POST':
        sneaker.name = request.form['name']
        sneaker.description = request.form['description']
        sneaker.price = request.form['price']
        sneaker.brand = request.form['brand']
        sneaker.is_featured = 'is_featured' in request.form

        file = request.files.get('image_file')
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            name_part, ext_part = os.path.splitext(original_filename)
            unique_suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{name_part}_{unique_suffix}{ext_part}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            sneaker.image_url = f'img/{unique_filename}'

        try:
            db.session.commit()
            flash('Кроссовок успешно обновлён!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {e}', 'danger')

    return render_template('edit_sneaker.html', sneaker=sneaker)

@app.route('/delete_sneaker/<int:sneaker_id>', methods=['POST'])
@admin_required
def delete_sneaker(sneaker_id):
    sneaker = Sneaker.query.get_or_404(sneaker_id)

    # Получаем клиентов, у кого этот сникер в корзине
    clients_with_sneaker = db.session.execute(
        text("""
            SELECT c.username
            FROM cart_item ci
            JOIN client c ON ci.client_id = c.id
            WHERE ci.sneaker_id = :sid
        """),
        {'sid': sneaker_id}
    ).fetchall()

    usernames = [row[0] for row in clients_with_sneaker]

    if usernames:
        user_list = ', '.join(usernames)
        flash(f'⚠️ Этот сникер есть в корзинах у: {user_list}. Он будет удалён из их корзин.', 'warning')

    try:
        # Удаляем вручную связанные записи из корзины
        db.session.execute(
            text("DELETE FROM cart_item WHERE sneaker_id = :sid"),
            {'sid': sneaker_id}
        )

        # Удаляем сам сникер
        db.session.delete(sneaker)
        db.session.commit()

        flash('Сникер удалён.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {e}', 'danger')

    return redirect(url_for('home'))



@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    CartItem.query.delete()
    db.session.commit()
    flash('Thank you for your order!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(client_id=current_user.id).all()
    total = sum(item.sneaker.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)




@app.route('/add_to_cart/<int:sneaker_id>', methods=['POST'])
@login_required
def add_to_cart(sneaker_id):
    size = request.form.get('size')
    if not size:
        flash("Пожалуйста, выберите размер.", "danger")
        return redirect(url_for('home'))

    item = CartItem.query.filter_by(
        sneaker_id=sneaker_id, client_id=current_user.id, size=size
    ).first()

    if item:
        item.quantity += 1
    else:
        db.session.add(CartItem(sneaker_id=sneaker_id, client_id=current_user.id, size=size))

    db.session.commit()
    flash('Товар добавлен в корзину!', 'success')
    return redirect(url_for('home'))

@app.route('/update_size/<int:item_id>', methods=['POST'])
@login_required
def update_size(item_id):
    new_size = request.form.get('new_size')
    item = CartItem.query.get_or_404(item_id)
    if item.client_id != current_user.id:
        abort(403)

    item.size = new_size
    db.session.commit()
    flash('Размер обновлён.', 'success')
    return redirect(url_for('cart'))


# --- Обработчик ошибки 403 ---
@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

# --- Запуск ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Sneaker.query.first():
            demo_sneaker = Sneaker(name="Demo Sneaker", description="First sneaker", price=35000, image_url="img/nike.webp", brand="Nike")
            db.session.add(demo_sneaker)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
