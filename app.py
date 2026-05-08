from flask import Flask, render_template_string, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

# ============================================================
#  APP CONFIG
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'shopsmart-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopsmart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# ============================================================
#  MODELS (DATABASE TABLES)
# ============================================================

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)
    phone      = db.Column(db.String(20))
    address    = db.Column(db.Text)
    is_admin   = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders     = db.relationship('Order', backref='user', lazy=True)
    reviews    = db.relationship('Review', backref='user', lazy=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(80), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price       = db.Column(db.Float, nullable=False)
    stock       = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    reviews     = db.relationship('Review', backref='product', lazy=True)

    @property
    def avg_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

class Order(db.Model):
    __tablename__ = 'orders'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total      = db.Column(db.Float, nullable=False)
    status     = db.Column(db.String(30), default='Pending')
    address    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items      = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    price      = db.Column(db.Float, nullable=False)

class Review(db.Model):
    __tablename__ = 'reviews'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)
    comment    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
#  HELPERS
# ============================================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

# ============================================================
#  BASE HTML TEMPLATE
# ============================================================

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}ShopSmart{% endblock %}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
<style>
  body { background:#f8f9fa; }
  .product-card { transition: transform .2s, box-shadow .2s; border:none; }
  .product-card:hover { transform:translateY(-4px); box-shadow:0 8px 20px rgba(0,0,0,.12)!important; }
  .card { border:none; border-radius:10px; }
  footer { border-top:3px solid #ffc107; }
  .table th { font-weight:600; font-size:.85rem; text-transform:uppercase; letter-spacing:.5px; }
</style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top shadow">
  <div class="container">
    <a class="navbar-brand fw-bold fs-4" href="{{ url_for('catalog') }}">
      <i class="bi bi-bag-heart-fill text-warning"></i> ShopSmart
    </a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <ul class="navbar-nav me-auto">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('catalog') }}"><i class="bi bi-shop"></i> Shop</a></li>
        {% if current_user.is_authenticated and current_user.is_admin %}
        <li class="nav-item"><a class="nav-link text-warning" href="{{ url_for('admin_dashboard') }}"><i class="bi bi-speedometer2"></i> Admin</a></li>
        {% endif %}
      </ul>
      <form class="d-flex me-3" action="{{ url_for('catalog') }}" method="get">
        <div class="input-group">
          <input class="form-control" type="search" name="q" placeholder="Search..." value="{{ request.args.get('q','') }}">
          <button class="btn btn-warning" type="submit"><i class="bi bi-search"></i></button>
        </div>
      </form>
      <ul class="navbar-nav">
        <li class="nav-item">
          <a class="nav-link position-relative" href="{{ url_for('view_cart') }}">
            <i class="bi bi-cart3 fs-5"></i>
            {% set cart = session.get('cart', {}) %}
            {% if cart %}
            <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-warning text-dark">
              {{ cart.values()|sum }}
            </span>
            {% endif %}
          </a>
        </li>
        {% if current_user.is_authenticated %}
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
            <i class="bi bi-person-circle"></i> {{ current_user.name }}
          </a>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><a class="dropdown-item" href="{{ url_for('profile') }}"><i class="bi bi-person"></i> Profile</a></li>
            <li><a class="dropdown-item" href="{{ url_for('order_history') }}"><i class="bi bi-box"></i> My Orders</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-right"></i> Logout</a></li>
          </ul>
        </li>
        {% else %}
        <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}"><i class="bi bi-box-arrow-in-right"></i> Login</a></li>
        <li class="nav-item"><a class="btn btn-warning btn-sm ms-2 nav-link" href="{{ url_for('register') }}">Register</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<div class="container my-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show">
        {{ msg }} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {% block content %}{% endblock %}
</div>

<footer class="bg-dark text-white text-center py-3 mt-5">
  <p class="mb-0">&copy; 2024 ShopSmart &mdash; FYP Project &mdash; Flask + SQLite</p>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>
"""

# ============================================================
#  MODULE 1 — AUTH ROUTES
# ============================================================

REGISTER_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Register{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-5">
    <div class="card shadow">
      <div class="card-header bg-dark text-white text-center py-3">
        <h4 class="mb-0"><i class="bi bi-person-plus"></i> Create Account</h4>
      </div>
      <div class="card-body p-4">
        <form method="post">
          <div class="mb-3">
            <label class="form-label fw-bold">Full Name</label>
            <input type="text" name="name" class="form-control" placeholder="Ali Hassan" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Email</label>
            <input type="email" name="email" class="form-control" placeholder="ali@example.com" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Password</label>
            <input type="password" name="password" class="form-control" placeholder="Min 6 characters" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Confirm Password</label>
            <input type="password" name="confirm" class="form-control" required>
          </div>
          <button class="btn btn-warning w-100 fw-bold">Create Account</button>
        </form>
        <hr>
        <p class="text-center mb-0">Already have account? <a href="{{ url_for('login') }}">Login</a></p>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

LOGIN_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Login{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-5">
    <div class="card shadow">
      <div class="card-header bg-dark text-white text-center py-3">
        <h4 class="mb-0"><i class="bi bi-box-arrow-in-right"></i> Login</h4>
      </div>
      <div class="card-body p-4">
        <form method="post">
          <div class="mb-3">
            <label class="form-label fw-bold">Email</label>
            <input type="email" name="email" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Password</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" name="remember" id="rem">
            <label class="form-check-label" for="rem">Remember me</label>
          </div>
          <button class="btn btn-warning w-100 fw-bold">Login</button>
        </form>
        <hr>
        <p class="text-center mb-0">No account? <a href="{{ url_for('register') }}">Register here</a></p>
        <p class="text-center text-muted small mt-1">Admin: admin@shopsmart.com / admin123</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

PROFILE_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Profile{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <div class="card shadow">
      <div class="card-header bg-dark text-white"><h5 class="mb-0"><i class="bi bi-person-circle"></i> My Profile</h5></div>
      <div class="card-body p-4">
        <form method="post">
          <div class="mb-3">
            <label class="form-label fw-bold">Full Name</label>
            <input type="text" name="name" class="form-control" value="{{ current_user.name }}" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Email (cannot change)</label>
            <input type="email" class="form-control" value="{{ current_user.email }}" disabled>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Phone</label>
            <input type="text" name="phone" class="form-control" value="{{ current_user.phone or '' }}">
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Delivery Address</label>
            <textarea name="address" class="form-control" rows="3">{{ current_user.address or '' }}</textarea>
          </div>
          <button class="btn btn-warning w-100 fw-bold">Update Profile</button>
        </form>
        <hr>
        <a href="{{ url_for('order_history') }}" class="btn btn-outline-dark w-100"><i class="bi bi-box"></i> My Orders</a>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

@app.route('/')
def home():
    return redirect(url_for('catalog'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('catalog'))
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if not all([name, email, password]):
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
        else:
            user = User(name=name, email=email, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f'Welcome, {name}!', 'success')
            return redirect(url_for('catalog'))
    return render_template_string(REGISTER_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalog'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user     = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=bool(request.form.get('remember')))
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(request.args.get('next') or url_for('catalog'))
        flash('Invalid email or password.', 'danger')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name    = request.form.get('name', current_user.name).strip()
        current_user.phone   = request.form.get('phone', '').strip()
        current_user.address = request.form.get('address', '').strip()
        db.session.commit()
        flash('Profile updated!', 'success')
    return render_template_string(PROFILE_HTML)

# ============================================================
#  MODULE 2 — PRODUCTS ROUTES
# ============================================================

CATALOG_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Shop{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="row">
  <div class="col-lg-3 mb-4">
    <div class="card shadow-sm">
      <div class="card-header bg-dark text-white"><i class="bi bi-funnel"></i> Filters</div>
      <div class="card-body">
        <h6 class="fw-bold">Categories</h6>
        <a href="{{ url_for('catalog', q=search) }}"
           class="d-block mb-1 text-decoration-none {% if not cat_id %}fw-bold text-warning{% else %}text-dark{% endif %}">
           All Products
        </a>
        {% for cat in categories %}
        <a href="{{ url_for('catalog', cat=cat.id, q=search) }}"
           class="d-block mb-1 text-decoration-none {% if cat_id==cat.id %}fw-bold text-warning{% else %}text-dark{% endif %}">
           {{ cat.name }}
        </a>
        {% endfor %}
        <hr>
        <h6 class="fw-bold">Sort By</h6>
        <a href="{{ url_for('catalog', q=search, cat=cat_id, sort='newest') }}"
           class="d-block mb-1 text-decoration-none {% if sort=='newest' %}fw-bold text-warning{% else %}text-dark{% endif %}">Newest</a>
        <a href="{{ url_for('catalog', q=search, cat=cat_id, sort='price_asc') }}"
           class="d-block mb-1 text-decoration-none {% if sort=='price_asc' %}fw-bold text-warning{% else %}text-dark{% endif %}">Price: Low to High</a>
        <a href="{{ url_for('catalog', q=search, cat=cat_id, sort='price_desc') }}"
           class="d-block mb-1 text-decoration-none {% if sort=='price_desc' %}fw-bold text-warning{% else %}text-dark{% endif %}">Price: High to Low</a>
      </div>
    </div>
  </div>

  <div class="col-lg-9">
    {% if search %}
    <p class="text-muted">Results for: <strong>{{ search }}</strong></p>
    {% endif %}
    {% if products.items %}
    <div class="row row-cols-1 row-cols-md-3 g-4">
      {% for p in products.items %}
      <div class="col">
        <div class="card h-100 shadow-sm product-card">
          <div class="card-body d-flex flex-column align-items-start justify-content-center" style="min-height:130px; background:#f1f3f5; border-radius:10px 10px 0 0;">
            <i class="bi bi-box-seam text-secondary" style="font-size:2.5rem"></i>
          </div>
          <div class="card-body">
            <span class="badge bg-secondary mb-1">{{ p.category.name }}</span>
            <h6 class="fw-bold">{{ p.name }}</h6>
            <div class="mb-1">
              {% for i in range(p.avg_rating|int) %}<i class="bi bi-star-fill text-warning" style="font-size:11px"></i>{% endfor %}
              {% if p.reviews %}<small class="text-muted">({{ p.reviews|length }})</small>{% endif %}
            </div>
            <p class="fs-5 fw-bold text-success mb-1">Rs. {{ "%.0f"|format(p.price) }}</p>
            <small class="text-muted">Stock: {{ p.stock }}</small>
          </div>
          <div class="card-footer d-flex gap-2">
            <a href="{{ url_for('product_detail', product_id=p.id) }}" class="btn btn-outline-dark btn-sm flex-grow-1">Details</a>
            <form method="post" action="{{ url_for('add_to_cart', product_id=p.id) }}">
              <input type="hidden" name="quantity" value="1">
              <button class="btn btn-warning btn-sm"><i class="bi bi-cart-plus"></i></button>
            </form>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% if products.pages > 1 %}
    <nav class="mt-4">
      <ul class="pagination justify-content-center">
        {% for p in products.iter_pages() %}
          {% if p %}
          <li class="page-item {% if p==products.page %}active{% endif %}">
            <a class="page-link" href="{{ url_for('catalog', page=p, q=search, cat=cat_id, sort=sort) }}">{{ p }}</a>
          </li>
          {% else %}
          <li class="page-item disabled"><span class="page-link">…</span></li>
          {% endif %}
        {% endfor %}
      </ul>
    </nav>
    {% endif %}
    {% else %}
    <div class="text-center py-5">
      <i class="bi bi-search fs-1 text-muted"></i>
      <p class="mt-2 text-muted">No products found.</p>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}""")

DETAIL_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}{{ product.name }}{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="{{ url_for('catalog') }}">Shop</a></li>
    <li class="breadcrumb-item">{{ product.category.name }}</li>
    <li class="breadcrumb-item active">{{ product.name }}</li>
  </ol>
</nav>
<div class="row mb-5">
  <div class="col-md-5">
    <div class="card shadow-sm p-5 text-center bg-light" style="min-height:280px">
      <i class="bi bi-box-seam text-muted" style="font-size:5rem"></i>
    </div>
  </div>
  <div class="col-md-7">
    <span class="badge bg-secondary">{{ product.category.name }}</span>
    <h2 class="fw-bold mt-2">{{ product.name }}</h2>
    <div class="mb-2">
      {% for i in range(product.avg_rating|int) %}<i class="bi bi-star-fill text-warning"></i>{% endfor %}
      {% for i in range(5 - product.avg_rating|int) %}<i class="bi bi-star text-warning"></i>{% endfor %}
      <span class="text-muted ms-2">{{ product.avg_rating }}/5 ({{ product.reviews|length }} reviews)</span>
    </div>
    <h3 class="text-success fw-bold">Rs. {{ "%.0f"|format(product.price) }}</h3>
    <p class="text-muted">{{ product.description }}</p>
    <p>
      {% if product.stock > 0 %}
      <span class="badge bg-success"><i class="bi bi-check-circle"></i> In Stock ({{ product.stock }} left)</span>
      {% else %}
      <span class="badge bg-danger">Out of Stock</span>
      {% endif %}
    </p>
    {% if product.stock > 0 %}
    <form method="post" action="{{ url_for('add_to_cart', product_id=product.id) }}" class="d-flex gap-2 align-items-center">
      <label class="fw-bold">Qty:</label>
      <input type="number" name="quantity" value="1" min="1" max="{{ product.stock }}" class="form-control" style="width:80px">
      <button class="btn btn-warning btn-lg"><i class="bi bi-cart-plus"></i> Add to Cart</button>
    </form>
    {% endif %}
  </div>
</div>

<div class="row">
  <div class="col-md-8">
    <h4 class="fw-bold mb-3"><i class="bi bi-chat-square-text"></i> Reviews</h4>
    {% if product.reviews %}
    {% for r in product.reviews %}
    <div class="card mb-3 shadow-sm">
      <div class="card-body">
        <div class="d-flex justify-content-between">
          <div>
            <strong>{{ r.user.name }}</strong>
            <span class="ms-2">{% for i in range(r.rating) %}<i class="bi bi-star-fill text-warning" style="font-size:11px"></i>{% endfor %}</span>
          </div>
          <small class="text-muted">{{ r.created_at.strftime('%d %b %Y') }}</small>
        </div>
        <p class="mt-2 mb-0">{{ r.comment }}</p>
        {% if current_user.is_authenticated and (current_user.id == r.user_id or current_user.is_admin) %}
        <form method="post" action="{{ url_for('delete_review', review_id=r.id) }}" class="mt-2">
          <button class="btn btn-sm btn-outline-danger">Delete</button>
        </form>
        {% endif %}
      </div>
    </div>
    {% endfor %}
    {% else %}
    <p class="text-muted">No reviews yet. Be the first!</p>
    {% endif %}

    {% if current_user.is_authenticated %}
    <div class="card shadow-sm mt-3">
      <div class="card-header bg-light"><strong>Write a Review</strong></div>
      <div class="card-body">
        <form method="post" action="{{ url_for('add_review', product_id=product.id) }}">
          <div class="mb-3">
            <label class="form-label fw-bold">Rating</label>
            <select name="rating" class="form-select" required>
              <option value="5">★★★★★ Excellent</option>
              <option value="4">★★★★☆ Good</option>
              <option value="3">★★★☆☆ Average</option>
              <option value="2">★★☆☆☆ Poor</option>
              <option value="1">★☆☆☆☆ Very Poor</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Comment</label>
            <textarea name="comment" class="form-control" rows="3" placeholder="Share your experience..."></textarea>
          </div>
          <button type="submit" class="btn btn-dark">Submit Review</button>
        </form>
      </div>
    </div>
    {% else %}
    <a href="{{ url_for('login') }}" class="btn btn-outline-dark">Login to write a review</a>
    {% endif %}
  </div>
  <div class="col-md-4">
    <h5 class="fw-bold">Related Products</h5>
    {% for rp in related %}
    <a href="{{ url_for('product_detail', product_id=rp.id) }}" class="text-decoration-none">
      <div class="card mb-2 shadow-sm">
        <div class="card-body py-2">
          <p class="mb-0 fw-bold text-dark">{{ rp.name }}</p>
          <small class="text-success">Rs. {{ "%.0f"|format(rp.price) }}</small>
        </div>
      </div>
    </a>
    {% endfor %}
  </div>
</div>
{% endblock %}""")

@app.route('/shop')
def catalog():
    search   = request.args.get('q', '')
    cat_id   = request.args.get('cat', type=int)
    sort     = request.args.get('sort', 'newest')
    page     = request.args.get('page', 1, type=int)
    query    = Product.query
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    products   = query.paginate(page=page, per_page=6, error_out=False)
    categories = Category.query.all()
    return render_template_string(CATALOG_HTML, products=products, categories=categories,
                                  search=search, cat_id=cat_id, sort=sort)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(Product.category_id == product.category_id,
                                   Product.id != product.id).limit(4).all()
    return render_template_string(DETAIL_HTML, product=product, related=related)

# ============================================================
#  MODULE 3 — CART & ORDERS ROUTES
# ============================================================

CART_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}My Cart{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<h3 class="fw-bold mb-4"><i class="bi bi-cart3"></i> My Cart</h3>
{% if items %}
<form method="post" action="{{ url_for('update_cart') }}">
<div class="table-responsive">
<table class="table table-hover align-middle shadow-sm">
  <thead class="table-dark">
    <tr><th>Product</th><th>Price</th><th>Qty</th><th>Subtotal</th><th></th></tr>
  </thead>
  <tbody>
  {% for item in items %}
  <tr>
    <td><strong>{{ item.product.name }}</strong><br><small class="text-muted">{{ item.product.category.name }}</small></td>
    <td>Rs. {{ "%.0f"|format(item.product.price) }}</td>
    <td><input type="number" name="qty_{{ item.product.id }}" value="{{ item.qty }}" min="0" max="{{ item.product.stock }}" class="form-control form-control-sm" style="width:70px"></td>
    <td class="fw-bold text-success">Rs. {{ "%.0f"|format(item.subtotal) }}</td>
    <td><a href="{{ url_for('remove_from_cart', product_id=item.product.id) }}" class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></a></td>
  </tr>
  {% endfor %}
  </tbody>
</table>
</div>
<div class="d-flex justify-content-between align-items-center mt-3">
  <button type="submit" class="btn btn-outline-secondary">Update Cart</button>
  <div class="text-end">
    <h4 class="fw-bold">Total: <span class="text-success">Rs. {{ "%.0f"|format(total) }}</span></h4>
    <a href="{{ url_for('checkout') }}" class="btn btn-warning btn-lg"><i class="bi bi-credit-card"></i> Checkout</a>
  </div>
</div>
</form>
{% else %}
<div class="text-center py-5">
  <i class="bi bi-cart-x fs-1 text-muted"></i>
  <h5 class="mt-3 text-muted">Your cart is empty</h5>
  <a href="{{ url_for('catalog') }}" class="btn btn-warning mt-2">Start Shopping</a>
</div>
{% endif %}
{% endblock %}""")

CHECKOUT_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Checkout{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<h3 class="fw-bold mb-4"><i class="bi bi-credit-card"></i> Checkout</h3>
<div class="row">
  <div class="col-md-7">
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-dark text-white">Delivery Details</div>
      <div class="card-body">
        <form method="post">
          <div class="mb-3">
            <label class="form-label fw-bold">Name</label>
            <input class="form-control" value="{{ current_user.name }}" disabled>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Delivery Address *</label>
            <textarea name="address" class="form-control" rows="3" required
              placeholder="House #, Street, City...">{{ current_user.address or '' }}</textarea>
          </div>
          <button type="submit" class="btn btn-warning btn-lg w-100 fw-bold">
            <i class="bi bi-bag-check"></i> Place Order — Rs. {{ "%.0f"|format(total) }}
          </button>
        </form>
      </div>
    </div>
  </div>
  <div class="col-md-5">
    <div class="card shadow-sm">
      <div class="card-header bg-dark text-white">Order Summary</div>
      <div class="card-body p-0">
        <table class="table mb-0">
          {% for item in items %}
          <tr>
            <td>{{ item.product.name }} <small class="text-muted">x{{ item.qty }}</small></td>
            <td class="text-end fw-bold">Rs. {{ "%.0f"|format(item.subtotal) }}</td>
          </tr>
          {% endfor %}
          <tr class="table-warning">
            <td class="fw-bold fs-5">Total</td>
            <td class="text-end fw-bold fs-5">Rs. {{ "%.0f"|format(total) }}</td>
          </tr>
        </table>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

ORDERS_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}My Orders{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<h3 class="fw-bold mb-4"><i class="bi bi-box-seam"></i> My Orders</h3>
{% if orders %}
<table class="table table-hover shadow-sm align-middle">
  <thead class="table-dark">
    <tr><th>Order #</th><th>Date</th><th>Items</th><th>Total</th><th>Status</th><th>Action</th></tr>
  </thead>
  <tbody>
  {% for o in orders %}
  <tr>
    <td><strong>#{{ o.id }}</strong></td>
    <td>{{ o.created_at.strftime('%d %b %Y') }}</td>
    <td>{{ o.items|length }} item(s)</td>
    <td class="text-success fw-bold">Rs. {{ "%.0f"|format(o.total) }}</td>
    <td>
      {% if o.status=='Delivered' %}<span class="badge bg-success">{{ o.status }}</span>
      {% elif o.status=='Shipped' %}<span class="badge bg-info text-dark">{{ o.status }}</span>
      {% elif o.status=='Processing' %}<span class="badge bg-primary">{{ o.status }}</span>
      {% elif o.status=='Cancelled' %}<span class="badge bg-danger">{{ o.status }}</span>
      {% else %}<span class="badge bg-warning text-dark">{{ o.status }}</span>{% endif %}
    </td>
    <td><a href="{{ url_for('order_detail', order_id=o.id) }}" class="btn btn-sm btn-outline-dark">View</a></td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<div class="text-center py-5">
  <i class="bi bi-box fs-1 text-muted"></i>
  <h5 class="mt-3 text-muted">No orders yet</h5>
  <a href="{{ url_for('catalog') }}" class="btn btn-warning mt-2">Start Shopping</a>
</div>
{% endif %}
{% endblock %}""")

ORDER_DETAIL_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Order #{{ order.id }}{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h3 class="fw-bold"><i class="bi bi-receipt"></i> Order #{{ order.id }}</h3>
  <a href="{{ url_for('order_history') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left"></i> Back</a>
</div>
<div class="row">
  <div class="col-md-8">
    <div class="card shadow-sm mb-4">
      <div class="card-header bg-dark text-white">Order Items</div>
      <div class="card-body p-0">
        <table class="table mb-0">
          <thead class="table-light"><tr><th>Product</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr></thead>
          <tbody>
          {% for item in order.items %}
          <tr>
            <td><a href="{{ url_for('product_detail', product_id=item.product_id) }}" class="text-decoration-none fw-bold">{{ item.product.name }}</a></td>
            <td>{{ item.quantity }}</td>
            <td>Rs. {{ "%.0f"|format(item.price) }}</td>
            <td class="fw-bold text-success">Rs. {{ "%.0f"|format(item.price * item.quantity) }}</td>
          </tr>
          {% endfor %}
          </tbody>
          <tfoot class="table-warning">
            <tr><td colspan="3" class="fw-bold text-end">Total:</td><td class="fw-bold fs-5">Rs. {{ "%.0f"|format(order.total) }}</td></tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card shadow-sm">
      <div class="card-header bg-dark text-white">Order Info</div>
      <div class="card-body">
        <p><strong>Date:</strong> {{ order.created_at.strftime('%d %b %Y, %I:%M %p') }}</p>
        <p><strong>Status:</strong>
          {% if order.status=='Delivered' %}<span class="badge bg-success">{{ order.status }}</span>
          {% elif order.status=='Shipped' %}<span class="badge bg-info text-dark">{{ order.status }}</span>
          {% elif order.status=='Processing' %}<span class="badge bg-primary">{{ order.status }}</span>
          {% elif order.status=='Cancelled' %}<span class="badge bg-danger">{{ order.status }}</span>
          {% else %}<span class="badge bg-warning text-dark">{{ order.status }}</span>{% endif %}
        </p>
        <p><strong>Address:</strong><br>{{ order.address }}</p>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

@app.route('/cart')
def view_cart():
    cart  = get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            sub = p.price * qty
            total += sub
            items.append({'product': p, 'qty': qty, 'subtotal': sub})
    return render_template_string(CART_HTML, items=items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty     = int(request.form.get('quantity', 1))
    if product.stock < 1:
        flash('Sorry, out of stock.', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    cart = get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + qty
    save_cart(cart)
    flash(f'"{product.name}" added to cart!', 'success')
    return redirect(url_for('catalog'))

@app.route('/cart/remove/<int:product_id>')
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    flash('Item removed.', 'info')
    return redirect(url_for('view_cart'))

@app.route('/cart/update', methods=['POST'])
def update_cart():
    cart = get_cart()
    for key, val in request.form.items():
        if key.startswith('qty_'):
            pid = key.replace('qty_', '')
            qty = int(val)
            if qty <= 0:
                cart.pop(pid, None)
            else:
                cart[pid] = qty
    save_cart(cart)
    flash('Cart updated.', 'success')
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash('Cart is empty.', 'warning')
        return redirect(url_for('catalog'))
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.query.get(int(pid))
        if p:
            sub = p.price * qty
            total += sub
            items.append({'product': p, 'qty': qty, 'subtotal': sub})
    if request.method == 'POST':
        address = request.form.get('address', '').strip()
        if not address:
            flash('Please enter a delivery address.', 'danger')
            return render_template_string(CHECKOUT_HTML, items=items, total=total)
        order = Order(user_id=current_user.id, total=total, address=address)
        db.session.add(order)
        db.session.flush()
        for item in items:
            oi = OrderItem(order_id=order.id, product_id=item['product'].id,
                           quantity=item['qty'], price=item['product'].price)
            item['product'].stock -= item['qty']
            db.session.add(oi)
        db.session.commit()
        session.pop('cart', None)
        flash(f'Order #{order.id} placed successfully!', 'success')
        return redirect(url_for('order_detail', order_id=order.id))
    return render_template_string(CHECKOUT_HTML, items=items, total=total)

@app.route('/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template_string(ORDERS_HTML, orders=orders)

@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('order_history'))
    return render_template_string(ORDER_DETAIL_HTML, order=order)

# ============================================================
#  MODULE 4 — REVIEWS ROUTES
# ============================================================

@app.route('/review/add/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    Product.query.get_or_404(product_id)
    existing = Review.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        flash('You already reviewed this product.', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))
    rating  = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '').strip()
    if not (1 <= rating <= 5):
        flash('Invalid rating.', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))
    review = Review(user_id=current_user.id, product_id=product_id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    flash('Review submitted!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/review/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    pid    = review.product_id
    if review.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
    else:
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted.', 'info')
    return redirect(url_for('product_detail', product_id=pid))

# ============================================================
#  MODULE 5 — ADMIN ROUTES
# ============================================================

ADMIN_DASH_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Admin Dashboard{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h3 class="fw-bold"><i class="bi bi-speedometer2"></i> Admin Dashboard</h3>
  <span class="badge bg-warning text-dark fs-6">Admin Panel</span>
</div>
<div class="row g-3 mb-4">
  <div class="col-md-3">
    <div class="card border-0 bg-primary text-white text-center p-3 shadow-sm">
      <i class="bi bi-people fs-2"></i><h2 class="fw-bold">{{ stats.users }}</h2><p class="mb-0">Users</p>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 bg-success text-white text-center p-3 shadow-sm">
      <i class="bi bi-box-seam fs-2"></i><h2 class="fw-bold">{{ stats.products }}</h2><p class="mb-0">Products</p>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 bg-warning text-dark text-center p-3 shadow-sm">
      <i class="bi bi-bag-check fs-2"></i><h2 class="fw-bold">{{ stats.orders }}</h2><p class="mb-0">Orders</p>
    </div>
  </div>
  <div class="col-md-3">
    <div class="card border-0 bg-info text-dark text-center p-3 shadow-sm">
      <i class="bi bi-currency-rupee fs-2"></i><h2 class="fw-bold">{{ "%.0f"|format(stats.revenue) }}</h2><p class="mb-0">Revenue</p>
    </div>
  </div>
</div>
<div class="row g-3 mb-4">
  <div class="col-md-4"><a href="{{ url_for('admin_products') }}" class="btn btn-outline-dark w-100 py-2"><i class="bi bi-box"></i> Manage Products</a></div>
  <div class="col-md-4"><a href="{{ url_for('admin_orders') }}" class="btn btn-outline-dark w-100 py-2"><i class="bi bi-bag"></i> Manage Orders</a></div>
  <div class="col-md-4"><a href="{{ url_for('admin_users') }}" class="btn btn-outline-dark w-100 py-2"><i class="bi bi-people"></i> Manage Users</a></div>
</div>
<div class="card shadow-sm">
  <div class="card-header bg-dark text-white d-flex justify-content-between">
    <span><i class="bi bi-clock-history"></i> Recent Orders</span>
    <a href="{{ url_for('admin_orders') }}" class="btn btn-sm btn-warning">View All</a>
  </div>
  <div class="card-body p-0">
    <table class="table table-hover mb-0">
      <thead class="table-light"><tr><th>#</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th></tr></thead>
      <tbody>
      {% for o in recent_orders %}
      <tr>
        <td><strong>#{{ o.id }}</strong></td>
        <td>{{ o.user.name }}</td>
        <td class="text-success fw-bold">Rs. {{ "%.0f"|format(o.total) }}</td>
        <td>
          {% if o.status=='Delivered' %}<span class="badge bg-success">{{ o.status }}</span>
          {% elif o.status=='Shipped' %}<span class="badge bg-info text-dark">{{ o.status }}</span>
          {% elif o.status=='Processing' %}<span class="badge bg-primary">{{ o.status }}</span>
          {% elif o.status=='Cancelled' %}<span class="badge bg-danger">{{ o.status }}</span>
          {% else %}<span class="badge bg-warning text-dark">{{ o.status }}</span>{% endif %}
        </td>
        <td>{{ o.created_at.strftime('%d %b') }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}""")

ADMIN_PRODUCTS_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Manage Products{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h3 class="fw-bold"><i class="bi bi-box-seam"></i> Products</h3>
  <a href="{{ url_for('admin_add_product') }}" class="btn btn-warning"><i class="bi bi-plus-lg"></i> Add Product</a>
</div>
<div class="card shadow-sm">
  <div class="card-body p-0">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-dark"><tr><th>#</th><th>Name</th><th>Category</th><th>Price</th><th>Stock</th><th>Rating</th><th>Actions</th></tr></thead>
      <tbody>
      {% for p in products %}
      <tr>
        <td>{{ p.id }}</td>
        <td><strong>{{ p.name }}</strong></td>
        <td><span class="badge bg-secondary">{{ p.category.name }}</span></td>
        <td class="text-success fw-bold">Rs. {{ "%.0f"|format(p.price) }}</td>
        <td>
          {% if p.stock > 10 %}<span class="badge bg-success">{{ p.stock }}</span>
          {% elif p.stock > 0 %}<span class="badge bg-warning text-dark">{{ p.stock }}</span>
          {% else %}<span class="badge bg-danger">0</span>{% endif %}
        </td>
        <td>{{ p.avg_rating }}/5</td>
        <td>
          <a href="{{ url_for('admin_edit_product', product_id=p.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
          <form method="post" action="{{ url_for('admin_delete_product', product_id=p.id) }}" class="d-inline"
                onsubmit="return confirm('Delete this product?')">
            <button class="btn btn-sm btn-outline-danger">Delete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}""")

ADMIN_PRODUCT_FORM_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', "{% block title %}{{ 'Edit' if product else 'Add' }} Product{% endblock %}").replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-7">
    <div class="card shadow">
      <div class="card-header bg-dark text-white">
        <h5 class="mb-0">{{ 'Edit' if product else 'Add New' }} Product</h5>
      </div>
      <div class="card-body p-4">
        <form method="post">
          <div class="mb-3">
            <label class="form-label fw-bold">Product Name</label>
            <input type="text" name="name" class="form-control" value="{{ product.name if product else '' }}" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold">Description</label>
            <textarea name="description" class="form-control" rows="3">{{ product.description if product else '' }}</textarea>
          </div>
          <div class="row">
            <div class="col-md-6 mb-3">
              <label class="form-label fw-bold">Price (Rs.)</label>
              <input type="number" name="price" class="form-control" step="0.01" value="{{ product.price if product else '' }}" required>
            </div>
            <div class="col-md-6 mb-3">
              <label class="form-label fw-bold">Stock</label>
              <input type="number" name="stock" class="form-control" value="{{ product.stock if product else 0 }}" min="0">
            </div>
          </div>
          <div class="mb-4">
            <label class="form-label fw-bold">Category</label>
            <select name="category_id" class="form-select" required>
              {% for cat in categories %}
              <option value="{{ cat.id }}" {% if product and product.category_id==cat.id %}selected{% endif %}>{{ cat.name }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="d-flex gap-2">
            <button type="submit" class="btn btn-warning flex-grow-1 fw-bold">{{ 'Update' if product else 'Add' }} Product</button>
            <a href="{{ url_for('admin_products') }}" class="btn btn-outline-secondary">Cancel</a>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

ADMIN_ORDERS_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Manage Orders{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<h3 class="fw-bold mb-4"><i class="bi bi-bag-check"></i> All Orders</h3>
<div class="card shadow-sm">
  <div class="card-body p-0">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-dark"><tr><th>Order #</th><th>Customer</th><th>Total</th><th>Date</th><th>Status</th><th>Update</th></tr></thead>
      <tbody>
      {% for o in orders %}
      <tr>
        <td><a href="{{ url_for('order_detail', order_id=o.id) }}" class="fw-bold text-decoration-none">#{{ o.id }}</a></td>
        <td>{{ o.user.name }}<br><small class="text-muted">{{ o.user.email }}</small></td>
        <td class="text-success fw-bold">Rs. {{ "%.0f"|format(o.total) }}</td>
        <td>{{ o.created_at.strftime('%d %b %Y') }}</td>
        <td>
          {% if o.status=='Delivered' %}<span class="badge bg-success">{{ o.status }}</span>
          {% elif o.status=='Shipped' %}<span class="badge bg-info text-dark">{{ o.status }}</span>
          {% elif o.status=='Processing' %}<span class="badge bg-primary">{{ o.status }}</span>
          {% elif o.status=='Cancelled' %}<span class="badge bg-danger">{{ o.status }}</span>
          {% else %}<span class="badge bg-warning text-dark">{{ o.status }}</span>{% endif %}
        </td>
        <td>
          <form method="post" action="{{ url_for('admin_update_order', order_id=o.id) }}" class="d-flex gap-1">
            <select name="status" class="form-select form-select-sm" style="width:130px">
              {% for s in ['Pending','Processing','Shipped','Delivered','Cancelled'] %}
              <option value="{{ s }}" {% if o.status==s %}selected{% endif %}>{{ s }}</option>
              {% endfor %}
            </select>
            <button class="btn btn-sm btn-warning">Update</button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}""")

ADMIN_USERS_HTML = BASE.replace('{% block title %}ShopSmart{% endblock %}', '{% block title %}Manage Users{% endblock %}').replace(
    '{% block content %}{% endblock %}', """
{% block content %}
<h3 class="fw-bold mb-4"><i class="bi bi-people"></i> All Users</h3>
<div class="card shadow-sm">
  <div class="card-body p-0">
    <table class="table table-hover align-middle mb-0">
      <thead class="table-dark"><tr><th>#</th><th>Name</th><th>Email</th><th>Phone</th><th>Orders</th><th>Role</th><th>Joined</th></tr></thead>
      <tbody>
      {% for u in users %}
      <tr>
        <td>{{ u.id }}</td>
        <td><strong>{{ u.name }}</strong></td>
        <td>{{ u.email }}</td>
        <td>{{ u.phone or '—' }}</td>
        <td><span class="badge bg-secondary">{{ u.orders|length }}</span></td>
        <td>
          {% if u.is_admin %}<span class="badge bg-warning text-dark">Admin</span>
          {% else %}<span class="badge bg-primary">Customer</span>{% endif %}
        </td>
        <td>{{ u.created_at.strftime('%d %b %Y') }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}""")

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'users':    User.query.count(),
        'products': Product.query.count(),
        'orders':   Order.query.count(),
        'revenue':  db.session.query(db.func.sum(Order.total)).scalar() or 0,
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    return render_template_string(ADMIN_DASH_HTML, stats=stats, recent_orders=recent_orders)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template_string(ADMIN_PRODUCTS_HTML, products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_product():
    categories = Category.query.all()
    if request.method == 'POST':
        p = Product(
            name=request.form['name'],
            description=request.form.get('description', ''),
            price=float(request.form['price']),
            stock=int(request.form.get('stock', 0)),
            category_id=int(request.form['category_id'])
        )
        db.session.add(p)
        db.session.commit()
        flash('Product added!', 'success')
        return redirect(url_for('admin_products'))
    return render_template_string(ADMIN_PRODUCT_FORM_HTML, categories=categories, product=None)

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_product(product_id):
    product    = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    if request.method == 'POST':
        product.name        = request.form['name']
        product.description = request.form.get('description', '')
        product.price       = float(request.form['price'])
        product.stock       = int(request.form.get('stock', 0))
        product.category_id = int(request.form['category_id'])
        db.session.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    return render_template_string(ADMIN_PRODUCT_FORM_HTML, product=product, categories=categories)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template_string(ADMIN_ORDERS_HTML, orders=orders)

@app.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_order(order_id):
    order        = Order.query.get_or_404(order_id)
    order.status = request.form.get('status', order.status)
    db.session.commit()
    flash(f'Order #{order.id} updated to {order.status}.', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template_string(ADMIN_USERS_HTML, users=users)

# ============================================================
#  DATABASE SEED (Sample Data)
# ============================================================

def seed_data():
    if Category.query.count() == 0:
        cats = [
            Category(name='Electronics'),
            Category(name='Clothing'),
            Category(name='Books'),
            Category(name='Home & Kitchen'),
        ]
        db.session.add_all(cats)
        db.session.commit()

        products = [
            Product(name='Wireless Headphones', price=4999, stock=25, category_id=1,
                    description='Premium sound quality with 40hr battery life.'),
            Product(name='Laptop Stand',        price=1499, stock=50, category_id=1,
                    description='Adjustable aluminum stand for all laptops.'),
            Product(name='Python Programming',  price=999,  stock=30, category_id=3,
                    description='Complete Python guide for beginners.'),
            Product(name='Cotton T-Shirt',      price=599,  stock=100, category_id=2,
                    description='Soft 100% cotton, all sizes available.'),
            Product(name='Coffee Mug',          price=349,  stock=75, category_id=4,
                    description='Ceramic mug, keeps coffee warm 2 hours.'),
            Product(name='Bluetooth Speaker',   price=2499, stock=20, category_id=1,
                    description='Waterproof portable speaker, 12hr battery.'),
        ]
        db.session.add_all(products)

        admin = User(
            name='Admin',
            email='admin@shopsmart.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Sample data seeded!")

# ============================================================
#  RUN
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    print("🚀 ShopSmart running at http://127.0.0.1:5000")
    print("👤 Admin login: admin@shopsmart.com / admin123")
    app.run(debug=True)
