import json
import os
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "crochet-studio-secret-key-2026")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crochet_shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Change these credentials (or set ADMIN_USER / ADMIN_PASS environment variables)
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "yarnstudio123")

db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    fiber = db.Column(db.String(100), nullable=False)
    badge = db.Column(db.String(50), default="Ready to Ship")
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "fiber": self.fiber,
            "badge": self.badge,
            "description": self.description,
            "image": self.image_url,
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommissionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    project_type = db.Column(db.String(80), nullable=False)
    yarn_color = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="New Inquiry")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== SESSION LOGIN FOR /admin ====================

def requires_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== SEED INITIAL PRODUCTS ====================

def seed_database():
    if Product.query.first() is None:
        sample_products = [
            Product(
                name="Barnaby the Chunky Bear",
                category="amigurumi",
                price=48.00,
                fiber="100% Velvet Chenille",
                badge="Ready to Ship",
                description="Hand-crocheted plush bear with safety eyes and ultra-soft velvet yarn.",
                image_url="https://images.unsplash.com/photo-1615486511484-92e172cc4fe0?auto=format&fit=crop&w=800&q=80",
            ),
            Product(
                name="Heirloom Waffle Throw",
                category="blankets",
                price=145.00,
                fiber="Merino Wool Blend",
                badge="Made to Order",
                description="Textured waffle-stitch throw blanket in warm oatmeal cream.",
                image_url="https://images.unsplash.com/photo-1584992236310-6edddc08acff?auto=format&fit=crop&w=800&q=80",
            ),
            Product(
                name="Meadow Granny Square Tote",
                category="wearables",
                price=62.00,
                fiber="Combed Organic Cotton",
                badge="1 Left",
                description="Sturdy floral granny square shoulder bag lined with unbleached cotton.",
                image_url="https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=800&q=80",
            ),
        ]
        db.session.bulk_save_objects(sample_products)
        db.session.commit()

# ==================== ROUTES & API ENDPOINTS ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    if not data.get('items'):
        return jsonify({"error": "Cart is empty"}), 400

    new_order = Order(
        customer_name=data.get('name', 'Guest Customer'),
        customer_email=data.get('email', 'Not provided'),
        items_json=json.dumps(data['items']),
        total_amount=float(data.get('total', 0)),
    )
    db.session.add(new_order)
    db.session.commit()

    return jsonify({
        "message": "Order received! We will send your confirmation shortly.",
        "order_id": new_order.id,
    }), 201

@app.route('/api/commissions', methods=['POST'])
def create_commission():
    data = request.get_json() or {}
    if not data.get('email'):
        return jsonify({"error": "Email is required"}), 400

    commission = CommissionRequest(
        name=data.get('name', 'Guest'),
        email=data.get('email'),
        project_type=data.get('project_type', 'Custom Piece'),
        yarn_color=data.get('yarn_color', 'Natural Cream'),
        details=data.get('details', ''),
    )
    db.session.add(commission)
    db.session.commit()

    return jsonify({
        "message": "Commission inquiry saved! Expect a reply within 24 hours.",
        "inquiry_id": commission.id,
    }), 201

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    error = ""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = "Invalid username or password."

    return f"""
    <html>
    <head><title>Admin Login</title></head>
    <body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #FAF6F0;">
        <form method="POST" style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); width: 320px; display: grid; gap: 12px;">
            <h2 style="margin: 0;">Studio Admin Login</h2>
            <p style="color: #b91c1c; margin: 0;">{error}</p>
            <input type="text" name="username" placeholder="Username" required style="padding: 8px;" />
            <input type="password" name="password" placeholder="Password" required style="padding: 8px;" />
            <button type="submit" style="padding: 10px; background: #C86D51; color: white; border: none; border-radius: 6px; cursor: pointer;">Log In</button>
        </form>
    </body>
    </html>
    """

@app.route('/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@requires_admin_auth
def admin_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    commissions = CommissionRequest.query.order_by(CommissionRequest.created_at.desc()).all()

    html = """
    <div style="font-family: sans-serif; max-width: 800px; margin: 2rem auto;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>Studio Orders & Commissions</h1>
            <a href="/logout">Log Out</a>
        </div>
        <h2>Orders</h2><ul>
    """
    for o in orders:
        html += (
            f"<li><strong>#{o.id}</strong> - {o.customer_name} ({o.customer_email}) "
            f"| Total: ${o.total_amount:.2f} | Items: {o.items_json}</li>"
        )
    html += "</ul><h2>Custom Commissions</h2><ul>"
    for c in commissions:
        html += (
            f"<li><strong>#{c.id}</strong> - {c.name} ({c.email}) "
            f"| {c.project_type} in {c.yarn_color}: {c.details}</li>"
        )
    html += "</ul></div>"
    return html

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)