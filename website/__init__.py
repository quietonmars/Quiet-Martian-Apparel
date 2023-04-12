import os.path
from flask import Flask, request, redirect, url_for, Blueprint
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash


db = SQLAlchemy()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'asdfasdfpoihadf adsflkhadf'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    app.config['UPLOAD_FOLDER'] = "static/uploads/"

    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import Customer, Order, Payment, Product, Brand, Category, Discount, Staff, AboutUs

    with app.app_context():
        db.create_all()
        if not Staff.query.all():
            password = generate_password_hash('Apple1234$', method='sha256')
            staff = Staff(
                name='Default Staff',
                nric='aa123',
                phone_number='09700895',
                dob=datetime.now(),
                email='staff@example.com',
                address='123 Default Street, Default City',
                status='activated',
                type='staff',
                username='staff1',
                password=password,
                created_by=1,
                updated_by=1
            )
            admin = Staff(
                name='Admin',
                nric='aa123',
                phone_number='09700895',
                dob=datetime.now(),
                email='admin@example.com',
                address='123 Default Street, Default City',
                status='activated',
                type='admin',
                username='admin',
                password=password,
                created_by=1,
                updated_by=1
            )
            db.session.add(staff)
            db.session.add(admin)
            print('success database default staff')
            db.session.commit()


    # create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = ('auth.login')
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        customer = Customer.query.get(int(id))
        if customer:
            return customer
        staff = Staff.query.get(int(id))
        if staff:
            return staff
        return None

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')