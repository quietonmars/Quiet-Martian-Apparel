from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response, abort
from flask_login import login_user, login_required, logout_user, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import sqlite3
from . import db
from datetime import datetime, timedelta, date
import os
from sqlalchemy import create_engine, text, desc, func, or_
from collections import Counter, defaultdict
import uuid

from .models import Customer, Staff, Category, Brand, Product, Color, Discount, product_color, Order, Payment, AboutUs

import smtplib
from email.message import EmailMessage

conn = sqlite3.connect('././instance/database.db', check_same_thread=False)
conn.execute("PRAGMA busy_timeout = 5000")
SQLALCHEMY_ENGINE_OPTIONS = {"pool_timeout": 30}

auth = Blueprint('auth', __name__)

conn.row_factory = sqlite3.Row

engine = create_engine('sqlite:///database.db', connect_args={'timeout': 60})
conn = engine.connect()

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    # Check if the user is a customer
    customer = Customer.query.get(int(user_id))
    if customer:
        return customer

    # Check if the user is a staff member
    staff = Staff.query.get(int(user_id))
    if staff:
        return staff

    # If the user is not found or is not active, return None
    return None


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        customer = Customer.query.filter_by(username=username).first()
        if customer:
            if check_password_hash(customer.password, password):
                flash('Logged In Successfully!', category='success')
                login_user(customer, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect Password. Please try again.', category='error')
        else:
            flash('Username does not exist', category='error')

    return render_template("customer/login.html", user=current_user)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        nric = request.form['nric']
        nationality = request.form['nationality']
        phone_number = request.form['phone_number']
        dob = request.form['dob']
        email = request.form['email']
        address = request.form['address']
        card_no = request.form['card_no']
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']

        dob = datetime.strptime(dob, '%Y-%m-%d')

        check_email = Customer.query.filter_by(email=email).first()
        username_check = Customer.query.filter_by(username=username).first()

        if username_check:
            flash('Username already exists', category='error')
        elif check_email:
            flash('Email already exists', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        elif len(name) < 2:
            flash('Name must be greater than 1 character.', category='error')
        elif password != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters', category='error')
        else:
            new_customer = Customer(name=name, nric=nric, nationality=nationality, phone_number=phone_number, dob=dob,
                                    email=email, address=address, card_no=card_no, username=username,
                                    password=generate_password_hash(password, method='sha256'))

            db.session.add(new_customer)
            db.session.commit()
            to = email
            subject = "Your account has been successfully created"
            body = "Hi " + name + ", " + "\n\n\n" + "We are pleased to inform you that your account has been" \
                                                    " successfully created in Quiet Martian Apparel" + "\n\n" \
                                                    "You can now login using your username." + "\n\nUsername :" \
                   + username + "\n\n" + "With your new account, you can enjoy the" \
                                         "following benefits: \n-Faster checkout \n-View and track your " \
                                         "orders" \
                                         "\n-Save your favorite products to your wishlist \n-Make Save and" \
                                         "secure payments"+ "Thank you for shopping with us.\n\nBest regards,\nQuiet " \
                                                            "Martian Apparel "
            print(to)
            print(subject)
            print(body)
            send_email(to, subject, body)
            flash('Account Registered Successfully!', category='success')
            return redirect(url_for('auth.login'))

    return render_template("customer/signup.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', category="success")
    return redirect(url_for('views.home'))


@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        customer = Customer.query.filter_by(id=current_user.id).first
    else:
        user = current_user

    dob = user.dob.strftime('%Y-%m-%d')
    return render_template("customer/profile.html", user=user, dob=dob)


@auth.route('/profile/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_profile(customer_id):
    customer = Customer.query.filter_by(id=customer_id).first()
    if customer != current_user:
        abort(403)

    if request.method == 'POST':
        name = request.form['name']
        nrc = request.form['nrc']
        nationality = request.form['nationality']
        phone = request.form['phone']
        dob_str = request.form['dob']
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        email = request.form['email']
        add = request.form['add']
        card = request.form['card']
        usn = request.form['usn']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password and confirm_password and password == confirm_password:
            current_user.set_password(password)

        customer.name = name
        customer.nrc = nrc
        customer.nationality = nationality
        customer.phone_number = phone
        customer.dob = dob
        customer.email = email
        customer.address = add
        customer.card_no = card
        customer.username = usn

        check_email = Customer.query.filter_by(email=email).first()
        username_check = Customer.query.filter_by(username=usn).first()

        if username_check and username_check != customer:
            flash('Username already exists', category='error')
        elif check_email and check_email != customer:
            flash('Email already exists', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        elif len(name) < 2:
            flash('Name must be greater than 1 character.', category='error')
        elif password and (password != confirm_password):
            flash('Passwords don\'t match.', category='error')
        elif password and (len(password) < 7):
            flash('Password must be at least 7 characters', category='error')
        else:
            if password:
                password = generate_password_hash(password, method='sha256')
                current_user.password = password
            db.session.commit()
            flash('Your profile has been updated.', 'success')
            return redirect(url_for('auth.profile'))

    dob_str = customer.dob.strftime('%Y-%m-%d')
    return render_template("customer/edit_profile.html", customer=customer, dob=dob_str, user=current_user)


@auth.route('/product-details/<int:id>', methods=['GET', 'POST'])
def product_details(id):
    product = Product.query.filter_by(id=id).first()
    # products = p
    colors = Color.query.join(product_color).filter(product_color.c.product_id == id).all()
    price = product.price
    if product.discount is not None:
        discount_percentage = product.discount.percentage
        discount_price = price * (100 - discount_percentage) / 100
        price = discount_price
    else:
        discount_percentage = 0

    if request.method == 'POST':
        color_id = request.form['color']
        product_id = request.form['product_id']
        print(product_id)
        color = Color.query.get(color_id)
        quantity = int(request.form['quantity'])
        price = product.price
        add_to_cart(current_user.id, product.id, quantity, price)

        return redirect(url_for('auth.cart'))

    return render_template("customer/product_details.html", datetime=datetime, product=product, price=price,
                           colors=colors, user=current_user)


@auth.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    customer_id = current_user.id
    product_id = request.form['product_id']
    color = request.form['color']
    quantity = int(request.form['quantity'])
    price = float(request.form['price'])

    # Fetch the product from the database
    product = Product.query.get(product_id)

    # Reduce the stock by the quantity specified in the order
    product.stock -= quantity

    if product.discount and product.discount.start_date.date() <= date.today() <= product.discount.end_date.date():
        discount_percentage = product.discount.percentage
        discount_price = price * (100 - discount_percentage) / 100
        price = discount_price

    # Create the order
    order = Order(customer_id=customer_id,
                  product_id=product_id,
                  quantity=quantity,
                  color=color,
                  price=price,
                  order_total=quantity * price,
                  order_status='cart')
    order.order_no = str(uuid.uuid4())

    db.session.add(order)
    db.session.commit()

    flash('Item successfully Added to Cart', category="success")
    return redirect(url_for('auth.cart'))


@auth.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    customer_id = current_user.id
    orders = Order.query.filter_by(customer_id=customer_id, order_status='cart').all()
    total = sum(order.order_total for order in orders)
    print(f"Number of orders: {len(orders)}")

    customer = Customer.query.get(customer_id)
    credit_info = customer.card_no
    if credit_info:
        print("credit number available")
    else:
        credit_info = ""

    return render_template("customer/cart.html", datetime=datetime, credit_info=credit_info, orders=orders, total=total,
                           user=current_user)


@auth.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    customer_id = current_user.id
    orders = Order.query.filter_by(customer_id=customer_id, order_status='cart').all()
    for order in orders:
        product = order.product
        product.stock += order.quantity  # Increase product stock by the quantity of the order
        db.session.delete(order)  # Remove the order from the database
    db.session.commit()

    flash('Your cart has been cleared!', 'success')
    return redirect(url_for('auth.cart'))


@auth.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    customer_id = current_user.id
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        card_no = request.form.get('card_no')
        expiry = request.form.get('expiry')
        orders = Order.query.filter_by(customer_id=customer_id, order_status='cart').all()
        payment_status = 'paid'

        expiry_d = datetime.strptime(expiry, '%Y-%m-%d')
        for order in orders:
            order.order_status = 'paid'
            payment = Payment(
                order_id=order.id,
                customer_id=order.customer_id,
                card_no=card_no,
                payment_method=payment_method,
                expiry=expiry_d,
                payment_date=datetime.now(),
                payment_status=payment_status
            )
            db.session.add(payment)
        db.session.commit()
        to = current_user.email
        paid_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = "Quiet Martian Apparel Order Confirmation for " + current_user.name
        body = "Hi " + current_user.name + ",\n\n" + "Your order for " + order.product.title + " has been paid using " + payment_method + ".\n\n" + "Order Date: " + paid_date + "\n\n" + "Price: " + str(
            order.price) + "$" + "\n\n" + "Quantity: " + str(order.quantity) + "\n\n" + "Total Amount: " + str(
            order.order_total) + "$" + "\n\n\n\n" + "Thank you for shopping with us.\n\nBest regards,\nQuiet Martian Apparel"
        print(to)
        print(subject)
        print(body)
        send_email(to, subject, body)
        flash('Order paid successfully', category="success")

        return redirect(url_for('auth.order_history'))
    return render_template("customer/payment.html", user=current_user)


@auth.route('/order-history')
@login_required
def order_history():
    customer_id = current_user.id
    orders = Order.query.filter(Order.order_status != 'cart', Order.customer_id == customer_id).all()
    total = sum(order.order_total for order in orders)
    print(f"Number of orders: {len(orders)}")
    return render_template("customer/order_history.html", orders=orders, total=total, user=current_user)


@auth.route('/order-details/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get(order_id)
    if not order or order.customer_id != current_user.id:
        abort(404)
    return render_template("customer/order_details.html", order=order, user=current_user)


@auth.route('/about-us')
def about_us():
    about_us = AboutUs.query.order_by(AboutUs.created_date.desc()).first()
    print(about_us.image)
    return render_template("customer/about_us.html", about_us=about_us, user=current_user)


# STAFF Part


@auth.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        staff = Staff.query.filter_by(username=username).first()
        if staff:
            if staff.status == "activated":
                if check_password_hash(staff.password, password):
                    flash('Logged In Successfully!', category='success')
                    login_user(staff, remember=True)
                    if staff.type == 'staff':
                        return redirect(url_for('auth.sales_dashboard'))
                    elif staff.type == 'admin':
                        return redirect(url_for('auth.manage_customers'))
                else:
                    flash('Incorrect Password. Please try again.', category='error')
            else:
                flash('Account is not activated. Please contact administrator.', category='error')
        else:
            flash('Username does not exist', category='error')

    return render_template("staff/staff_login.html", user=current_user)


@auth.route('/admin-logout')
@login_required
def admin_logout():
    logout_user()
    flash('Logged out successfully', category="success")
    return redirect(url_for('auth.staff_login'))


@auth.route('/new-staff', methods=['GET', 'POST'])
def new_staff():
    if request.method == 'POST':
        name = request.form['name']
        nric = request.form['nric']
        phone_number = request.form['phone_number']
        dob = request.form['dob']
        email = request.form['email']
        address = request.form['address']
        # status = request.form['status']
        staff_type = request.form['type']
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']

        email_staff = Staff.query.filter_by(email=email).first()
        staff = Staff.query.filter_by(username=username).first()
        if staff:
            flash('Username already exists.', category='error')
        elif email_staff:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        elif len(name) < 2:
            flash('Name must be greater than 1 character.', category='error')
        elif password != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters', category='error')
        else:
            dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
            hashed_password = generate_password_hash(password, method='sha256')
            staff = Staff(name=name, nric=nric, phone_number=phone_number, dob=dob_date,
                          email=email, address=address, status="pending", type=staff_type,
                          username=username, password=hashed_password)
            db.session.add(staff)
            db.session.commit()
            to = email
            subject = "Account has been Created Successfully"
            body = "Dear " + name + ",\n\n\n" + "Your account has been successfully created and will be reviewed by " \
                                                "our team." \
                                                "We will let you know when the account is updated." + "\nUsername: " + username + "\n\n\nBest regards,\nQuiet Martian Apparel"
            print(to)
            print(subject)
            print(body)
            send_email(to, subject, body)
            flash('Account Registered Successfully! Please wait for account to be reviewed and approved.',
                  category='success')
            return redirect(url_for('auth.staff_login'))

    return render_template("staff/new_staff.html", user=current_user)


@auth.route('/sales-dashboard', methods=['GET', 'POST'])
@login_required
def sales_dashboard():
    # get all paid orders
    orders = Order.query.filter_by(order_status='paid').all()
    if not orders:
        flash('There are no orders in the system yet.',
              category='success')
        cc = ''
        msc = ''
        count_b = ''
        count_c = ''
        msb = ''
        most_sold_color = ''
    else:
        # get a list of tuples containing the product ID and its quantity for each order
        product_quantities = [(order.product_id, order.quantity) for order in orders]

        # count the number of times each product has been sold
        product_sales_count = Counter(dict(product_quantities))

        # get the most sold product by category
        category_sales_count = {}
        for product_id, quantity in product_quantities:
            category_id = Product.query.get(product_id).category_id
            category_sales_count[category_id] = category_sales_count.get(category_id, 0) + quantity
        most_sold_category = Category.query.get(max(category_sales_count, key=category_sales_count.get))

        # get the most sold product by brand
        brand_sales_count = {}
        for product_id, quantity in product_quantities:
            brand_id = Product.query.get(product_id).brand_id
            brand_sales_count[brand_id] = brand_sales_count.get(brand_id, 0) + quantity
        most_sold_brand = Brand.query.get(max(brand_sales_count, key=brand_sales_count.get))

        # get the number of orders for each category and brand
        category_order_count = {}
        brand_order_count = {}
        for order in orders:
            category_id = Product.query.get(order.product_id).category_id
            category_order_count[category_id] = category_order_count.get(category_id, 0) + 1
            brand_id = Product.query.get(order.product_id).brand_id
            brand_order_count[brand_id] = brand_order_count.get(brand_id, 0) + 1

        # print the results
        print(f"Most sold category: {most_sold_category.name}")
        print(f"Most sold brand: {most_sold_brand.name}")
        print("Number of orders by category:")
        for category_id, order_count in category_order_count.items():
            category = Category.query.get(category_id)
            print(f"{category.name}: {order_count}")
        print("Number of orders by brand:")
        for brand_id, order_count in brand_order_count.items():
            brand = Brand.query.get(brand_id)
            print(f"{brand.name}: {order_count}")

        msb = most_sold_brand.name
        msc = most_sold_category.name
        count_c = (f"{category.name}: {order_count}")
        count_b = (f"{brand.name}: {order_count}")

        color_counts = defaultdict(int)
        for order in orders:
            for product_color in order.product.colors:
                color_counts[product_color.name] += order.quantity

        most_sold_color = max(color_counts, key=color_counts.get)
        print(most_sold_color)
        color_order_count = defaultdict(int)

        orders = Order.query.filter_by(order_status='paid').all()

        for order in orders:
            product = order.product
            for color in product.colors:
                color_order_count[color.name] += order.quantity

        for color_name, order_count in color_order_count.items():
            print(f"{color_name}: {order_count}")

        cc = (f"{order_count}")
    almost_out_of_stock = Product.query.filter(Product.stock < 5).all()

    return render_template("staff/sales_dashboard.html", cc=cc, msc=msc, count_b=count_b, count_c=count_c, msb=msb,
                           most_sold_color=most_sold_color, orders=orders, user=current_user,
                           almost_out_of_stock=almost_out_of_stock)


@auth.route('/order-report', methods=['GET', 'POST'])
def order_report():
    orders = Order.query.filter_by(order_status='paid').all()
    tod_orders = Order.query.filter_by(order_status='delivering').all()
    d_orders = Order.query.filter_by(order_status='delivered').all()
    return render_template("staff/order_report.html", tod_orders=tod_orders, d_orders=d_orders, orders=orders,
                           user=current_user)


@auth.route('/order-delivering', methods=['POST'])
def order_delivering():
    order_id = request.form['order_id']
    order = Order.query.get(order_id)
    if order:
        order.order_status = 'delivering'
        flash('Order is now Successfully added to delivery', category='success')
        db.session.commit()
        to = order.customer.email
        subject = "Your Order for " + order.product.title + " is now added to Delivery"
        delivering_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        body = "Hi " + order.customer.name + ",\n\n" + "Your order for " + order.product.title + " have been added to delivery. And estimated to arrive within one week." + "\n\n" + "Delivery Address: " + order.customer.address + "\n\n" + "Delivery Date: " + delivering_date + "\n\n" + "Price: " + str(
            order.price) + "$" + "\n\n" + "Quantity: " + str(order.quantity) + "\n\n" + "Total Amount: " + str(
            order.order_total) + "$" + "\n\n\n\n" + "Thank you for shopping with us.\n\nBest regards,\nQuiet Martian Apparel"
        print(to)
        print(subject)
        print(body)
        send_email(to, subject, body)
    return redirect(url_for('auth.order_report'))


@auth.route('/order-delivered', methods=['POST'])
def order_delivered():
    order_id = request.form['order_id']
    order = Order.query.get(order_id)
    if order:
        order.order_status = 'delivered'
        flash('Order is now Successfully Delivered', category='success')
        db.session.commit()
        to = order.customer.email
        subject = "Your Order for " + order.product.title + " is now successfully delivered"
        delivered_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        body = "Hi " + order.customer.name + ",\n\n" + "We are delighted to inform you that your order for the " + order.product.title + " has been successfully delivered to your specified address. We hope that you are satisfied with your purchase." + "\n\n" + "Delivery Address: " + order.customer.address + "\n\n" + "Delivery Date: " + delivered_date + "\n\n" + "Price: " + str(
            order.price) + "$" + "\n\n" + "Quantity: " + str(order.quantity) + "\n\n" + "Total Amount: " + str(
            order.order_total) + "$" + "\n\n\n\n" + "Thank you for shopping with us.\n\nBest regards,\nQuiet Martian Apparel"
        print(to)
        print(subject)
        print(body)
        send_email(to, subject, body)
    return redirect(url_for('auth.order_report'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif', 'bmp'}


@auth.route('/manage-products', methods=['GET', 'POST'])
@login_required
def manage_products():
    p = Product.query.all()
    products = p

    c = Category.query.all()
    categories = c

    b = Brand.query.all()
    brands = b

    co = Color.query.all()
    colors = co

    dis = Discount.query.all()
    discounts = dis

    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['desc']
        stock = request.form['stock']
        brand_id = request.form['brand']
        cat_id = request.form['cat']
        discount_id = request.form.get('discount')
        if discount_id is None:
            discount_id = 0
        price = request.form['price']
        colors = request.form.getlist('colors[]')
        print(colors)

        colors_str = ','.join(colors)

        image1 = request.files['image1']
        image2 = request.files['image2']
        image3 = request.files['image3']

        uploaded_file = ""
        if 'image1' not in request.files:
            flash('No image 1 file')
            return redirect(request.url)
        elif 'image2' not in request.files:
            flash('No image 2 file')
            return redirect(request.url)
        elif 'image3' not in request.files:
            flash('No image 3 file')
            return redirect(request.url)

        if image1.filename == '':
            print('no image 1 selected')
        elif image2.filename == '':
            print('no image 2 selected')
        elif image3.filename == '':
            print('no image 3 selected')
        else:
            filename = secure_filename(image1.filename)
            filename = filename.replace(' ', '_')
            image1.save(os.path.join("website/static/uploads/", filename))
            uploaded_file = filename
            flash('Image 1 Uploaded')
            imagefile1 = uploaded_file

            filename2 = secure_filename(image2.filename)
            filename2 = filename2.replace(' ', '_')
            image2.save(os.path.join("website/static/uploads/", filename2))
            uploaded_file2 = filename2
            flash('Image 2 Uploaded')
            imagefile2 = uploaded_file2

            filename3 = secure_filename(image3.filename)
            filename3 = filename3.replace(' ', '_')
            image3.save(os.path.join("website/static/uploads/", filename3))
            uploaded_file3 = filename3
            flash('Image 3 Uploaded')
            imagefile3 = uploaded_file3

        new_product = Product(title=name, description=desc, stock=stock, brand_id=brand_id, category_id=cat_id,
                              discount_id=discount_id, price=price, color_id=colors_str, image_1=imagefile1,
                              image_2=imagefile2, image_3=imagefile3, created_by_id=current_user.name,
                              updated_by_id=current_user.name)

        db.session.add(new_product)
        db.session.commit()

        for color_id in colors:
            new_color = product_color.insert().values(
                product_id=new_product.id,
                color_id=color_id
            )
            db.session.execute(new_color)
            db.session.commit()

        flash('New Product Added Successfully', category='success')

        return redirect(url_for('auth.manage_products'))

    return render_template("staff/products.html", datetime=datetime, categories=categories, brands=brands,
                           colors=colors, discounts=discounts, products=products, user=current_user)


@auth.route('/manage-products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get(product_id)
    b = Brand.query.all()
    brands = b

    products = Product.query.all()

    if request.method == 'POST':
        product.title = request.form['name']
        product.description = request.form['desc']
        product.stock = request.form['stock']
        product.stock = request.form['brand']
        product.category_id = request.form['cat']
        discount = request.form.get('discount')
        if not discount:
            discount = 0
        product.discount_id = discount
        product.price = request.form['price']
        colors = request.form.getlist('colors[]')
        colors_str = ','.join(colors)
        product.color_id = colors_str
        for color_id in colors:
            new_color = product_color.insert().values(
                product_id=product_id,
                color_id=color_id
            )
            db.session.execute(new_color)
            db.session.commit()

        if 'image1' in request.files:
            image1 = request.files['image1']
            if image1.filename != '':
                filename = secure_filename(image1.filename)
                filename = filename.replace(' ', '_')
                image1.save(os.path.join("website/static/uploads/", filename))
                product.image_1 = filename

        if 'image2' in request.files:
            image2 = request.files['image2']
            if image2.filename != '':
                filename = secure_filename(image2.filename)
                filename = filename.replace(' ', '_')
                image2.save(os.path.join("website/static/uploads/", filename))
                product.image_2 = filename

        if 'image3' in request.files:
            image3 = request.files['image3']
            if image3.filename != '':
                filename = secure_filename(image3.filename)
                filename = filename.replace(' ', '_')
                image3.save(os.path.join("website/static/uploads/", filename))
                product.image_3 = filename

        db.session.commit()

        flash('Product updated successfully', 'success')
        return redirect(url_for('auth.manage_products'))

    categories = Category.query.all()
    colors = Color.query.all()
    discounts = Discount.query.all()

    return render_template("staff/edit_product.html", datetime=datetime, products=products, brands=brands,
                           product=product, categories=categories, colors=colors, discounts=discounts,
                           user=current_user)


@auth.route('/manage-brands', methods=['GET', 'POST'])
@login_required
def manage_brands():
    bran = Brand.query.all()
    brands = bran
    if request.method == 'POST':
        Brand_name = request.form.get('newbrand')
        new_brand = Brand(name=Brand_name, created_by=current_user.name, updated_by=current_user.name)
        db.session.add(new_brand)
        db.session.commit()
        flash('New Brand Added Successfully', category='success')
        return redirect(url_for('auth.manage_brands', user=current_user))
    return render_template("staff/brands.html", brands=brands, user=current_user)


@auth.route('/manage-brands/edit/<int:brand_id>', methods=['GET', 'POST'])
@login_required
def edit_brand(brand_id):
    bran = Brand.query.all()
    brands = bran
    brand = Brand.query.get(brand_id)
    if request.method == 'POST':
        brand.name = request.form['brand_name']
        brand.updated_by = current_user.name
        brand.updated_date = datetime.utcnow()
        db.session.commit()
        flash('Brand updated successfully', category='success')
        return redirect(url_for('auth.manage_brands'))
    return render_template('staff/edit_brand.html', brands=brands, brand=brand, user=current_user)


@auth.route('/manage-category', methods=['GET', 'POST'])
@login_required
def manage_category():
    categories = Category.query.all()

    if request.method == 'POST':
        Category_name = request.form.get('newcat')
        new_category = Category(name=Category_name, created_by=current_user.name, updated_by=current_user.name)
        db.session.add(new_category)
        db.session.commit()
        flash('New Category Added Successfully', category='success')

        return redirect(url_for('auth.manage_category', user=current_user))

    return render_template("staff/categories.html", categories=categories, user=current_user)


@auth.route('/edit-category/<int:category_id>/<category_name>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id, category_name):
    category = Category.query.get(category_id)
    categories = Category.query.all()
    if request.method == 'POST':
        category.name = request.form.get('newcat')
        category.updated_by = current_user.name
        category.updated_date = datetime.now()
        db.session.commit()
        flash('Category Updated Successfully', category='success')
        return redirect(url_for('auth.manage_category', user=current_user))

    return render_template("staff/edit_category.html", categories=categories, category=category,
                           category_name=category.name, user=current_user)


@auth.route('/manage-colors', methods=['GET', 'POST'])
@login_required
def manage_colors():
    co = Color.query.all()
    colors = co
    if request.method == 'POST':
        color_name = request.form.get('newcolor')
        color_code = request.form.get('color_code')

        new_color = Color(name=color_name, color_code=color_code)
        db.session.add(new_color)
        db.session.commit()
        flash('New Color Added Successfully', category='success')
        return redirect(url_for('auth.manage_colors', user=current_user))

    return render_template("staff/manage_colors.html", colors=colors, user=current_user)


@auth.route('/edit-colors/<int:color_id>', methods=['GET', 'POST'])
@login_required
def edit_colors(color_id):
    color = Color.query.get(color_id)
    co = Color.query.all()
    colors = co
    if request.method == 'POST':
        color.name = request.form.get('name')
        color.color_code = request.form.get('color_code')
        db.session.commit()
        flash('Color Updated Successfully', category='success')
        return redirect(url_for('auth.manage_colors', user=current_user))

    return render_template("staff/edit_color.html", color=color, colors=colors, user=current_user)


@auth.route('/manage-discount', methods=['GET', 'POST'])
@login_required
def manage_discount():
    d = Discount.query.all()
    discounts = d

    if request.method == 'POST':
        discount_name = request.form.get('name')
        discount_code = request.form.get('code')
        discount_percentage = request.form.get('percentage')
        discount_start_date = request.form.get('start_date')
        discount_end_date = request.form.get('end_date')

        d_sdate = datetime.strptime(discount_start_date, '%Y-%m-%d').date()
        d_edate = datetime.strptime(discount_end_date, '%Y-%m-%d').date()
        new_discount = Discount(name=discount_name, discount_code=discount_code, percentage=discount_percentage,
                                start_date=d_sdate, end_date=d_edate, created_by=current_user.name,
                                updated_by=current_user.name)
        db.session.add(new_discount)
        db.session.commit()
        flash('New Discount Added Successfully', category='success')
        return redirect(url_for('auth.manage_discount', user=current_user))

    return render_template("staff/discount.html", discounts=discounts, user=current_user)


@auth.route('/manage-discount/edit/<int:discount_id>', methods=['GET', 'POST'])
@login_required
def edit_discount(discount_id):
    discount = Discount.query.get(discount_id)
    d = Discount.query.all()
    discounts = d
    if request.method == 'POST':
        discount.name = request.form['name']
        discount.discount_code = request.form['code']
        discount.percentage = request.form['percentage']
        discount.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        discount.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        discount.updated_by = current_user.name
        db.session.commit()
        flash('Discount updated successfully', category='success')
        return redirect(url_for('auth.manage_discount'))

    return render_template('staff/edit_discount.html', discount=discount, discounts=discounts, user=current_user)


# ADMIN STAFF

@auth.route('/manage-customers', methods=['GET', 'POST'])
@login_required
def manage_customers():
    c = Customer.query.all()
    customers = c

    return render_template("staff/manage_customers.html", customers=customers, user=current_user)


@auth.route('/manage-staffs', methods=['GET', 'POST'])
@login_required
def manage_staffs():
    s = Staff.query.all()
    staffs = s
    return render_template("staff/manage_staffs.html", staffs=staffs, user=current_user)


@auth.route('/approve_reject_staff/<int:id>/<string:status>')
def approve_reject_staff(id, status):
    staff = Staff.query.get_or_404(id)

    if staff.status == status:
        flash(f"Staff status already set to {status}", category="info")
        return redirect(url_for('auth.manage_staffs'))

    if status == 'pending':
        return redirect(url_for('auth.manage_staffs'))

    if request.args.get('confirm') == 'true':
        staff.status = status
        db.session.commit()
        to = staff.email
        subject = "Your Account has been " + status
        body = "Dear " + staff.name + ", \n\n\n" + "Your account has been updated to " + status + \
               ". \n\nIf your account has been approved, you can now login." + \
               "\nIf your account has been deactivated without prior notice, Please contact us." + \
               "\n\n Best Regards, \n Quiet Martian Staff Team"
        print(to)
        print(subject)
        print(body)
        send_email(to, subject, body)

        if status == 'activated':
            flash('Staff is approved', category='success')
        elif status == 'rejected':
            flash('Staff is rejected', category='warning')
        elif status == 'deactivated':
            flash('Staff account is deactivated', category='info')
        elif status == 'activated':
            flash('Staff account is activated', category='success')
        else:
            print('Change status canceled')
            flash('Change Status Cancelled', category='success')

    return f"""
            <script>
                if ('{staff.status}' !== '{status}' && confirm('Are you sure you want to change the status of admin {staff.name} to {status}?')) {{
                    window.location = '{url_for('auth.approve_reject_staff', id=id, status=status, confirm='true')}';
                }} else {{
                    window.location = '{url_for('auth.manage_staffs')}';
                }}
            </script>
        """


@auth.route('/about_us/edit', methods=['GET', 'POST'])
@login_required
def edit_aboutus():
    about_us = AboutUs.query.order_by(AboutUs.updated_date.desc()).first()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        image = request.files['image']
        uploaded_file = ""
        if 'image' not in request.files:

            imagefile = about_us.image  # use the old image
        else:
            image = request.files['image']
            if image.filename == '':

                imagefile = about_us.image  # use the old image
            else:

                filename = secure_filename(image.filename)
                filename = filename.replace(' ', '_')
                image.save(os.path.join("website/static/uploads/", filename))
                uploaded_file = filename
                flash('Image Uploaded')
                imagefile = uploaded_file

        new_aboutus = AboutUs(staff_id=current_user.id, title=title, description=description, image=imagefile,
                              created_date=datetime.now(), created_by=current_user.id, updated_date=datetime.now(),
                              updated_by=current_user.id)
        db.session.add(new_aboutus)
        db.session.commit()
        flash('About Us page updated!', category='success')
        return redirect(url_for('auth.edit_aboutus'))

    return render_template('staff/edit_aboutus.html', about_us=about_us, user=current_user)


def send_email(to, subject, body):
    # Create a new email message
    msg = EmailMessage()
    msg.set_content(body)
    msg['To'] = to
    msg['Subject'] = subject
    msg['From'] = 'yangster24dawhla@gmail.com'

    # Connect to the SMTP server and send the message
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login('yangster24dawhla@gmail.com', 'kimungscuzlobuff')
        smtp.send_message(msg)
