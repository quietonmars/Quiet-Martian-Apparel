from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash



class Customer(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    nric = db.Column(db.String(150))
    nationality = db.Column(db.String(150))
    phone_number = db.Column(db.String(150))
    dob = db.Column(db.DateTime)
    email = db.Column(db.String(150), unique=True)
    address = db.Column(db.String(255))
    card_no = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, default=func.now())

    payments = db.relationship('Payment')
    orders = db.relationship('Order')

    def set_password(self, password):
        """Set the password hash for the customer."""
        self.password_hash = generate_password_hash(password)


class Order(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    order_no = db.Column(db.String(150), unique=True)
    quantity = db.Column(db.Integer)
    color = db.Column(db.String(30))
    price = db.Column(db.Float)
    order_total = db.Column(db.Float)
    order_date = db.Column(db.DateTime, default=func.now())
    order_status = db.Column(db.String(150))

    payments = db.relationship('Payment')
    product = db.relationship('Product', lazy=True)
    customer = db.relationship('Customer', lazy=True)


class Payment(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    card_no = db.Column(db.String(150))
    payment_method = db.Column(db.String(150))
    expiry = db.Column(db.DateTime)
    payment_date = db.Column(db.DateTime, default=func.now())
    payment_status = db.Column(db.String(150))


class Product(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    title = db.Column(db.String(150))
    description = db.Column(db.String(255))
    stock = db.Column(db.Integer)
    discount_id = db.Column(db.Integer, db.ForeignKey('discount.id'))
    price = db.Column(db.Float)
    color_id = db.Column(db.Integer, db.ForeignKey('color.id'))
    image_1 = db.Column(db.String(150))
    image_2 = db.Column(db.String(150))
    image_3 = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, default=func.now())
    created_by_id = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by_id = db.Column(db.Integer)

    brand = db.relationship('Brand')
    category = db.relationship('Category')
    color = db.relationship('Color')
    colors = db.relationship('Color', secondary='product_color')
    orders = db.relationship('Order', lazy=True)
    discount = db.relationship('Discount', lazy=True)
    # c = db.relationship('product_color', lazy=True)


product_color = db.Table('product_color',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
    db.Column('color_id', db.Integer, db.ForeignKey('color.id'))
)


class Color(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    color_code = db.Column(db.String(150))

    products = db.relationship('Product')


class Brand(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, default=func.now())
    created_by = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by = db.Column(db.Integer)

    products = db.relationship('Product')


class Category(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, default=func.now())
    created_by = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by = db.Column(db.Integer)

    products = db.relationship('Product')


class Discount(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    discount_code = db.Column(db.String(150), unique=True)
    percentage = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_date = db.Column(db.DateTime, default=func.now())
    created_by = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by = db.Column(db.Integer)

    products = db.relationship('Product')


class Staff(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    nric = db.Column(db.String(150))
    phone_number = db.Column(db.String(20))
    dob = db.Column(db.Date)
    email = db.Column(db.String(150), unique=True)
    address = db.Column(db.String(255))
    status = db.Column(db.String(150))
    type = db.Column(db.String(150))
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    created_date = db.Column(db.DateTime, default=func.now())
    created_by = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by = db.Column(db.Integer)

    about_us = db.relationship('AboutUs')
    # products = db.relationship('Product')
    # brands = db.relationship('Brand')
    # categories = db.relationship('Category')
    # discounts = db.relationship('Discount')


class AboutUs(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    created_date = db.Column(db.DateTime, default=func.now())
    created_by = db.Column(db.Integer)
    updated_date = db.Column(db.DateTime, default=func.now())
    updated_by = db.Column(db.Integer)

    staff = db.relationship('Staff')
