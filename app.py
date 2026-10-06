import os
import secrets
from datetime import datetime

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "demo-only-change-before-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///loantrack_demo.db").replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
demo_tokens = {}

STAGES = ["Application received", "Documents verified", "Credit assessment", "Decision", "Funds disbursed"]


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    application = db.relationship("LoanApplication", backref="customer", uselist=False)


class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product = db.Column(db.String(120), nullable=False)
    requested_amount = db.Column(db.Integer, nullable=False)
    stage_index = db.Column(db.Integer, nullable=False, default=0)
    next_action = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    history = db.relationship("StatusEvent", backref="application", lazy=True, cascade="all, delete-orphan")
    collateral = db.relationship("CollateralVerification", backref="application", uselist=False, cascade="all, delete-orphan")


class StatusEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("loan_application.id"), nullable=False)
    stage_index = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(240), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    changed_by = db.Column(db.String(120), nullable=False)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("loan_application.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="REQUIRED")
    officer_comment = db.Column(db.String(240), nullable=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("loan_application.id"), nullable=False)
    message = db.Column(db.String(240), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CollateralVerification(db.Model):
    """Test-only collateral workflow. It never contacts an external land registry."""
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("loan_application.id"), nullable=False, unique=True)
    title_number = db.Column(db.String(100), nullable=False)
    county = db.Column(db.String(100), nullable=False)
    submitted_owner = db.Column(db.String(160), nullable=False)
    submitted_size = db.Column(db.String(60), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="PENDING")
    customer_status = db.Column(db.String(160), nullable=False, default="Collateral details are awaiting review.")
    official_search_reference = db.Column(db.String(100), nullable=True)
    officer_notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    events = db.relationship("CollateralEvent", backref="collateral", lazy=True, cascade="all, delete-orphan")


class CollateralEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collateral_id = db.Column(db.Integer, db.ForeignKey("collateral_verification.id"), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    changed_by = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def seed_demo_data():
    if not User.query.first():
        customer = User(username="LT-260912-041", password_hash=generate_password_hash("2468"), role="customer", display_name="Mary Wanjiku")
        customer_two = User(username="LT-260911-018", password_hash=generate_password_hash("1357"), role="customer", display_name="James Otieno")
        manager = User(username="manager.demo", password_hash=generate_password_hash("Manager2026!"), role="manager", display_name="Demo Branch Manager")
        db.session.add_all([customer, customer_two, manager])
        db.session.flush()
        first = LoanApplication(reference="LT-260912-041", customer=customer, product="Business expansion loan", requested_amount=250000, stage_index=2, next_action="No action is required. A decision update is expected by 16 September 2026.")
        second = LoanApplication(reference="LT-260911-018", customer=customer_two, product="Asset finance loan", requested_amount=480000, stage_index=1, next_action="Please bring the requested proof of income to the branch or upload it through the approved channel.")
        db.session.add_all([first, second])
        db.session.flush()
        db.session.add_all([
            StatusEvent(application=first, stage_index=0, message="Application received.", changed_by="System"),
            StatusEvent(application=first, stage_index=1, message="Documents passed initial checks.", changed_by="Demo Branch Manager"),
            StatusEvent(application=first, stage_index=2, message="Credit assessment is in progress.", changed_by="Demo Branch Manager"),
            StatusEvent(application=second, stage_index=0, message="Application received.", changed_by="System"),
            StatusEvent(application=second, stage_index=1, message="Documents are being checked.", changed_by="Demo Branch Manager"),
        ])
        db.session.add_all([
            Document(application_id=first.id, name="National ID", status="VERIFIED"),
            Document(application_id=first.id, name="Payslip", status="VERIFIED"),
            Document(application_id=first.id, name="Bank statement", status="RECEIVED"),
            Document(application_id=first.id, name="Title document", status="UNDER_REVIEW"),
            Document(application_id=second.id, name="National ID", status="VERIFIED"),
            Document(application_id=second.id, name="Latest payslip", status="REQUIRED", officer_comment="Please submit the latest payslip."),
        ])
        db.session.commit()
    first = LoanApplication.query.filter_by(reference="LT-260912-041").first()
    if first and not first.collateral:
        collateral = CollateralVerification(application=first, title_number="DEMO/NAIROBI/041", county="Nairobi", submitted_owner="Mary Wanjiku", submitted_size="0.25 hectares", status="PENDING", customer_status="Collateral details are undergoing review.")
        db.session.add(collateral)
        db.session.flush()
        db.session.add(CollateralEvent(collateral=collateral, status="PENDING", message="Test collateral record created. No external land-system request was made.", changed_by="System"))
        db.session.commit()


def current_user():
    if not session.get("user_id"):
        return None
    return db.session.get(User, session["user_id"])


def api_user():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user_id = demo_tokens.get(token)
    return db.session.get(User, user_id) if user_id else None


def application_payload(application):
    return {
        "reference": application.reference,
        "product": application.product,
        "requestedAmount": application.requested_amount,
        "stageIndex": application.stage_index,
        "stage": STAGES[application.stage_index],
        "nextAction": application.next_action,
        "updatedAt": application.updated_at.isoformat(),
        "history": [
            {
                "stageIndex": e.stage_index,
                "stage": STAGES[e.stage_index],
                "message": e.message,
                "changedBy": e.changed_by,
                "createdAt": e.created_at.isoformat(),
            }
            for e in StatusEvent.query.filter_by(application_id=application.id)
                                      .order_by(StatusEvent.created_at.asc()).all()
        ],
        "documents": [
            {"name": d.name, "status": d.status, "comment": d.officer_comment or ""}
            for d in Document.query.filter_by(application_id=application.id).all()
        ],
        "notifications": [
            {"message": n.message, "createdAt": n.created_at.isoformat()}
            for n in Notification.query.filter_by(application_id=application.id)
                                      .order_by(Notification.created_at.desc()).all()
        ],
        "collateralStatus": application.collateral.customer_status if application.collateral else None,
    }


def require_role(role):
    user = current_user()
    if not user or user.role != role:
        abort(403)
    return user


def generate_customer_username():
    """Generate the next LT-YYMMDD-NNN reference for today."""
    today = datetime.utcnow().strftime("%y%m%d")
    prefix = f"LT-{today}-"
    last = User.query.filter(User.username.like(prefix + "%")).order_by(User.username.desc()).first()
    seq = int(last.username.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


@app.context_processor
def utility_processor():
    return {"stages": STAGES, "current_user": current_user}


@app.get("/")
def index():
    user = current_user()
    if user:
        return redirect(url_for("manager_dashboard" if user.role == "manager" else "customer_dashboard"))
    return render_template("login.html")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("The demo sign-in details do not match. Please try again.", "error")
        return redirect(url_for("index"))
    session.clear()
    session["user_id"] = user.id
    return redirect(url_for("manager_dashboard" if user.role == "manager" else "customer_dashboard"))


@app.post("/api/demo/login")
def api_demo_login():
    """Demo API only. Replace with bank-approved authentication before any real use."""
    payload = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=str(payload.get("username", "")).strip()).first()
    if not user or not check_password_hash(user.password_hash, str(payload.get("password", ""))):
        return jsonify(error="Invalid demo sign-in details."), 401
    token = secrets.token_urlsafe(32)
    demo_tokens[token] = user.id
    return jsonify(token=token, role=user.role, displayName=user.display_name)


@app.get("/api/demo/me")
def api_demo_me():
    user = api_user()
    if not user:
        return jsonify(error="Sign in required."), 401
    if user.role == "customer":
        return jsonify(role="customer", displayName=user.display_name, application=application_payload(user.application))
    applications = LoanApplication.query.order_by(LoanApplication.updated_at.desc()).all()
    return jsonify(role="manager", displayName=user.display_name, applications=[application_payload(a) | {"customerName": a.customer.display_name, "id": a.id} for a in applications])


# ============================================================
# JSON API endpoints for the Android app
# ============================================================

def require_api_role(role):
    user = api_user()
    if not user or user.role != role:
        return None
    return user


@app.get("/api/demo/application")
def api_customer_application():
    user = require_api_role("customer")
    if not user:
        return jsonify(error="Customer sign-in required."), 401
    return jsonify(application_payload(user.application))


@app.get("/api/demo/manager/applications")
def api_manager_applications():
    user = require_api_role("manager")
    if not user:
        return jsonify(error="Manager sign-in required."), 401
    apps = LoanApplication.query.order_by(LoanApplication.updated_at.desc()).all()
    return jsonify(applications=[
        {
            **application_payload(a),
            "customerName": a.customer.display_name,
            "id": a.id,
        }
        for a in apps
    ])


@app.get("/api/demo/manager/application/<int:application_id>")
def api_manager_application(application_id):
    user = require_api_role("manager")
    if not user:
        return jsonify(error="Manager sign-in required."), 401
    a = db.session.get(LoanApplication, application_id)
    if not a:
        return jsonify(error="Application not found."), 404
    return jsonify({
        **application_payload(a),
        "id": a.id,
        "customerName": a.customer.display_name,
    })


@app.post("/api/demo/manager/application/<int:application_id>/status")
def api_manager_update_status(application_id):
    user = require_api_role("manager")
    if not user:
        return jsonify(error="Manager sign-in required."), 401
    a = db.session.get(LoanApplication, application_id)
    if not a:
        return jsonify(error="Application not found."), 404

    payload = request.get_json(silent=True) or {}
    try:
        new_stage = int(payload.get("stageIndex"))
        if new_stage not in range(len(STAGES)):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="stageIndex must be 0..4"), 400

    note = str(payload.get("message", "")).strip()[:240]
    action = str(payload.get("nextAction", "")).strip()[:500]

    a.stage_index = new_stage
    if action:
        a.next_action = action
    db.session.add(StatusEvent(
        application=a,
        stage_index=new_stage,
        message=note or f"Status changed to {STAGES[new_stage]}.",
        changed_by=user.display_name,
    ))
    db.session.add(Notification(
        application_id=a.id,
        message=f"LoanTrack: your application {a.reference} moved to {STAGES[new_stage]}. Sign in securely to view details.",
    ))
    db.session.commit()
    return jsonify(ok=True, application=application_payload(a) | {"id": a.id})


# ------------------------------------------------------------
# ANDROID APP: Manager creates a new customer (JSON)
# ------------------------------------------------------------

@app.post("/api/demo/manager/customers")
def api_manager_create_customer():
    """
    Manager-only. Creates a customer and optionally their first loan application.

    JSON body:
    {
      "displayName": "Jane Mwangi",             # required
      "username":    "LT-260915-001",           # optional; auto-generated
      "pin":         "4321",                    # required
      "product":     "Business expansion loan", # optional
      "requestedAmount": 300000,                # optional but required if product is set
      "nextAction":  "Please submit your ID."   # optional
    }
    """
    manager = require_api_role("manager")
    if not manager:
        return jsonify(error="Manager sign-in required."), 401

    payload = request.get_json(silent=True) or {}
    display_name = str(payload.get("displayName", "")).strip()
    username = str(payload.get("username", "")).strip()
    pin = str(payload.get("pin", "")).strip()

    if not display_name:
        return jsonify(error="displayName is required."), 400
    if not pin or len(pin) < 4:
        return jsonify(error="pin must be at least 4 characters."), 400

    if not username:
        username = generate_customer_username()

    if User.query.filter_by(username=username).first():
        return jsonify(error=f"Username {username} already exists."), 409

    customer = User(
        username=username,
        password_hash=generate_password_hash(pin),
        role="customer",
        display_name=display_name,
    )
    db.session.add(customer)
    db.session.flush()

    application = None
    product = str(payload.get("product", "")).strip()
    if product:
        amount_raw = payload.get("requestedAmount")
        try:
            amount = int(amount_raw)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            db.session.rollback()
            return jsonify(error="requestedAmount must be a positive integer when product is set."), 400

        application = LoanApplication(
            reference=username,
            customer=customer,
            product=product,
            requested_amount=amount,
            stage_index=0,
            next_action=str(payload.get("nextAction", "")).strip()
                or "Your application has been received. A credit officer will be in touch.",
        )
        db.session.add(application)
        db.session.flush()
        db.session.add(StatusEvent(
            application=application,
            stage_index=0,
            message="Application received.",
            changed_by=manager.display_name,
        ))
        db.session.add(Notification(
            application_id=application.id,
            message=f"LoanTrack: welcome {display_name}. Your application {username} has been received.",
        ))

    db.session.commit()

    return jsonify(
        ok=True,
        customer={
            "id": customer.id,
            "username": customer.username,
            "displayName": customer.display_name,
        },
        application=(
            {**application_payload(application), "id": application.id}
            if application else None
        ),
    ), 201

# ============================================================


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.get("/customer")
def customer_dashboard():
    user = require_role("customer")
    documents = Document.query.filter_by(application_id=user.application.id).all()
    notifications = Notification.query.filter_by(application_id=user.application.id).order_by(Notification.created_at.desc()).all()
    return render_template("customer.html", application=user.application, documents=documents, notifications=notifications)


@app.get("/manager")
def manager_dashboard():
    require_role("manager")
    applications = LoanApplication.query.order_by(LoanApplication.updated_at.desc()).all()
    selected = request.args.get("application", type=int)
    active = db.session.get(LoanApplication, selected) if selected else applications[0]
    documents = Document.query.filter_by(application_id=active.id).all()
    notifications = Notification.query.filter_by(application_id=active.id).order_by(Notification.created_at.desc()).all()
    counts = {"total": len(applications), "documents": sum(1 for app in applications if app.stage_index == 1), "assessment": sum(1 for app in applications if app.stage_index == 2), "decision": sum(1 for app in applications if app.stage_index == 3), "disbursement": sum(1 for app in applications if app.stage_index == 4)}
    return render_template("manager.html", applications=applications, active=active, documents=documents, notifications=notifications, counts=counts)


@app.post("/manager/application/<int:application_id>")
def update_application(application_id):
    manager = require_role("manager")
    application = db.get_or_404(LoanApplication, application_id)
    try:
        new_stage = int(request.form.get("stage_index"))
        if new_stage not in range(len(STAGES)):
            raise ValueError
    except (TypeError, ValueError):
        abort(400)
    note = request.form.get("message", "").strip()[:240]
    action = request.form.get("next_action", "").strip()[:500]
    application.stage_index = new_stage
    application.next_action = action or application.next_action
    db.session.add(StatusEvent(application=application, stage_index=new_stage, message=note or f"Status changed to {STAGES[new_stage]}.", changed_by=manager.display_name))
    db.session.add(Notification(application_id=application.id, message=f"LoanTrack: your application {application.reference} moved to {STAGES[new_stage]}. Sign in securely to view details."))
    db.session.commit()
    flash("Demo status updated. Sign in as the customer to see the change.", "success")
    return redirect(url_for("manager_dashboard", application=application.id))


# ------------------------------------------------------------
# WEB UI: Manager creates a customer from the HTML dashboard (form)
# ------------------------------------------------------------

@app.post("/manager/customers")
def manager_create_customer_form():
    manager = require_role("manager")

    display_name = request.form.get("display_name", "").strip()
    username = request.form.get("username", "").strip()
    pin = request.form.get("pin", "").strip()
    product = request.form.get("product", "").strip()
    amount_raw = request.form.get("requested_amount", "").strip()
    next_action = request.form.get("next_action", "").strip()

    if not display_name or not pin or len(pin) < 4:
        flash("Name is required and PIN must be at least 4 characters.", "error")
        return redirect(url_for("manager_dashboard"))

    if not username:
        username = generate_customer_username()

    if User.query.filter_by(username=username).first():
        flash(f"Username {username} already exists. Please choose another.", "error")
        return redirect(url_for("manager_dashboard"))

    customer = User(
        username=username,
        password_hash=generate_password_hash(pin),
        role="customer",
        display_name=display_name,
    )
    db.session.add(customer)
    db.session.flush()

    if product:
        amount_int = int(amount_raw) if amount_raw.isdigit() and int(amount_raw) > 0 else 0
        if amount_int > 0:
            application = LoanApplication(
                reference=username,
                customer=customer,
                product=product,
                requested_amount=amount_int,
                stage_index=0,
                next_action=next_action or "Your application has been received. A credit officer will be in touch.",
            )
            db.session.add(application)
            db.session.flush()
            db.session.add(StatusEvent(
                application=application,
                stage_index=0,
                message="Application received.",
                changed_by=manager.display_name,
            ))
            db.session.add(Notification(
                application_id=application.id,
                message=f"LoanTrack: welcome {display_name}. Your application {username} has been received.",
            ))

    db.session.commit()
    flash(f"Customer {display_name} created. Login ID: {username}", "success")
    return redirect(url_for("manager_dashboard"))

# ============================================================


@app.post("/manager/application/<int:application_id>/document/<int:document_id>")
def update_document(application_id, document_id):
    manager = require_role("manager")
    document = db.get_or_404(Document, document_id)
    if document.application_id != application_id:
        abort(404)
    status = request.form.get("status", "REQUIRED")
    if status not in {"REQUIRED", "RECEIVED", "VERIFIED", "UNDER_REVIEW", "REJECTED"}:
        abort(400)
    document.status = status
    document.officer_comment = request.form.get("comment", "").strip()[:240] or None
    db.session.add(Notification(application_id=application_id, message=f"LoanTrack: there is a document update for application {document.application.reference}. Sign in securely to view it."))
    db.session.add(StatusEvent(application=document.application, stage_index=document.application.stage_index, message=f"Document update: {document.name} - {status}.", changed_by=manager.display_name))
    db.session.commit()
    flash("Demo document status and customer notification recorded.", "success")
    return redirect(url_for("manager_dashboard", application=application_id))


@app.post("/manager/application/<int:application_id>/collateral")
def update_collateral(application_id):
    manager = require_role("manager")
    application = db.get_or_404(LoanApplication, application_id)
    collateral = application.collateral
    if not collateral:
        collateral = CollateralVerification(
            application=application,
            title_number=request.form.get("title_number", "").strip()[:100] or "DEMO TITLE REQUIRED",
            county=request.form.get("county", "").strip()[:100] or "Not recorded",
            submitted_owner=request.form.get("submitted_owner", "").strip()[:160] or "Not recorded",
            submitted_size=request.form.get("submitted_size", "").strip()[:60] or None,
        )
        db.session.add(collateral)
    else:
        collateral.title_number = request.form.get("title_number", "").strip()[:100] or collateral.title_number
        collateral.county = request.form.get("county", "").strip()[:100] or collateral.county
        collateral.submitted_owner = request.form.get("submitted_owner", "").strip()[:160] or collateral.submitted_owner
        collateral.submitted_size = request.form.get("submitted_size", "").strip()[:60] or collateral.submitted_size
    status = request.form.get("status", "PENDING")
    allowed = {"PENDING", "SIMULATED_MATCH", "DISCREPANCY", "HOLD"}
    if status not in allowed:
        abort(400)
    collateral.status = status
    collateral.customer_status = request.form.get("customer_status", "").strip()[:160] or collateral.customer_status
    collateral.official_search_reference = request.form.get("official_search_reference", "").strip()[:100] or None
    collateral.officer_notes = request.form.get("officer_notes", "").strip()[:1000] or None
    db.session.flush()
    db.session.add(CollateralEvent(
        collateral=collateral, status=status,
        message="Test update recorded. This is not an official Ministry of Lands or Ardhisasa verification.",
        changed_by=manager.display_name,
    ))
    db.session.commit()
    flash("Test collateral status updated. No external land-registry request was sent.", "success")
    return redirect(url_for("manager_dashboard", application=application.id))


@app.post("/manager/application/<int:application_id>/collateral/simulated-search")
def simulated_land_search(application_id):
    """Presentation-only response. Never replace this with portal scraping or shared credentials."""
    manager = require_role("manager")
    application = db.get_or_404(LoanApplication, application_id)
    collateral = application.collateral
    if not collateral:
        flash("Add the fictional collateral details before running the demonstration search.", "error")
        return redirect(url_for("manager_dashboard", application=application.id))
    result = request.form.get("demo_result", "match")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    collateral.official_search_reference = f"DEMO-ARDHI-{timestamp}"
    if result == "discrepancy":
        collateral.status = "DISCREPANCY"
        collateral.customer_status = "Collateral review requires attention. Please wait for a secure update."
        event_message = "SIMULATION ONLY: a fictional official-search response reported a discrepancy; officer review is required."
    else:
        collateral.status = "SIMULATED_MATCH"
        collateral.customer_status = "Collateral review is complete and the application is proceeding."
        event_message = "SIMULATION ONLY: fictional submitted and registry data matched. No external system was contacted."
    db.session.add(CollateralEvent(collateral=collateral, status=collateral.status, message=event_message, changed_by=manager.display_name))
    db.session.commit()
    flash("Ardhisasa integration simulation completed. This result is fictional and no external service was contacted.", "success")
    return redirect(url_for("manager_dashboard", application=application.id))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/service-worker.js")
def service_worker():
    response = send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/.well-known/assetlinks.json")
def android_asset_links():
    """Only publish a trusted-app association after the signed Android app is built."""
    package_name = os.getenv("ANDROID_PACKAGE_NAME")
    fingerprint = os.getenv("ANDROID_SHA256_CERT_FINGERPRINT")
    if not package_name or not fingerprint:
        abort(404)
    return jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": package_name,
            "sha256_cert_fingerprints": [fingerprint],
        },
    }])


with app.app_context():
    db.create_all()
    seed_demo_data()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
