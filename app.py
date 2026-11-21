import os
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template,
    request, session, url_for
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "sqlite:///crochet_shop.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "replace-this-with-a-long-random-secret"),
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
)
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
ORDER_STATUSES = ["Pending", "Confirmed", "Processing", "Shipped", "Delivered", "Cancelled"]


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    fiber = db.Column(db.String(120), nullable=False, default="Cotton yarn")
    badge = db.Column(db.String(60), default="Ready to Ship")
    description = db.Column(db.Text, nullable=False, default="")
    image_url = db.Column(db.String(255), nullable=False, default="")
    stock = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "fiber": self.fiber,
            "badge": self.badge,
            "description": self.description,
            "image_url": self.image_url,
            "stock": self.stock,
            "active": self.active,
        }


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)


class Commission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    project_type = db.Column(db.String(100), nullable=False)
    yarn_color = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def verify_csrf():
    token = request.form.get("_csrf_token", "")
    if not token or not secrets.compare_digest(token, session.get("_csrf_token", "")):
        abort(400, description="Invalid form token. Refresh the page and try again.")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Upload a PNG, JPG, JPEG, WEBP or GIF image.")
    filename = secure_filename(file.filename)
    unique_name = f"{secrets.token_hex(8)}_{filename}"
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    file.save(Path(app.config["UPLOAD_FOLDER"]) / unique_name)
    return f"/static/uploads/{unique_name}"


def seed_products():
    if Product.query.first():
        return
    samples = [
        Product(
            name="Strawberry Bag Charm",
            category="Keychains",
            price=100,
            fiber="Soft Cotton & Milk Yarn",
            badge="Bestseller",
            description="Handcrafted crochet strawberry bag charm.",
            image_url="/static/cro2.jpeg",
            stock=10,
        ),
        Product(
            name="Daisy Keychain",
            category="Keychains",
            price=75,
            fiber="Velvet Chenille",
            badge="Ready to Ship",
            description="Beautiful handmade crochet daisy keychain.",
            image_url="/static/cro3.jpeg",
            stock=12,
        ),
        Product(
            name="Heirloom Waffle Throw",
            category="Blankets",
            price=145,
            fiber="Merino Wool Blend",
            badge="Made to Order",
            description="Textured waffle-stitch throw blanket.",
            image_url="/static/cro4.jpeg",
            stock=3,
        ),
        Product(
            name="Meadow Granny Square Tote",
            category="Wearables",
            price=620,
            fiber="Mercerized Cotton",
            badge="New",
            description="Handmade granny square tote bag.",
            image_url="/static/cro5.jpeg",
            stock=5,
        ),
        Product(
            name="Mini Charm & Keychain Trio",
            category="Accessories",
            price=240,
            fiber="Fine Yarn & Beaded Accents",
            badge="Limited",
            description="Handmade charms for bags and keys.",
            image_url="/static/cro1.jpeg",
            stock=8,
        ),
    ]
    db.session.add_all(samples)
    db.session.commit()


def upgrade_sqlite_schema():
    if db.engine.dialect.name != "sqlite":
        return
    inspector = inspect(db.engine)
    with db.engine.begin() as connection:
        if inspector.has_table("product"):
            product_columns = {col["name"] for col in inspector.get_columns("product")}
            if "stock" not in product_columns:
                connection.exec_driver_sql("ALTER TABLE product ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")
            if "active" not in product_columns:
                connection.exec_driver_sql("ALTER TABLE product ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1")

        if inspector.has_table("order"):
            order_columns = {col["name"] for col in inspector.get_columns("order")}
            if "email" not in order_columns:
                connection.exec_driver_sql(
                    'ALTER TABLE "order" ADD COLUMN email VARCHAR(160) NOT NULL DEFAULT \'\''
                )
            if "total" not in order_columns:
                connection.exec_driver_sql(
                    'ALTER TABLE "order" ADD COLUMN total FLOAT NOT NULL DEFAULT 0'
                )
            if "status" not in order_columns:
                connection.exec_driver_sql(
                    'ALTER TABLE "order" ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT \'Pending\''
                )
            if "created_at" not in order_columns:
                connection.exec_driver_sql(
                    'ALTER TABLE "order" ADD COLUMN created_at DATETIME'
                )


with app.app_context():
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.create_all()
    upgrade_sqlite_schema()
    seed_products()

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@loopatelier.com").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
    if not AdminUser.query.filter_by(email=admin_email).first():
        db.session.add(AdminUser(
            email=admin_email,
            password_hash=generate_password_hash(admin_password)
        ))
        db.session.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/products")
def get_products():
    products = Product.query.filter_by(active=True).order_by(Product.id.desc()).all()
    return jsonify([p.to_dict() for p in products])


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    items = data.get("items", [])
    if not name or "@" not in email or not isinstance(items, list) or not items:
        return jsonify(error="Enter a valid name, email and at least one product."), 400

    order = Order(customer_name=name, email=email, total=0)
    calculated_total = 0
    for row in items:
        try:
            product_id = int(row.get("id"))
            quantity = int(row.get("qty"))
        except (TypeError, ValueError, AttributeError):
            return jsonify(error="Invalid product details."), 400
        product = db.session.get(Product, product_id)
        if not product or not product.active or quantity < 1:
            return jsonify(error="One of the selected products is unavailable."), 400
        calculated_total += product.price * quantity
        order.items.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            quantity=quantity,
            unit_price=product.price,
        ))
    order.total = round(calculated_total, 2)
    db.session.add(order)
    db.session.commit()
    return jsonify(status="ok", order_id=order.id, total=order.total), 201


@app.post("/api/commissions")
def create_commission():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "project_type", "yarn_color", "details"]
    if any(not str(data.get(k, "")).strip() for k in required) or "@" not in str(data.get("email", "")):
        return jsonify(error="Please complete all required fields with a valid email."), 400
    commission = Commission(
        name=str(data["name"]).strip(),
        email=str(data["email"]).strip().lower(),
        project_type=str(data["project_type"]).strip(),
        yarn_color=str(data["yarn_color"]).strip(),
        details=str(data["details"]).strip(),
    )
    db.session.add(commission)
    db.session.commit()
    return jsonify(status="ok", inquiry_id=commission.id), 201


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        verify_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = AdminUser.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_email"] = admin.email
            session["_csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("admin_login.html")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    verify_csrf()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    products = Product.query.order_by(Product.id.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    commissions = Commission.query.order_by(Commission.created_at.desc()).all()
    customers = db.session.query(Order.email, Order.customer_name).distinct().all()
    revenue = db.session.query(db.func.coalesce(db.func.sum(Order.total), 0)).filter(
        Order.status != "Cancelled"
    ).scalar()
    stats = {
        "products": Product.query.count(),
        "active_products": Product.query.filter_by(active=True).count(),
        "orders": Order.query.count(),
        "pending": Order.query.filter_by(status="Pending").count(),
        "customers": len(customers),
        "revenue": round(float(revenue or 0), 2),
        "commissions": Commission.query.count(),
    }
    return render_template(
        "admin_dashboard.html",
        products=products,
        orders=orders,
        commissions=commissions,
        customers=customers,
        stats=stats,
        statuses=ORDER_STATUSES,
    )


@app.post("/admin/products/save")
@admin_required
def save_product():
    verify_csrf()
    product_id = request.form.get("product_id", "").strip()
    product = db.session.get(Product, int(product_id)) if product_id.isdigit() else Product()
    if product_id and product is None:
        abort(404)
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    try:
        price = float(request.form.get("price", ""))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Enter a valid price and stock quantity.", "error")
        return redirect(url_for("admin_dashboard") + "#products")
    if not name or not category or price < 0 or stock < 0 or not description:
        flash("Please complete the product fields correctly.", "error")
        return redirect(url_for("admin_dashboard") + "#products")
    try:
        new_image = save_product_image(request.files.get("image"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin_dashboard") + "#products")

    product.name = name
    product.category = category
    product.price = price
    product.fiber = request.form.get("fiber", "").strip()
    product.badge = request.form.get("badge", "").strip()
    product.description = description
    product.stock = stock
    product.active = request.form.get("active") == "on"
    if new_image:
        product.image_url = new_image
    elif not product.image_url:
        product.image_url = "/static/cro1.jpeg"
    db.session.add(product)
    db.session.commit()
    flash("Product saved successfully.", "success")
    return redirect(url_for("admin_dashboard") + "#products")


@app.post("/admin/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    verify_csrf()
    product = db.get_or_404(Product, product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_dashboard") + "#products")


@app.post("/admin/orders/<int:order_id>/status")
@admin_required
def update_order_status(order_id):
    verify_csrf()
    order = db.get_or_404(Order, order_id)
    status = request.form.get("status", "")
    if status not in ORDER_STATUSES:
        abort(400)
    order.status = status
    db.session.commit()
    flash(f"Order #{order.id} updated to {status}.", "success")
    return redirect(url_for("admin_dashboard") + "#orders")


@app.errorhandler(413)
def too_large(_error):
    return "Image is too large. Maximum upload size is 5 MB.", 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)