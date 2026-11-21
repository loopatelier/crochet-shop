import os
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Use DATABASE_URL if provided (e.g., Postgres), otherwise local/ephemeral SQLite
database_url = os.environ.get("DATABASE_URL", "sqlite:///crochet_shop.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")

db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Float, nullable=False)
    fiber = db.Column(db.String(120), nullable=False)
    badge = db.Column(db.String(60), nullable=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

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
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)
    items_json = db.Column(db.Text, nullable=False, default="[]")


class CommissionInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    project_type = db.Column(db.String(120), nullable=False)
    yarn_color = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, nullable=False)


def seed_products():
    if Product.query.first() is not None:
        return

    initial_products = [
        Product(
            name="Cozy Crochet Bouquet",
            category="bouquets",
            price=38.00,
            fiber="Soft Cotton & Milk Yarn",
            badge="Bestseller",
            description="Handcrafted crochet floral keepsake wrapped for gifting.",
            image_url="/static/cro2.jpeg",
        ),
        Product(
            name="Barnaby the Chunky Bear",
            category="amigurumi",
            price=48.00,
            fiber="100% Velvet Chenille",
            badge="Ready to Ship",
            description="Hand-crocheted plush bear with safety eyes and ultra-soft velvet.",
            image_url="/static/cro3.jpeg",
        ),
        Product(
            name="Heirloom Waffle Throw",
            category="blankets",
            price=145.00,
            fiber="Merino Wool Blend",
            badge="Made to Order",
            description="Textured waffle-stitch throw blanket in warm oatmeal cream.",
            image_url="/static/cro4.jpeg",
        ),
        Product(
            name="Meadow Granny Square Tote",
            category="wearables",
            price=62.00,
            fiber="Mercerized Cotton",
            badge="New",
            description="Structured handmade granny square tote bag for everyday outings.",
            image_url="/static/cro5.jpeg",
        ),
        Product(
            name="Mini Charm & Keychain Trio",
            category="accessories",
            price=24.00,
            fiber="Fine Yarn & Beaded Accents",
            badge="Limited",
            description="Playful handmade charms for bags, keys, and phone straps.",
            image_url="/static/cro6.jpeg",
        ),
    ]

    db.session.add_all(initial_products)
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_products()


@app.route("/")
def index():
    products = Product.query.all()
    return render_template("index.html", products=products)


@app.route("/api/products")
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@app.route("/api/orders", methods=["POST"])
def create_order():
    import json

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    order = Order(
        customer_name=(data.get("name") or email.split("@")[0]).strip(),
        email=email,
        total=float(data.get("total") or 0.0),
        items_json=json.dumps(data.get("items") or []),
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({"status": "ok", "order_id": order.id}), 201


@app.route("/api/commissions", methods=["POST"])
def create_commission():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    inquiry = CommissionInquiry(
        name=(data.get("name") or "Guest").strip(),
        email=email,
        project_type=(data.get("project_type") or "Custom Piece").strip(),
        yarn_color=(data.get("yarn_color") or "Natural Cream").strip(),
        details=(data.get("details") or "").strip(),
    )
    db.session.add(inquiry)
    db.session.commit()
    return jsonify({"status": "ok", "inquiry_id": inquiry.id}), 201


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)