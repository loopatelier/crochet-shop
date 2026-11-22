import os
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Use DATABASE_URL if provided (e.g., Postgres), otherwise local SQLite
database_url = os.environ.get("DATABASE_URL", "sqlite:///crochet_shop.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

db = SQLAlchemy(app)

ORDER_STATUSES = [
    "Pending Verification",
    "Payment Verified",
    "Crafting",
    "Shipped",
    "Delivered",
    "Cancelled",
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_safe_image_url(url):
    if not url:
        return False
    if url.startswith("/"):
        return True
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}


def save_uploaded_image(file_storage, prefix="item"):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Unsupported image format. Please use JPG, PNG, WEBP, or GIF.")
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    safe_base = secure_filename(file_storage.filename.rsplit(".", 1)[0]) or prefix
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{prefix}_{safe_base}_{stamp}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(filepath)
    return f"/static/uploads/{filename}"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    subtitle = db.Column(db.String(140), nullable=False, default="100% Combed Cotton")
    category = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=5)
    fiber = db.Column(db.String(120), nullable=False, default="100% Combed Cotton")
    badge = db.Column(db.String(60), nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    visible = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def active(self):
        return self.visible

    @active.setter
    def active(self, val):
        self.visible = bool(val)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle,
            "category": self.category,
            "price": self.price,
            "stock": self.stock,
            "fiber": self.fiber,
            "badge": self.badge,
            "description": self.description,
            "image_url": self.image_url,
            "visible": self.visible,
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), nullable=False, default="")
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    instagram = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(160), nullable=True)
    address = db.Column(db.Text, nullable=False)
    utr = db.Column(db.String(120), nullable=False)
    items_json = db.Column(db.Text, nullable=False, default="[]")
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    shipping = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(40), nullable=False, default="Pending Verification")
    created_at = db.Column(db.String(60), nullable=False, default="")


class CommissionInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(160), nullable=False)
    item_type = db.Column(db.String(140), nullable=False)
    colors = db.Column(db.String(140), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.String(60), nullable=False, default="")


class StoreSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(160), nullable=False, default="admin@theloopatelier.com")
    password_hash = db.Column(db.String(255), nullable=True)
    upi_id = db.Column(db.String(120), nullable=False, default="theloopatelier@upi")
    upi_name = db.Column(db.String(120), nullable=False, default="The Loop Atelier")
    qr_image_url = db.Column(db.String(255), nullable=True)
    shipping_fee = db.Column(db.Float, nullable=False, default=80.0)
    free_shipping_above = db.Column(db.Float, nullable=False, default=2500.0)


def get_store_settings():
    setting = StoreSetting.query.first()
    if not setting:
        setting = StoreSetting(
            admin_email=(
                os.environ.get("ADMIN_USER")
                or os.environ.get("ADMIN_EMAIL")
                or "admin@theloopatelier.com"
            ),
            upi_id="theloopatelier@upi",
            upi_name="The Loop Atelier",
            qr_image_url="/static/upi_qr.jpeg",
            shipping_fee=80.0,
            free_shipping_above=2500.0,
        )
        db.session.add(setting)
        db.session.commit()
    return setting


def seed_products():
    if Product.query.first() is not None:
        return

    initial_products = [
        Product(
            name="Strawberry Bag Charm",
            subtitle="Soft Cotton & Milk Yarn",
            category="Amigurumi & Plush",
            price=450.00,
            stock=10,
            fiber="Soft Cotton & Milk Yarn",
            badge="Bestseller",
            description="Handcrafted crochet strawberry keepsake for bags, keys, and pouches.",
            image_url="/static/cro2.jpeg",
            visible=True,
        ),
        Product(
            name="Daisy Keychain",
            subtitle="100% Velvet Chenille",
            category="Floral & Keepsakes",
            price=350.00,
            stock=12,
            fiber="100% Velvet Chenille",
            badge="Ready to Ship",
            description="Charming textured daisy keychain crocheted stitch by stitch with soft yarn.",
            image_url="/static/cro3.jpeg",
            visible=True,
        ),
        Product(
            name="Heirloom Waffle Throw",
            subtitle="Merino Wool Blend",
            category="Wearables & Bags",
            price=2450.00,
            stock=4,
            fiber="Merino Wool Blend",
            badge="Made to Order",
            description="Deeply textured waffle-stitch throw blanket in warm oatmeal cream.",
            image_url="/static/cro4.jpeg",
            visible=True,
        ),
        Product(
            name="Meadow Granny Square Tote",
            subtitle="Mercerized Cotton",
            category="Wearables & Bags",
            price=1250.00,
            stock=6,
            fiber="Mercerized Cotton",
            badge="New",
            description="Structured handmade granny square tote bag for everyday outings.",
            image_url="/static/cro5.jpeg",
            visible=True,
        ),
        Product(
            name="Mini Charm & Keychain Trio",
            subtitle="Fine Yarn & Beaded Accents",
            category="Book & Pet Accessories",
            price=650.00,
            stock=8,
            fiber="Fine Yarn & Beaded Accents",
            badge="Limited",
            description="Playful handmade charms for bags, keys, and phone straps.",
            image_url="/static/cro6.jpeg",
            visible=True,
        ),
    ]

    db.session.add_all(initial_products)
    db.session.commit()


def init_db():
    try:
        db.create_all()
        get_store_settings()
        seed_products()
    except Exception as exc:
        app.logger.error("Database init error: %s", exc)


init_db()


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/")
def index():
    products = Product.query.filter_by(visible=True).order_by(Product.id.asc()).all()
    settings = get_store_settings()
    default_qr_url = settings.qr_image_url or "/static/upi_qr.jpeg"
    return render_template(
        "index.html",
        products=products,
        settings=settings,
        default_qr_url=default_qr_url,
    )


@app.route("/api/orders", methods=["POST"])
def create_order():
    import json

    data = request.get_json(silent=True) or {}
    customer_name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    instagram = (data.get("instagram") or "").strip()
    email = (data.get("email") or "").strip()
    address = (data.get("address") or "").strip()
    utr = (data.get("utr") or "").strip()
    items = data.get("items") or []

    if not customer_name or not phone or not address or not utr:
        return jsonify({"success": False, "error": "Please fill in all required fields."}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"success": False, "error": "Your basket is empty."}), 400

    settings = get_store_settings()
    subtotal = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
    shipping = 0.0 if subtotal == 0 or subtotal >= float(settings.free_shipping_above) else float(settings.shipping_fee)
    total = subtotal + shipping
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    order = Order(
        customer_name=customer_name,
        phone=phone,
        instagram=instagram or None,
        email=email or None,
        address=address,
        utr=utr,
        items_json=json.dumps(items),
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        status="Pending Verification",
        created_at=now_str,
    )
    db.session.add(order)
    db.session.flush()
    order.invoice_no = f"TLA-{datetime.now().strftime('%Y%m%d')}-{order.id:04d}"
    db.session.commit()

    return jsonify({
        "success": True,
        "order_id": order.id,
        "invoice_no": order.invoice_no,
        "created_at": order.created_at,
        "subtotal": order.subtotal,
        "shipping": order.shipping,
        "total": order.total,
    }), 201


@app.route("/api/custom-inquiry", methods=["POST"])
def create_custom_inquiry():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    contact = (data.get("contact") or "").strip()
    item_type = (data.get("item_type") or "").strip()
    colors = (data.get("colors") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not name or not contact or not item_type:
        return jsonify({"success": False, "error": "Please complete required fields."}), 400

    inq = CommissionInquiry(
        name=name,
        contact=contact,
        item_type=item_type,
        colors=colors or None,
        notes=notes or None,
        created_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
    )
    db.session.add(inq)
    db.session.commit()
    return jsonify({"success": True, "id": inq.id}), 201


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    settings = get_store_settings()
    admin_user = (
        os.environ.get("ADMIN_USER")
        or os.environ.get("ADMIN_EMAIL")
        or settings.admin_email
        or "admin@theloopatelier.com"
    ).strip().lower()
    admin_pass_plain = (
        os.environ.get("ADMIN_PASS")
        or os.environ.get("ADMIN_PASSWORD")
        or "atelier123"
    )

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        valid_pass = (
            check_password_hash(settings.password_hash, password)
            if settings.password_hash
            else password == admin_pass_plain
        )
        if email == admin_user and valid_pass:
            session["admin_logged_in"] = True
            session["admin_email"] = email
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin email or password.", "error")

    return render_template("admin_login.html", settings=settings)


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_email", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@app.route("/admin/dashboard")
def admin_dashboard():
    import json

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    settings = get_store_settings()
    default_qr_url = settings.qr_image_url or "/static/upi_qr.jpeg"
    all_products = Product.query.order_by(Product.id.desc()).all()
    raw_orders = Order.query.order_by(Order.id.desc()).all()
    inquiries = CommissionInquiry.query.order_by(CommissionInquiry.id.desc()).all()

    orders_entries = []
    phones_set = set()
    total_revenue = 0.0
    pending_orders = 0

    for o in raw_orders:
        try:
            parsed_items = json.loads(o.items_json or "[]")
        except Exception:
            parsed_items = []
        orders_entries.append({"obj": o, "items": parsed_items})
        if o.phone:
            phones_set.add(o.phone.strip())
        if o.status != "Cancelled":
            total_revenue += float(o.total or 0.0)
        if o.status in {"Pending Verification", "Pending"}:
            pending_orders += 1

    active_products = sum(1 for p in all_products if p.visible)

    return render_template(
        "admin_dashboard.html",
        settings=settings,
        default_qr_url=default_qr_url,
        products=all_products,
        active_products=active_products,
        orders=orders_entries,
        pending_orders=pending_orders,
        unique_customers=len(phones_set),
        total_revenue=total_revenue,
        inquiries=inquiries,
    )


@app.route("/admin/product/save", methods=["POST"])
def save_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    prod_id = (request.form.get("id") or "").strip()
    name = (request.form.get("name") or "").strip()
    subtitle = (request.form.get("subtitle") or "100% Combed Cotton").strip()
    category = (request.form.get("category") or "Wearables & Bags").strip()
    price = float(request.form.get("price") or 0)
    stock = int(request.form.get("stock") or 0)
    visible = (request.form.get("visible") or "true").lower() == "true"
    description = (request.form.get("description") or "").strip()
    image_url_input = (request.form.get("image_url") or "").strip()

    try:
        uploaded_url = save_uploaded_image(request.files.get("image_file"), prefix="product")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard"))

    if prod_id:
        prod = Product.query.get_or_404(int(prod_id))
        prod.name = name
        prod.subtitle = subtitle
        prod.fiber = subtitle
        prod.category = category
        prod.price = price
        prod.stock = stock
        prod.visible = visible
        prod.description = description
        if uploaded_url:
            prod.image_url = uploaded_url
        elif image_url_input and is_safe_image_url(image_url_input):
            prod.image_url = image_url_input
    else:
        final_img = (
            uploaded_url
            or (image_url_input if is_safe_image_url(image_url_input) else None)
            or "https://placehold.co/600x600/EFE8DD/2B2420?text=Crochet+Piece"
        )
        prod = Product(
            name=name,
            subtitle=subtitle,
            fiber=subtitle,
            category=category,
            price=price,
            stock=stock,
            visible=visible,
            description=description,
            image_url=final_img,
        )
        db.session.add(prod)

    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/delete/<int:prod_id>", methods=["POST"])
def delete_product(prod_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    prod = Product.query.get_or_404(prod_id)
    db.session.delete(prod)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/order/status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    order = Order.query.get_or_404(order_id)
    status = (request.form.get("status") or "").strip()
    if status in ORDER_STATUSES:
        order.status = status
        db.session.commit()
    return redirect(url_for("admin_dashboard") + "#orders")


@app.route("/admin/settings", methods=["POST"])
def update_settings():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    settings = get_store_settings()
    settings.upi_id = (request.form.get("upi_id") or settings.upi_id).strip()
    settings.upi_name = (request.form.get("upi_name") or settings.upi_name).strip()
    settings.shipping_fee = float(request.form.get("shipping_fee") or 0)
    settings.free_shipping_above = float(request.form.get("free_shipping_above") or 0)

    new_password = request.form.get("new_password") or ""
    if new_password.strip():
        from werkzeug.security import generate_password_hash
        settings.password_hash = generate_password_hash(new_password.strip())

    try:
        uploaded_qr = save_uploaded_image(request.files.get("qr_file"), prefix="qr")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard") + "#settings")

    if uploaded_qr:
        settings.qr_image_url = uploaded_qr
    elif not settings.qr_image_url:
        settings.qr_image_url = "/static/upi_qr.jpeg"

    db.session.commit()
    flash("Settings updated.", "success")
    return redirect(url_for("admin_dashboard") + "#settings")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)