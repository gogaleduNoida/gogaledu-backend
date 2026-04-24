from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_jwt_extended import get_jwt_identity
from models import Lead, Payment, Partner, FirmCategory, RegistrationPlan, SupportQuery, Scheme, Employee
from extensions import db
from auth.routes import role_required
import os
from werkzeug.utils import secure_filename
from functools import wraps
from pytz import timezone
import pytz
from datetime import date
import json

partner_bp = Blueprint("partner", __name__, template_folder="templates/partner")


def profile_complete_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        partner_id = session.get('partner_id')
        partner_id = get_jwt_identity()
        partner = Partner.query.get(partner_id)
        
        if not partner or not partner.profile_complete:
            flash("Complete your profile first!", "error")
            return redirect(url_for('partner.update_profile'))
        return f(*args, **kwargs)
    return decorated_function


@partner_bp.route("/dashboard")
@role_required("partner")
@profile_complete_required
def dashboard():
    partner_id = get_jwt_identity()
    partner = Partner.query.get(partner_id)

    today = date.today()

    schemes = Scheme.query.filter(
        Scheme.status == "active",
        Scheme.start_date <= today,
        Scheme.end_date >= today
    ).all()

    if partner.status != "active":
        flash("Your account is blocked by Admin", "error")
        return redirect(url_for("auth.logout"))
    
    total_leads = Lead.query.filter_by(partner_id=partner_id).count()

    converted = Lead.query.filter_by(
        partner_id=partner_id,
        status="converted"
    ).count()

    leads = Lead.query.filter_by(partner_id=partner_id)\
                      .order_by(Lead.created_at.desc())\
                      .all()

    for l in leads:
        l.registration_amount = None
        l.partner_revenue = None

        if l.status == "Converted" and l.registration_plan:
            l.registration_amount = l.registration_plan.amount
            l.partner_revenue = l.registration_plan.partner_commission

    return render_template(
        "dashboard.html",
        total_leads =total_leads,
        converted = converted,
        partner_name=partner.name,
        leads=leads,
        schemes=schemes)

def assign_employee_by_area(state, district):
    if not state or not district:
        return None

    state = state.strip().lower()
    district = district.strip().lower()

    employees = Employee.query.filter(
        db.func.lower(Employee.state) == state,
        db.func.lower(Employee.district) == district,
        Employee.status == "active"
    ).all()

    if not employees:
        return None

    return employees[0]

@partner_bp.route("/create_lead", methods=["GET", "POST"])
@role_required("partner")
@profile_complete_required
def create_lead():
    partner_id = get_jwt_identity()
    partner = Partner.query.get(partner_id)
    partner_name = partner.name
    
    json_path = os.path.join("utils", "StateCityData.json")
    with open(json_path) as f:
        state_data = json.load(f)

    if request.method == "POST":
        student_name=request.form['student_name']
        mobile=request.form['mobile']
        email=request.form['email']
        current_status=request.form['current_status']
        address=request.form['address']
        remark=request.form['remark']
        state = request.form.get('state')
        district = request.form.get('district')
        partner_id=partner_id
        state = state.strip().lower() if state else None
        district = district.strip().lower() if district else None
    
        existing_lead = Lead.query.filter_by(mobile=mobile).first()
        if existing_lead:
            flash("Mobile number already exists!", "danger")
            return redirect(url_for("partner.create_lead"))
        
        assigned_employee = assign_employee_by_area(state, district)

        lead = Lead(
            student_name=student_name,
            mobile=mobile,
            email=email,
            current_status=current_status,
            address=address,
            remark=remark,
            partner_id=partner_id,
            state=state,
            district=district,
            assigned_to=assigned_employee.id if assigned_employee else None
        )
        
        try:
            db.session.add(lead)
            db.session.commit()
            flash("Lead created successfully", "success")
            return redirect(url_for("partner.dashboard"))
        except:
            db.session.rollback()
            flash("Duplicate entry detected!", "danger")
            return redirect(url_for("partner.create_lead"))
    return render_template("create_lead.html", partner_name=partner_name, state_data=state_data)

@partner_bp.route("/profile", methods=["GET", "POST"])
@role_required("partner")
def update_profile():
    partner_id = get_jwt_identity()
    partner = Partner.query.get_or_404(partner_id)
    partner_name = partner.name

    BASE_UPLOAD = "static/uploads/partners"
    partner_folder = os.path.join(BASE_UPLOAD, f"id_{partner_id}")
    profile_folder = os.path.join(partner_folder, "profile")
    bank_folder = os.path.join(partner_folder, "bank")
    firm_folder = os.path.join(partner_folder, "firm")

    os.makedirs(profile_folder, exist_ok=True)
    os.makedirs(bank_folder, exist_ok=True)
    os.makedirs(firm_folder, exist_ok=True)

    if request.method == "POST":

        # -------- Editable Fields --------
        partner.name = request.form.get("name")
        partner.profession = request.form.get("profession")
        partner.firm_category_id = request.form.get("firm_category")
        partner.firm_name = request.form.get("firm_name")

        # -------- Profile Image Upload --------
        profile_image = request.files.get("profile_image")
        if profile_image and profile_image.filename:
            filename = "profile_" + secure_filename(profile_image.filename)
            path = os.path.join(profile_folder, filename)
            profile_image.save(path)
            partner.profile_image = path

        # -------- Firm Proof Upload --------
        firm_proof = request.files.get("firm_proof")
        if firm_proof and firm_proof.filename:
            filename = "firm_" + secure_filename(firm_proof.filename)
            path = os.path.join(firm_folder, filename)
            firm_proof.save(path)
            partner.firm_proof = path

        # -------- Bank Details (Only If Not Locked) --------
        if not partner.bank_details_locked:
            bank_name = request.form.get("bank_name")
            acc_holder = request.form.get("account_holder_name")
            acc_number = request.form.get("account_number")
            ifsc = request.form.get("ifsc_code")
            bank_proof = request.files.get("bank_proof")

            if bank_name and acc_number and bank_proof:
                filename = "bank_" + secure_filename(bank_proof.filename)
                path = os.path.join(bank_folder, filename)
                bank_proof.save(path)

                partner.bank_name = bank_name
                partner.account_holder_name = acc_holder
                partner.account_number = acc_number
                partner.ifsc_code = ifsc
                partner.bank_proof = path
                partner.bank_details_locked = True

        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for("partner.update_profile"))

    firm_categories = FirmCategory.query.all()

    return render_template(
        "profile.html",
        partner=partner,
        partner_name=partner_name,
        firm_categories=firm_categories
    )

@partner_bp.route("/payment")
@role_required("partner")
@profile_complete_required
def payments_page():

    partner_id = get_jwt_identity()
    partner = Partner.query.get_or_404(partner_id)

    payments = (
        Payment.query
        .filter_by(partner_id=partner_id)
        .order_by(Payment.id.desc())
        .all()
    )

    total_payment = 0
    released_payment = 0
    pending_payment = 0

    payment_data = []

    for payment in payments:

        total_payment += payment.commission_amount

        if payment.status == "success":
            released_payment += payment.commission_amount

        if payment.status == "pending":
            pending_payment += payment.commission_amount

        payment_data.append({
            "student_name": payment.lead.student_name,
            "lead_id": payment.lead_id,
            "registration_amount": payment.lead.registration_plan.amount,
            "amount": payment.commission_amount,
            "status": payment.status,
            "released_date": payment.released_date.strftime("%d %b %Y") if payment.released_date else "-"
        })

    return render_template(
        "payment.html",
        partner_name=partner.name,
        payments=payment_data,
        total_payment=total_payment,
        released_payment=released_payment,
        pending_payment=pending_payment
    )

@partner_bp.route("/terms_conditions")
@role_required("partner")
def terms_conditions():
    partner_id = get_jwt_identity() 
    partner = Partner.query.get_or_404(partner_id)
    registrationPlans = RegistrationPlan.query.all()

    return render_template(
        "terms_conditions.html",
        partner_name=partner.name, registrationPlans=registrationPlans)


@partner_bp.route("/support", methods=["GET", "POST"])
@role_required("partner")
@profile_complete_required
def support():

    partner_id = get_jwt_identity()
    partner = Partner.query.get_or_404(partner_id)

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")

        if not title or not description or len(description) < 10:
            flash("Title and description must be at least 10 characters.", "danger")
            return redirect(url_for("partner.support"))

        new_query = SupportQuery(
            user_id=partner.id,
            username=partner.name,
            role="partner",
            title=title,
            description=description
        )

        db.session.add(new_query)
        db.session.commit()

        flash("Your query has been sent successfully!", "success")
        return redirect(url_for("partner.support"))

    # Fetch only current partner queries
    queries = SupportQuery.query.filter_by(
        user_id=partner.id,
        role="partner"
    ).order_by(SupportQuery.sent_at.desc()).all()

    # Convert to IST
    ist = timezone("Asia/Kolkata")
    for q in queries:
        q.ist_time = q.sent_at.replace(tzinfo=pytz.utc).astimezone(ist)

    return render_template(
        "support.html",
        partner_name=partner.name,
        queries=queries
    )