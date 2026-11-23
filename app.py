import os
import re
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

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


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
    gallery_images_json = db.Column(db.Text, default="[]")
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
    reference_image_url = db.Column(db.String(300), default="")
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime("%d %b %Y"))


class StoreSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(120), default="admin@loopatelier.com")
    password_hash = db.Column(db.String(256), nullable=False)
    upi_id = db.Column(db.String(120), default="theloopatelier@upi")
    upi_name = db.Column(db.String(120), default="Ayesha")
    qr_image_url = db.Column(db.String(300), default="/static/upi_qr.jpeg")
    shipping_fee = db.Column(db.Float, default=70.0)
    free_shipping_above = db.Column(db.Float, default=999.0)


def save_uploaded_file(file_obj):
    if not file_obj or not file_obj.filename:
        return None
    ext = os.path.splitext(file_obj.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
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
            upi_id="theloopatelier@upi",
            upi_name="Ayesha",
            qr_image_url="/static/upi_qr.jpeg",
            shipping_fee=70.0,
            free_shipping_above=999.0
        )
        db.session.add(default_settings)
        db.session.commit()

    if Product.query.count() == 0:
        sample_products = [
            Product(
                name="Strawberry Bag Charm",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=75,
                stock=4,
                visible=True,
                image_url="/static/cro2.jpeg",
                gallery_images_json="[]",
                description="A tiny Strawberry & Daisy charm - soft & cute."
            ),
            Product(
                name="Daisy Keychain",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=75,
                stock=6,
                visible=True,
                image_url="/static/cro3.jpeg",
                gallery_images_json="[]",
                description="A soft Daisy Keychain with a yellow centre."
            ),
            Product(
                name="Heart Keychain",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=100,
                stock=3,
                visible=True,
                image_url="/static/cro4.jpeg",
                gallery_images_json="[]",
                description="Red heart keychain."
            ),
            Product(
                name="Bouquet",
                subtitle="Acrylic Yarn",
                category="Bouquets & Bags",
                price=1200,
                stock=5,
                visible=True,
                image_url="/static/cro6.jpeg",
                gallery_images_json="[]",
                description="A lilac lilly bouquet ."
            ),
            Product(
                name="F1 Keychain",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=100,
                stock=5,
                visible=True,
                image_url="/static/f1.jpeg",
                gallery_images_json="[]",
                description="F1 kechain with tassel."
            ),
            Product(
                name="Letter keychain",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=130,
                stock=5,
                visible=True,
                image_url="/static/letter.jpeg",
                gallery_images_json="[]",
                description="A letter and kitty keychain set with pearls."
            ),
             Product(
                name="Rose Bag",
                subtitle="Acrylic Yarn",
                category="Bouquets & Bags",
                price=1299,
                stock=5,
                visible=True,
                image_url="/static/rose1.jpeg",
                gallery_images_json="[/static/rose2.jpeg]",
                description="A deep red rose bag with a pearl strap."
            ),
             Product(
                name="Hanging Spiderman ",
                subtitle="Acrylic Yarn",
                category="Amigurumi & Key Charms",
                price=175,
                stock=5,
                visible=True,
                image_url="/static/spiderman.jpeg",
                gallery_images_json="[]",
                description="A tiny spider hero plush."
            ),
             Product(
                name="Frog pet hat",
                subtitle="Acrylic Yarn",
                category="Book & Pet Accessories",
                price=230,
                stock=5,
                visible=True,
                image_url="/static/cat0.1.jpeg",
                gallery_images_json="[/static/cat0.jpeg]",
                description="A green frog hat for pets."
            ),
            Product(
                name="Strawberry pet hat",
                subtitle="Acrylic Yarn",
                category="Book & Pet Accessories",
                price=230,
                stock=5,
                visible=True,
                image_url="/static/cat1.0.jpeg",
                gallery_images_json="[/static/cat1.jpeg]",
                description="A red strawberry hat for pets."
            ),
            Product(
                name="Pink pet hat",
                subtitle="Acrylic Yarn",
                category="Book & Pet Accessories",
                price=120,
                stock=5,
                visible=True,
                image_url="/static/cat2.0.jpeg",
                gallery_images_json="[/static/cat2.jpeg]",
                description="A pink flower hat for pets."
            ),
            Product(
                name="Book cover with book mark",
                subtitle="Acrylic Yarn",
                category="Book & Pet Accessories",
                price=450,
                stock=2,
                visible=True,
                image_url="/static/cover0.jpeg",
                gallery_images_json="[/static/cover1.jpeg]",
                description="A brown book cover with white daisies."
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
    data = request.get_json(silent=True) or {}
    customer_name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    instagram = (data.get("instagram") or "").strip()
    address = (data.get("address") or "").strip()
    utr = (data.get("utr") or "").strip()
    items = data.get("items") or []

    if not customer_name or not phone or not address or not utr:
        return jsonify({"success": False, "error": "Please fill in all required fields."}), 400

    if not re.fullmatch(r"[A-Za-z0-9]{8,24}", utr):
        return jsonify({"success": False, "error": "Please enter a valid UPI UTR / transaction ID (8–24 letters/numbers)."}), 400

    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"success": False, "error": "Your basket is empty."}), 400

    settings = StoreSettings.query.first()
    shipping_fee = float(settings.shipping_fee) if settings else 70.0
    free_above = float(settings.free_shipping_above) if settings else 999.0

    subtotal = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
    shipping = 0.0 if subtotal == 0 or subtotal >= free_above else shipping_fee
    total = subtotal + shipping
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    new_order = Order(
        invoice_no=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-TEMP",
        customer_name=customer_name,
        phone=phone,
        email=email,
        instagram=instagram,
        address=address,
        items_json=json.dumps(items),
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        utr=utr,
        created_at=now_str,
    )
    db.session.add(new_order)
    db.session.flush()
    new_order.invoice_no = f"INV-{datetime.now().strftime('%Y%m%d')}-{new_order.id + 100}"

    for item in items:
        prod = Product.query.get(item.get("id"))
        if prod and prod.stock > 0:
            prod.stock = max(0, prod.stock - int(item.get("qty", 1)))

    db.session.commit()
    return jsonify({
        "success": True,
        "invoice_no": new_order.invoice_no,
        "created_at": new_order.created_at
    })


@app.route("/api/custom-inquiry", methods=["POST"])
def create_custom_inquiry():
    if request.content_type and "multipart/form-data" in request.content_type:
        ref_url = save_uploaded_file(request.files.get("reference_image")) or ""
        inquiry = CustomInquiry(
            name=(request.form.get("name") or "").strip(),
            contact=(request.form.get("contact") or "").strip(),
            item_type=(request.form.get("item_type") or "").strip(),
            colors=(request.form.get("colors") or "").strip(),
            notes=(request.form.get("notes") or "").strip(),
            reference_image_url=ref_url,
        )
    else:
        data = request.get_json(silent=True) or {}
        inquiry = CustomInquiry(
            name=(data.get("name") or "").strip(),
            contact=(data.get("contact") or "").strip(),
            item_type=(data.get("item_type") or "").strip(),
            colors=(data.get("colors") or "").strip(),
            notes=(data.get("notes") or "").strip(),
        )

    if not inquiry.name or not inquiry.contact or not inquiry.item_type:
        return jsonify({"success": False, "error": "Please provide your name, contact, and item idea."}), 400

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
        if settings and email == settings.admin_email and check_password_hash(settings.password_hash, password):
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
        try:
            parsed_items = json.loads(o.items_json or "[]")
        except Exception:
            parsed_items = []
        orders.append({
            "obj": o,
            "items": parsed_items
        })
    inquiries = CustomInquiry.query.order_by(CustomInquiry.id.desc()).all()
    settings = StoreSettings.query.first()

    active_products = sum(1 for p in products if p.visible)
    pending_orders = sum(1 for o in orders_raw if o.status == "Pending Verification")
    unique_customers = len(set(o.phone.strip() for o in orders_raw if o.phone))
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

    extra_files = request.files.getlist("gallery_files")
    extra_urls = [u for f in extra_files if (u := save_uploaded_file(f))]

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
        if extra_urls:
            prod.gallery_images_json = json.dumps(extra_urls)
    else:
        prod = Product(
            name=request.form.get("name"),
            subtitle=request.form.get("subtitle", "100% Combed Cotton"),
            category=request.form.get("category", "Wearables & Keepsakes"),
            price=float(request.form.get("price", 0)),
            stock=int(request.form.get("stock", 1)),
            visible=request.form.get("visible") == "true",
            image_url=image_url or "https://images.unsplash.com/photo-1615486511484-92e172cc4fe0?auto=format&fit=crop&w=800&q=80",
            gallery_images_json=json.dumps(extra_urls),
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