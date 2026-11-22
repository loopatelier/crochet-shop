import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "the-loop-atelier-super-secret-key-2026")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "atelier.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subtitle = db.Column(db.String(200), default="100% Combed Cotton")
    category = db.Column(db.String(80), default="Wearables & Keepsakes")
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=3)
    visible = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300), default="")
    description = db.Column(db.Text, default="")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120), default="")
    instagram = db.Column(db.String(100), default="")
    address = db.Column(db.Text, nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    shipping = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)
    utr = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="Pending Verification")
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d %b %Y, %I:%M %p"))

class CustomInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(120), nullable=False)
    item_type = db.Column(db.String(120), nullable=False)
    colors = db.Column(db.String(150), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d %b %Y"))

class StoreSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(120), default="admin@loopatelier.com")
    password_hash = db.Column(db.String(256), nullable=False)
    upi_id = db.Column(db.String(120), default="9480178844@ibl")
    upi_name = db.Column(db.String(120), default="Ayesha")
    qr_image_url = db.Column(db.String(300), default="/static/upi_qr.jpeg")
    shipping_fee = db.Column(db.Float, default=70.0)
    free_shipping_above = db.Column(db.Float, default=1200.0)

def save_uploaded_file(file_obj):
    if not file_obj or file_obj.filename == "":
        return None
    filename = secure_filename(f"{int(datetime.now().timestamp())}_{file_obj.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file_obj.save(filepath)
    return f"/static/uploads/{filename}"

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# --- INITIALIZE DEFAULT DATA ---
with app.app_context():
    db.create_all()
    if not StoreSettings.query.first():
        default_settings = StoreSettings(
            admin_email="admin@loopatelier.com",
            password_hash=generate_password_hash("atelier2026"),
            upi_id="9480178844@ibl",
            upi_name="Ayesha",
            shipping_fee=70.0,
            free_shipping_above=1200.0
        )
        db.session.add(default_settings)
        db.session.commit()

    if Product.query.count() == 0:
        sample_products = [
            Product(
                name="Meadow Granny Square Tote",
                subtitle="Combed Organic Cotton",
                category="Wearables & Keepsakes",
                price=850,
                stock=4,
                visible=True,
                image_url="https://images.unsplash.com/photo-1615486511484-92e172cc4fe0?auto=format&fit=crop&w=800&q=80",
                description="Hand-stitched vintage floral granny squares joined with sturdy braided shoulder straps."
            ),
            Product(
                name="Pastel Lavender Lily Bouquet",
                subtitle="Everlasting Crochet Florals",
                category="Bouquets & Bags",
                price=680,
                stock=6,
                visible=True,
                image_url="https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=800&q=80",
                description="Delicate soft-lilac lilies wrapped in Korean kraft paper with satin ribbon."
            ),
            Product(
                name="Sleepy Snorlax Amigurumi Plush",
                subtitle="Velvet Chenille Yarn",
                category="Amigurumi & Key Charms",
                price=790,
                stock=2,
                visible=True,
                image_url="https://images.unsplash.com/photo-1618842676088-c4d48a6a7c9d?auto=format&fit=crop&w=800&q=80",
                description="Plush, ultra-soft handmade companion crocheted in plush velvet yarn."
            ),
            Product(
                name="Botanical Daisy Book Sleeve",
                subtitle="Padded Cotton Yarn",
                category="Book & Pet Accessories",
                price=520,
                stock=5,
                visible=True,
                image_url="https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80",
                description="Cushioned crochet sleeve with a wooden button closure to keep paperbacks safe."
            )
        ]
        db.session.bulk_save_objects(sample_products)
        db.session.commit()

# --- PUBLIC CUSTOMER ROUTES (NO ADMIN LINKS ANYWHERE) ---
@app.route("/")
def index():
    products = Product.query.filter_by(visible=True).all()
    settings = StoreSettings.query.first()
    return render_template("index.html", products=products, settings=settings)

@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data or not data.get("items") or not data.get("utr"):
        return jsonify({"error": "Missing required order details"}), 400

    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d')}-{Order.query.count() + 101}"
    new_order = Order(
        invoice_no=invoice_no,
        customer_name=data["customer_name"],
        phone=data["phone"],
        email=data.get("email", ""),
        instagram=data.get("instagram", ""),
        address=data["address"],
        items_json=json.dumps(data["items"]),
        subtotal=float(data["subtotal"]),
        shipping=float(data["shipping"]),
        total=float(data["total"]),
        utr=data["utr"].strip()
    )
    db.session.add(new_order)

    # Deduct stock automatically
    for item in data["items"]:
        prod = Product.query.get(item["id"])
        if prod and prod.stock > 0:
            prod.stock = max(0, prod.stock - int(item["qty"]))

    db.session.commit()
    return jsonify({
        "success": True,
        "invoice_no": invoice_no,
        "created_at": new_order.created_at
    })

@app.route("/api/custom-inquiry", methods=["POST"])
def create_custom_inquiry():
    data = request.get_json()
    inquiry = CustomInquiry(
        name=data.get("name", ""),
        contact=data.get("contact", ""),
        item_type=data.get("item_type", ""),
        colors=data.get("colors", ""),
        notes=data.get("notes", "")
    )
    db.session.add(inquiry)
    db.session.commit()
    return jsonify({"success": True})

# --- PRIVATE ADMIN ROUTES (ONLY ACCESSIBLE BY DIRECT URL) ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        settings = StoreSettings.query.first()
        if email == settings.admin_email and check_password_hash(settings.password_hash, password):
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid studio credentials."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    orders_raw = Order.query.order_by(Order.id.desc()).all()
    orders = []
    for o in orders_raw:
        orders.append({
            "obj": o,
            "items": json.loads(o.items_json)
        })
    inquiries = CustomInquiry.query.order_by(CustomInquiry.id.desc()).all()
    settings = StoreSettings.query.first()

    active_products = sum(1 for p in products if p.visible)
    pending_orders = sum(1 for o in orders_raw if o.status == "Pending Verification")
    unique_customers = len(set(o.phone.strip() for o in orders_raw))
    total_revenue = sum(o.total for o in orders_raw if o.status != "Cancelled")

    return render_template(
        "admin_dashboard.html",
        products=products,
        orders=orders,
        inquiries=inquiries,
        settings=settings,
        active_products=active_products,
        pending_orders=pending_orders,
        unique_customers=unique_customers,
        total_revenue=total_revenue
    )

@app.route("/admin/product/save", methods=["POST"])
@admin_required
def save_product():
    prod_id = request.form.get("id")
    uploaded_url = save_uploaded_file(request.files.get("image_file"))
    image_url = uploaded_url or request.form.get("image_url", "").strip()

    if prod_id:
        prod = Product.query.get_or_404(int(prod_id))
        prod.name = request.form.get("name")
        prod.subtitle = request.form.get("subtitle")
        prod.category = request.form.get("category")
        prod.price = float(request.form.get("price", 0))
        prod.stock = int(request.form.get("stock", 0))
        prod.visible = request.form.get("visible") == "true"
        prod.description = request.form.get("description", "")
        if image_url:
            prod.image_url = image_url
    else:
        prod = Product(
            name=request.form.get("name"),
            subtitle=request.form.get("subtitle", "100% Combed Cotton"),
            category=request.form.get("category", "Wearables & Keepsakes"),
            price=float(request.form.get("price", 0)),
            stock=int(request.form.get("stock", 1)),
            visible=request.form.get("visible") == "true",
            image_url=image_url or "https://images.unsplash.com/photo-1615486511484-92e172cc4fe0?auto=format&fit=crop&w=800&q=80",
            description=request.form.get("description", "")
        )
        db.session.add(prod)

    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/product/delete/<int:prod_id>", methods=["POST"])
@admin_required
def delete_product(prod_id):
    prod = Product.query.get_or_404(prod_id)
    db.session.delete(prod)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/order/status/<int:order_id>", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get("status", order.status)
    db.session.commit()
    return redirect(url_for("admin_dashboard") + "#orders")

@app.route("/admin/settings", methods=["POST"])
@admin_required
def update_settings():
    settings = StoreSettings.query.first()
    settings.upi_id = request.form.get("upi_id", settings.upi_id).strip()
    settings.upi_name = request.form.get("upi_name", settings.upi_name).strip()
    settings.shipping_fee = float(request.form.get("shipping_fee", settings.shipping_fee))
    settings.free_shipping_above = float(request.form.get("free_shipping_above", settings.free_shipping_above))

    qr_url = save_uploaded_file(request.files.get("qr_file"))
    if qr_url:
        settings.qr_image_url = qr_url

    new_pass = request.form.get("new_password", "").strip()
    if new_pass:
        settings.password_hash = generate_password_hash(new_pass)

    db.session.commit()
    return redirect(url_for("admin_dashboard") + "#settings")

if __name__ == "__main__":
    app.run(debug=True)