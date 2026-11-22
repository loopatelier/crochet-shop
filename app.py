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

ORDER_STATUSES = ["Pending", "Paid / Verifying", "Confirmed", "In Progress", "Shipped", "Delivered", "Cancelled"]


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
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=5)
    fiber = db.Column(db.String(120), nullable=False)
    badge = db.Column(db.String(60), nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "stock": self.stock,
            "fiber": self.fiber,
            "badge": self.badge,
            "description": self.description,
            "image_url": self.image_url,
            "active": self.active,
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(40), nullable=False, default="")
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    address = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(60), nullable=False, default="UPI")
    payment_reference = db.Column(db.String(120), nullable=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    shipping_fee = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(40), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, nullable=True)
    product_name = db.Column(db.String(140), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)


class CommissionInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    project_type = db.Column(db.String(100), nullable=False)
    yarn_color = db.Column(db.String(120), nullable=False)
    timeline = db.Column(db.String(60), nullable=True)
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PaymentSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    upi_id = db.Column(db.String(120), nullable=True)
    upi_qr_image = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


def seed_products():
    if Product.query.first() is not None:
        return

    initial_products = [
        Product(
            name="Strawberry Bag Charm",
            category="Keychains",
            price=450.00,
            stock=10,
            fiber="Soft Cotton & Milk Yarn",
            badge="Bestseller",
            description="Handcrafted crochet strawberry keepsake for bags, keys, and pouches.",
            image_url="/static/cro2.jpeg",
            active=True,
        ),
        Product(
            name="Daisy Keychain",
            category="Keychains",
            price=350.00,
            stock=12,
            fiber="100% Velvet Chenille",
            badge="Ready to Ship",
            description="Charming textured daisy keychain crocheted stitch by stitch with soft yarn.",
            image_url="/static/cro3.jpeg",
            active=True,
        ),
        Product(
            name="Heirloom Waffle Throw",
            category="Blankets",
            price=2450.00,
            stock=4,
            fiber="Merino Wool Blend",
            badge="Made to Order",
            description="Deeply textured waffle-stitch throw blanket in warm oatmeal cream.",
            image_url="/static/cro4.jpeg",
            active=True,
        ),
        Product(
            name="Meadow Granny Square Tote",
            category="Wearables",
            price=1250.00,
            stock=6,
            fiber="Mercerized Cotton",
            badge="New",
            description="Structured handmade granny square tote bag for everyday outings.",
            image_url="/static/cro5.jpeg",
            active=True,
        ),
        Product(
            name="Mini Charm & Keychain Trio",
            category="Accessories",
            price=650.00,
            stock=8,
            fiber="Fine Yarn & Beaded Accents",
            badge="Limited",
            description="Playful handmade charms for bags, keys, and phone straps.",
            image_url="/static/cro6.jpeg",
            active=True,
        ),
    ]

    db.session.add_all(initial_products)
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_products()


@app.route("/")
def index():
    products = Product.query.filter_by(active=True).all()
    qr_setting = PaymentSetting.query.first()
    return render_template("index.html", products=products, qr_setting=qr_setting)


@app.route("/api/products")
def get_products():
    products = Product.query.filter_by(active=True).all()
    return jsonify([p.to_dict() for p in products])


@app.route("/api/payment-info")
def get_payment_info():
    qr_setting = PaymentSetting.query.first()
    return jsonify({
        "upi_id": qr_setting.upi_id if qr_setting else "",
        "upi_qr_image": qr_setting.upi_qr_image if qr_setting else "",
    })


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    customer_name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    payment_method = (data.get("payment_method") or "UPI").strip()
    payment_reference = (data.get("payment_reference") or "").strip()
    items = data.get("items") or []

    if not customer_name:
        return jsonify({"error": "Please enter your full name."}), 400
    if not email:
        return jsonify({"error": "Please enter a valid email address."}), 400
    if not phone:
        return jsonify({"error": "Please enter your phone number."}), 400
    if not address:
        return jsonify({"error": "Please enter your delivery address."}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "Your basket is empty."}), 400

    computed_subtotal = 0.0
    order_items = []
    for item in items:
        qty = max(1, int(item.get("qty", item.get("quantity", 1))))
        unit_price = float(item.get("price", 0.0))
        name = str(item.get("name") or "Handmade Piece")
        pid = item.get("id")
        computed_subtotal += qty * unit_price
        order_items.append(
            OrderItem(
                product_id=pid,
                product_name=name,
                quantity=qty,
                unit_price=unit_price,
            )
        )

    shipping_fee = 0.0 if computed_subtotal >= 2500.0 or computed_subtotal == 0.0 else 80.0
    total = computed_subtotal + shipping_fee
    initial_status = "Paid / Verifying" if payment_reference else "Pending"

    order = Order(
        customer_name=customer_name,
        email=email,
        phone=phone,
        address=address,
        payment_method=payment_method or "UPI",
        payment_reference=payment_reference or None,
        subtotal=computed_subtotal,
        shipping_fee=shipping_fee,
        total=total,
        status=initial_status,
        items=order_items,
    )
    db.session.add(order)
    db.session.flush()
    order.invoice_number = f"TLA-{datetime.utcnow().strftime('%Y%m%d')}-{order.id:04d}"
    db.session.commit()

    return jsonify({
        "status": "ok",
        "order_id": order.id,
        "invoice_number": order.invoice_number,
        "created_at": order.created_at.strftime("%d %b %Y, %I:%M %p"),
        "customer_name": order.customer_name,
        "email": order.email,
        "phone": order.phone,
        "address": order.address,
        "payment_method": order.payment_method,
        "payment_reference": order.payment_reference or "Not provided",
        "subtotal": order.subtotal,
        "shipping_fee": order.shipping_fee,
        "total": order.total,
        "order_status": order.status,
        "items": [
            {
                "name": i.product_name,
                "qty": i.quantity,
                "price": i.unit_price,
                "line_total": i.quantity * i.unit_price,
            }
            for i in order.items
        ],
    }), 201


@app.route("/api/commissions", methods=["POST"])
def create_commission():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    project_type = (data.get("project_type") or "Custom Piece").strip()
    yarn_color = (data.get("yarn_color") or "Warm Terracotta & Cream").strip()
    timeline = (data.get("timeline") or "").strip()
    details = (data.get("details") or "").strip()

    if not name or not email or not details:
        return jsonify({"error": "Please provide your name, email, and project details."}), 400

    inquiry = CommissionInquiry(
        name=name,
        email=email,
        project_type=project_type,
        yarn_color=yarn_color,
        timeline=timeline or None,
        details=details,
    )
    db.session.add(inquiry)
    db.session.commit()

    return jsonify({"status": "ok", "inquiry_id": inquiry.id}), 201


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    admin_email = (
        os.environ.get("ADMIN_USER")
        or os.environ.get("ADMIN_EMAIL")
        or "admin@theloopatelier.com"
    )
    admin_password_hash = os.environ.get("ADMIN_PASSWORD_HASH")
    admin_plain_password = (
        os.environ.get("ADMIN_PASS")
        or os.environ.get("ADMIN_PASSWORD")
        or "atelier123"
    )

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        valid_pass = (
            check_password_hash(admin_password_hash, password)
            if admin_password_hash
            else password == admin_plain_password
        )
        if email == admin_email.strip().lower() and valid_pass:
            session["admin_logged_in"] = True
            session["admin_email"] = email
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin email or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_email", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    all_products = Product.query.order_by(Product.id.desc()).all()
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    all_commissions = CommissionInquiry.query.order_by(CommissionInquiry.created_at.desc()).all()
    qr_setting = PaymentSetting.query.first()

    customer_map = {}
    for o in all_orders:
        if o.email not in customer_map:
            customer_map[o.email] = (o.email, o.customer_name, o.phone, o.address)

    revenue = sum(o.total for o in all_orders if o.status != "Cancelled")
    pending_count = sum(1 for o in all_orders if o.status in {"Pending", "Paid / Verifying"})
    active_products = sum(1 for p in all_products if p.active)

    stats = {
        "products": len(all_products),
        "active_products": active_products,
        "orders": len(all_orders),
        "pending": pending_count,
        "customers": len(customer_map),
        "revenue": revenue,
    }

    return render_template(
        "admin_dashboard.html",
        products=all_products,
        orders=all_orders,
        customers=list(customer_map.values()),
        commissions=all_commissions,
        stats=stats,
        statuses=ORDER_STATUSES,
        qr_setting=qr_setting,
    )


@app.route("/admin/products/save", methods=["POST"])
def save_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product_id = (request.form.get("product_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "Keychains").strip()
    price = float(request.form.get("price") or 0)
    stock = int(request.form.get("stock") or 0)
    fiber = (request.form.get("fiber") or "Cotton Yarn").strip()
    badge = (request.form.get("badge") or "").strip() or None
    description = (request.form.get("description") or "").strip()
    image_url_input = (request.form.get("image_url") or "").strip()
    active = request.form.get("active") == "on"

    if not name or not description:
        flash("Product name and description are required.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        uploaded_path = save_uploaded_image(request.files.get("image"), prefix="product")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard"))

    if product_id:
        product = Product.query.get_or_404(int(product_id))
        product.name = name
        product.category = category
        product.price = price
        product.stock = stock
        product.fiber = fiber
        product.badge = badge
        product.description = description
        product.active = active
        if uploaded_path:
            product.image_url = uploaded_path
        elif image_url_input and is_safe_image_url(image_url_input):
            product.image_url = image_url_input
    else:
        final_image = (
            uploaded_path
            if uploaded_path
            else (image_url_input if is_safe_image_url(image_url_input) else "https://placehold.co/600x450/EFE7DC/3A322D?text=Crochet+Piece")
        )
        product = Product(
            name=name,
            category=category,
            price=price,
            stock=stock,
            fiber=fiber,
            badge=badge,
            description=description,
            image_url=final_image,
            active=active,
        )
        db.session.add(product)

    db.session.commit()
    flash("Product saved and updated in the shop.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    if new_status in ORDER_STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} updated to {new_status}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/payment-qr", methods=["POST"])
def upload_payment_qr():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    upi_id = (request.form.get("upi_id") or "").strip()
    try:
        uploaded_qr = save_uploaded_image(request.files.get("qr_image"), prefix="upi_qr")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard"))

    qr_setting = PaymentSetting.query.first()
    if not qr_setting:
        qr_setting = PaymentSetting()
        db.session.add(qr_setting)

    if upi_id:
        qr_setting.upi_id = upi_id
    if uploaded_qr:
        qr_setting.upi_qr_image = uploaded_qr
    qr_setting.updated_at = datetime.utcnow()
    db.session.commit()

    flash("UPI payment settings updated.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)