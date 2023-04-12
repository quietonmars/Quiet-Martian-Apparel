from flask import Blueprint
from flask import Flask, flash, redirect, render_template, request, session, g, current_app, url_for
from flask_login import login_required, current_user
from .models import Product, Brand, Color, Category

views = Blueprint('views', __name__)


@views.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    if query:
        products = Product.query.filter(
            (Product.title.ilike(f'%{query}%')) |
            (Product.description.ilike(f'%{query}%')) |
            (Brand.name.ilike(f'%{query}%')) |
            (Category.name.ilike(f'%{query}%')) |
            (Color.name.ilike(f'%{query}%'))
        ).paginate(page=page, per_page=8)
    else:
        products = Product.query.paginate(page=page, per_page=8)
    return render_template("customer/home.html", products=products, query=query, user=current_user)

