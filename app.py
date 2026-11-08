import os
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-this-before-deploy')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gaz_tup_dev.db').replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', '0') == '1'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Devam etmek için giriş yapın.'

ROLES = ['Yönetici', 'Planlama', 'Depo Kabul', 'Kalite Denetim', 'Sürücü', 'Salt Okunur']

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(140), nullable=False)
    role = db.Column(db.String(40), nullable=False, default='Salt Okunur')
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    def get_id(self): return str(self.id)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True)
    name = db.Column(db.String(180), nullable=False)
    active = db.Column(db.Boolean, default=True)

class CylinderType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True)
    name = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.String(50))

class Cylinder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial_no = db.Column(db.String(100), unique=True, nullable=False)
    cylinder_type_id = db.Column(db.Integer, db.ForeignKey('cylinder_type.id'))
    status = db.Column(db.String(40), nullable=False, default='Depoda - Dolu')
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(60), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    status = db.Column(db.String(40), default='Yeni')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles: abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco

def audit(action, detail=''):
    db.session.add(AuditLog(user_id=current_user.id, action=action, detail=detail))

@app.cli.command('init-db')
def init_db():
    db.create_all()
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')
    if username and password and not User.query.filter_by(username=username).first():
        db.session.add(User(username=username, full_name='Sistem Yöneticisi', role='Yönetici', password_hash=generate_password_hash(password)))
        db.session.commit()
        print('Yönetici hesabı oluşturuldu.')
    else: print('Tablolar hazır. Yönetici için ADMIN_USERNAME ve ADMIN_PASSWORD tanımlayın.')

@app.route('/')
def home(): return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

@app.route('/giris', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username','').strip(), active=True).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            login_user(user)
            db.session.add(AuditLog(user_id=user.id, action='Giriş yaptı', detail=''))
            db.session.commit()
            return redirect(url_for('dashboard'))
        flash('Kullanıcı adı veya şifre hatalı.', 'danger')
    return render_template('login.html')

@app.route('/cikis')
@login_required
def logout():
    audit('Çıkış yaptı'); db.session.commit(); logout_user(); return redirect(url_for('login'))

@app.route('/panel')
@login_required
def dashboard():
    stats = {'customers': Customer.query.filter_by(active=True).count(), 'cylinders': Cylinder.query.count(), 'orders': Order.query.count(), 'users': User.query.filter_by(active=True).count()}
    recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    return render_template('dashboard.html', stats=stats, recent=recent)

@app.route('/kullanicilar', methods=['GET','POST'])
@roles_required('Yönetici')
def users():
    if request.method == 'POST':
        username=request.form.get('username','').strip(); password=request.form.get('password',''); name=request.form.get('full_name','').strip(); role=request.form.get('role','Salt Okunur')
        if not username or len(password)<12 or not name or role not in ROLES:
            flash('Bilgileri kontrol edin. Şifre en az 12 karakter olmalı.', 'danger')
        elif User.query.filter_by(username=username).first(): flash('Bu kullanıcı adı zaten kayıtlı.', 'danger')
        else:
            db.session.add(User(username=username, full_name=name, role=role, password_hash=generate_password_hash(password)))
            audit('Kullanıcı oluşturdu', username); db.session.commit(); flash('Kullanıcı oluşturuldu.', 'success')
        return redirect(url_for('users'))
    return render_template('users.html', users=User.query.order_by(User.username).all(), roles=ROLES)

@app.errorhandler(403)
def forbidden(_): return render_template('message.html', title='Yetki yok', message='Bu sayfaya erişim yetkiniz bulunmuyor.'),403

with app.app_context():
    db.create_all()

    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if admin_username and admin_password:
        existing_admin = User.query.filter_by(
            username=admin_username
        ).first()

        if not existing_admin:
            admin = User(
                username=admin_username,
                full_name='Sistem Yöneticisi',
                role='Yönetici',
                password_hash=generate_password_hash(admin_password)
            )
            db.session.add(admin)
            db.session.commit()
            print('İlk yönetici hesabı oluşturuldu.')

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
