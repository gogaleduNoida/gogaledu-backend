from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Admin, Partner, Employee, FirmCategory
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, verify_jwt_in_request, get_jwt
from datetime import timedelta
from functools import wraps
from flask import abort
from extensions import db

auth_bp = Blueprint("auth", __name__, template_folder="templates")

def role_required(required_role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            if claims.get("role") != required_role:
                abort(403) 

            return fn(*args, **kwargs)
        return decorator
    return wrapper

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form['role']
        mobile = request.form['mobile']
        password = request.form['password']
        user = None
        if role == "admin":
            user = Admin.query.filter_by(mobile=mobile).first()
        elif role == "partner":
            user = Partner.query.filter_by(mobile=mobile).first()
        else:
            user = Employee.query.filter_by(mobile=mobile).first()

        if user and user.check_password(password):
            access_token = create_access_token(identity=str(user.id),              
                additional_claims={"role": role, "name": user.name},
                expires_delta=timedelta(hours=8))

            if role == "admin":
                resp = redirect(url_for("admin.panel"))
            elif role == "partner":
                resp = redirect(url_for("partner.dashboard"))
            else:
                resp = redirect(url_for("employee.workbench"))

            set_access_cookies(resp, access_token)
            return resp
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for("auth.login"))
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    resp = redirect("https://www.gogaledu.com/")
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route("/partner_signup", methods=["GET", "POST"])
def partner_signup():

    firm_categories = FirmCategory.query.filter_by(is_active=True).all()

    if request.method == "POST":
        name = request.form.get("name").strip()
        mobile = request.form.get("mobile").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        firm_category_id = request.form.get("firm_category")

        existing_partner = Partner.query.filter(
            (Partner.mobile == mobile) | (Partner.email == email)
        ).first()

        if existing_partner:
            flash("Mobile or Email already exists!", "danger")
            return redirect(url_for("auth.partner_signup"))
        
        try:
            partner = Partner(name=name, mobile=mobile, email=email, firm_category_id=firm_category_id, status="active")
            partner.set_password(password)

            db.session.add(partner)
            db.session.commit()
            flash("Partner created successfully", "success")
            return redirect(url_for("partner.update_profile"))
        except:
            db.session.rollback()
            flash("Duplicate entry detected!", "danger")
            return redirect(url_for("auth.partner_signup"))
    return render_template("partner_signup.html", firm_categories=firm_categories)