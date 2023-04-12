from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from flask_login import login_user, login_required, logout_user, current_user, LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import sqlite3
from . import db
from datetime import datetime, timedelta
import os
from sqlalchemy import create_engine, text, desc, func
from collections import Counter, defaultdict
import uuid

from .models import Customer, Staff, Category, Brand, Product, Color, Discount, product_color, Order, Payment, AboutUs

conn = sqlite3.connect('././instance/database.db', check_same_thread=False)
conn.execute("PRAGMA busy_timeout = 5000")
SQLALCHEMY_ENGINE_OPTIONS = {"pool_timeout": 30}

auth = Blueprint('auth',__name__)

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
                                    email=email, address=address, card_no=card_no, username=username, password=generate_password_hash(password, method='sha256'))

            db.session.add(new_customer)
            db.session.commit()
            flash('Account Registered Successfully!', category='success')
            return redirect(url_for('auth.login'))

    return render_template("customer/signup.html",user=current_user)


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
    return render_template("customer/profile.html", user=user,dob=dob)


@auth.route('/product-details/<int:id>', methods=['GET', 'POST'])
def product_details(id):
    product = Product.query.filter_by(id=id).first()
    # products = p
    colors = Color.query.join(product_color).filter(product_color.c.product_id == id).all()
    price = product.price
    if product.discount:
        discount_percentage = product.discount.percentage
        discount_price = price * (100 - discount_percentage) / 100
        price = discount_price

    if request.method == 'POST':
        color_id = request.form['color']
        product_id = request.form['product_id']
        print(product_id)
        color = Color.query.get(color_id)
        quantity = int(request.form['quantity'])
        price = product.price
        add_to_cart(current_user.id, product.id, quantity, price)

        return redirect(url_for('auth.cart'))

    return render_template("customer/product_details.html", product=product, price=price, colors=colors, user=current_user)


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

    if product.discount:
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

    return render_template("customer/cart.html", credit_info=credit_info, orders=orders, total=total, user=current_user)


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
        flash('Order paid successfully', category="success")

        return redirect(url_for('auth.order_history'))
    return render_template("customer/payment.html", user=current_user)


@auth.route('/order-history')
@login_required
def order_history():
    customer_id = current_user.id
    orders = Order.query.filter_by(customer_id=customer_id, order_status='paid').all()
    total = sum(order.order_total for order in orders)
    print(f"Number of orders: {len(orders)}")
    return render_template("customer/order_history.html", orders=orders, total=total, user=current_user)


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
            flash('Account Registered Successfully! Please wait for account to be reviewed and approved.', category='success')
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

        cc = (f"{color_name}: {order_count}")

    return render_template("staff/sales_dashboard.html", cc=cc,msc=msc, count_b=count_b, count_c=count_c, msb=msb, most_sold_color=most_sold_color, orders=orders, user=current_user)


@auth.route('/order-report', methods=['GET', 'POST'])
def order_report():
    orders = Order.query.filter_by(order_status='paid').all()
    return render_template("staff/order_report.html", orders=orders, user=current_user)


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
            imagefile1=uploaded_file

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
                              discount_id=discount_id, price=price, color_id=colors_str, image_1=imagefile1, image_2=imagefile2, image_3=imagefile3, created_by_id=current_user.name, updated_by_id=current_user.name)

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

    return render_template("staff/products.html", categories=categories, brands=brands, colors=colors, discounts=discounts, products=products, user=current_user)


@auth.route('/manage-brands', methods=['GET', 'POST'])
@login_required
def manage_brands():
    bran = Brand.query.all()
    brands = bran
    if request.method == 'POST':
        Brand_name = request.form.get('newbrand')
        new_brand = Brand(name=Brand_name,created_by=current_user.name, updated_by=current_user.name)
        db.session.add(new_brand)
        db.session.commit()
        flash('New Brand Added Successfully', category='success')
        return redirect(url_for('auth.manage_brands', user=current_user))
    return render_template("staff/brands.html",brands=brands, user=current_user)


@auth.route('/manage-category', methods=['GET', 'POST'])
@login_required
def manage_category():
    cat = Category.query.all()
    categories = cat
    if request.method == 'POST':
        Category_name = request.form.get('newcat')
        new_category = Category(name=Category_name,created_by=current_user.name, updated_by=current_user.name)
        db.session.add(new_category)
        db.session.commit()
        flash('New Category Added Successfully', category='success')
        return redirect(url_for('auth.manage_category', user=current_user))

    return render_template("staff/categories.html", categories=categories, user=current_user)


@auth.route('/manage-colors', methods=['GET', 'POST'])
@login_required
def manage_colors():
    co = Color.query.all()
    colors = co
    if request.method == 'POST':
        color_name = request.form.get('newcolor')
        color_code = request.form.get('color_code')

        new_color = Color(name=color_name,color_code=color_code)
        db.session.add(new_color)
        db.session.commit()
        flash('New Color Added Successfully', category='success')
        return redirect(url_for('auth.manage_colors', user=current_user))

    return render_template("staff/manage_colors.html", colors= colors, user=current_user)


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
        new_discount = Discount(name=discount_name, discount_code=discount_code, percentage=discount_percentage, start_date=d_sdate,end_date=d_edate,created_by=current_user.name, updated_by=current_user.name)
        db.session.add(new_discount)
        db.session.commit()
        flash('New Discount Added Successfully', category='success')
        return redirect(url_for('auth.manage_discount', user=current_user))

    return render_template("staff/discount.html", discounts=discounts,user=current_user)


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
            flash('Change Status Cancelled',category='success')

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
    about_us = AboutUs.query.first()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        image = request.files['image']
        uploaded_file = ""
        if 'image' not in request.files:
            flash('No image file')
            return redirect(request.url)

        if image.filename == '':
            print('no image selected')
        else:
            filename = secure_filename(image.filename)
            filename = filename.replace(' ', '_')
            image.save(os.path.join("website/static/uploads/", filename))
            uploaded_file = filename
            flash('Image Uploaded')
            imagefile = uploaded_file

        new_aboutus = AboutUs(staff_id=current_user.id, title=title, description=description, image=imagefile, created_date=datetime.now(), created_by=current_user.id, updated_date=datetime.now(), updated_by=current_user.id)
        db.session.add(new_aboutus)
        db.session.commit()
        flash('About Us page updated!', category='success')
        return redirect(url_for('auth.edit_aboutus'))

    return render_template('staff/edit_aboutus.html', about_us=about_us, user=current_user)