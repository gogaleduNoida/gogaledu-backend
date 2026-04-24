from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from models import Partner, Lead, Payment, Admin, Employee, AdmissionCourse, FirmCategory, RegistrationPlan, SupportQuery, Scheme
from extensions import db
from sqlalchemy.exc import IntegrityError
from auth.routes import role_required
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, text
import pytz
from datetime import timezone, datetime
from decimal import Decimal
from werkzeug.utils import secure_filename
import os
import csv
from PIL import Image
import uuid
import json

admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")

@admin_bp.route("/panel")
@role_required("admin")
def panel():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

    total_partners = Partner.query.count()
    active_partners = Partner.query.filter_by(status="active").count()
    total_employees = Employee.query.count()
    total_leads = Lead.query.count()
    total_converted = Lead.query.filter_by(status="Converted").count()
    return render_template("panel.html",
                           total_partners=total_partners,
                           active_partners=active_partners,
                           total_employees=total_employees,
                           total_leads=total_leads,
                           total_converted=total_converted,
                           admin_name=admin_name
)

@admin_bp.route("/partners")
@role_required("admin")
def partners():
    partners = Partner.query.all()

    # partner-wise total leads
    total_leads = (
        db.session.query(
            Lead.partner_id,
            func.count(Lead.id).label("total")
        )
        .group_by(Lead.partner_id)
        .all()
    )

    # partner-wise converted leads
    converted_leads = (
        db.session.query(
            Lead.partner_id,
            func.count(Lead.id).label("converted")
        )
        .filter(Lead.status == "converted")
        .group_by(Lead.partner_id)
        .all()
    )

    total_leads_dict = {p: c for p, c in total_leads}
    converted_dict = {p: c for p, c in converted_leads}

    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

    return render_template("partners.html", partners=partners, total_leads= total_leads_dict, converted=converted_dict, admin_name=admin_name)

@admin_bp.route("/partner/<int:partner_id>")
@role_required("admin")
def view_partner(partner_id):

    partner = Partner.query.get_or_404(partner_id)

    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    firm_categories = FirmCategory.query.all()

    return render_template(
        "view_partner.html",
        admin_name=admin_name,
        partner=partner,
        firm_categories=firm_categories
    )

@admin_bp.route("/partner/<int:partner_id>/toggle-bank-lock", methods=["POST"])
@role_required("admin")
def toggle_bank_lock(partner_id):

    partner = Partner.query.get_or_404(partner_id)
    partner.bank_details_locked = not partner.bank_details_locked
    db.session.commit()
    return redirect(url_for("admin.view_partner", partner_id=partner_id))

@admin_bp.route("/partner/<int:partner_id>/status", methods=["POST"])
@role_required("admin")
def update_partner_status(partner_id):
    status = request.form.get("status")

    if status not in ["active", "inactive", "blocked"]:
        flash("Invalid status selected!", "error")
        return redirect(url_for("admin.partners"))

    partner = Partner.query.get_or_404(partner_id)
    partner.status = status
    db.session.commit()

    flash(f"Partner status updated to {status.upper()}", "success")
    return redirect(url_for("admin.partners"))

@admin_bp.route("/create_partner", methods=["GET", "POST"])
@role_required("admin")
def create_partner():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

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
            return redirect(url_for("admin.create_partner"))
        
        try:
            partner = Partner(name=name, mobile=mobile, email=email, firm_category_id=firm_category_id, status="active")
            partner.set_password(password)

            db.session.add(partner)
            db.session.commit()
            flash("Partner created successfully", "success")
            return redirect(url_for("admin.partners"))
        except:
            db.session.rollback()
            flash("Duplicate entry detected!", "danger")
            return redirect(url_for("admin.create_partner"))
    return render_template("create_partner.html", admin_name=admin_name, firm_categories=firm_categories)

@admin_bp.route("/leads")
@role_required("admin")
def leads():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    page = request.args.get("page", 1, type=int)
    per_page = 10

    leads_pagination = Lead.query.order_by(Lead.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    leads = leads_pagination.items
    courses = AdmissionCourse.query.all()
    registration_plans = RegistrationPlan.query.all()
    employees = Employee.query.all()
    return render_template("leads.html", leads=leads, pagination=leads_pagination, courses=courses, registration_plans=registration_plans, employees=employees,admin_name=admin_name)

@admin_bp.route("/lead/<int:lead_id>")
@role_required("admin")
def view_lead(lead_id):

    lead = Lead.query.get_or_404(lead_id)
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    lead_time_ist = None 
    employees = Employee.query.all()


    if lead.remark_updated_at:
        ist = pytz.timezone('Asia/Kolkata')
        lead_time_ist = (
            lead.remark_updated_at
            .replace(tzinfo=timezone.utc)
            .astimezone(ist)
        )

    return render_template(
        "view_lead.html",
        admin_name=admin_name,
        lead_time_ist=lead_time_ist,
        lead=lead,
        employees=employees
    )

@admin_bp.route("/update_lead/<int:lead_id>", methods=["POST"])
@role_required("admin")
def update_lead(lead_id):
    new_status = request.form.get("status")
    payment_term = request.form.get("payment_term")
    course_id = request.form.get('course_id')
    registration_plan_id = request.form.get('registration_plan_id')
    lead = Lead.query.get_or_404(lead_id)

    if new_status:
        if lead.status in ["Converted", "Not Converted"] and new_status != lead.status:
            flash("Lead status already finalized and cannot be changed.", "warning")
            return redirect(url_for("admin.leads"))
        lead.status = new_status

    # COURSE + PAYMENT ONLY IF CONVERTED
    if lead.status == "Converted":

        if lead.course_id and lead.registration_plan_id and lead.payment_term:
            flash("Plan, Course and Payment already finalized. Cannot modify again.", "warning")
            return redirect(url_for("admin.leads"))

        if registration_plan_id:
            lead.registration_plan_id = int(registration_plan_id)

        if course_id:
            lead.course_id = int(course_id)

        if payment_term:
            if payment_term not in ["Cash", "Online", "Other"]:
                flash("Invalid payment method.", "error")
                return redirect(url_for("admin.leads"))
            lead.payment_term = payment_term


        if lead.registration_plan_id:

            plan = RegistrationPlan.query.get(lead.registration_plan_id)

            if plan:
                existing_payment = Payment.query.filter_by(lead_id=lead.id).first()

                if not existing_payment:
                    payment = Payment(
                        partner_id=lead.partner_id,
                        lead_id=lead.id,
                        commission_amount=plan.partner_commission,
                        status="Pending"
                    )

                    db.session.add(payment)
                else:
                    existing_payment.commission_amount = plan.partner_commission

    db.session.commit()
    flash("Lead updated successfully.", "success")
    return redirect(url_for("admin.leads"))

@admin_bp.route("/assign_lead/<int:lead_id>", methods=["POST"])
@role_required("admin")
def assign_lead(lead_id):
    employee_id = request.form.get("employee_id")

    lead = Lead.query.get_or_404(lead_id)

    if employee_id:
        lead.assigned_to = int(employee_id)
    else:
        lead.assigned_to = None

    db.session.commit()
    flash("Lead assigned successfully", "success")
    return redirect(url_for("admin.leads"))

# ---------------temporary method--------admin create
@admin_bp.route("/create_admin", methods=["GET", "POST"])
@role_required("admin")
def create_admin():
    if request.method == "POST":
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']

        existing_admin = Admin.query.filter(
    (Admin.mobile == mobile) | (Admin.email == email)
).first()
        
        if existing_admin:
            if existing_admin.mobile == mobile:
                flash("Mobile number already exists!", "danger")
            else:
                flash("Email already exists!", "danger")
            return redirect(url_for("admin.create_admin"))

        admin = Admin(name=name, mobile=mobile, email=email)
        admin.set_password(password)

        try:
            db.session.add(admin)
            db.session.commit()
            flash("Admin created successfully", "success")
            return redirect(url_for("admin.panel"))
        except IntegrityError:
            db.session.rollback()
            flash("Duplicate entry detected!", "danger")
            return redirect(url_for("admin.create_admin"))
    return render_template("create_admin.html")

@admin_bp.route("/employees")
@role_required("admin")
def employees():
    employees = Employee.query.all()
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template("employees.html", employees=employees, admin_name=admin_name)

@admin_bp.route("/employee/<int:employee_id>")
@role_required("admin")
def view_employee(employee_id):

    employee = Employee.query.get_or_404(employee_id)
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template(
        "view_employee.html",
        admin_name=admin_name,
        employee=employee
                )

@admin_bp.route("/employee/<int:employee_id>/status", methods=["POST"])
@role_required("admin")
def update_employee_status(employee_id):
    status = request.form.get("status")

    if status not in ["active", "inactive", "blocked"]:
        flash("Invalid status selected!", "error")
        return redirect(url_for("admin.employees"))

    employee = Employee.query.get_or_404(employee_id)
    employee.status = status
    db.session.commit()

    flash(f"Employee status updated to {status.upper()}", "success")
    return redirect(url_for("admin.employees"))

@admin_bp.route("/create_employee", methods=["GET", "POST"])
@role_required("admin")
def create_employee():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

    json_path = os.path.join("utils", "StateCityData.json")
    with open(json_path) as f:
        state_data = json.load(f)

    if request.method == "POST":
        name = request.form['name']
        mobile = request.form['mobile']
        password = request.form['password']
        email = request.form.get('email')
        role = request.form['role']
        state = request.form['state']
        district = request.form['district']
        joining_date_str = request.form['joining_date']
        joining_date = datetime.strptime(joining_date_str, "%Y-%m-%d").date()

        state = state.strip().lower() if state else None
        district = district.strip().lower() if district else None

        existing_employee = Employee.query.filter_by(mobile=mobile).first()
        if existing_employee:
            flash("Mobile number already exists!", "danger")
            return redirect(url_for("admin.create_employee"))
        
        employee = Employee(
            name=name,
            mobile=mobile,
            email=email,
            role=role,
            state=state,
            district=district,
            joining_date=joining_date
        )
        employee.set_password(password)

        try:
            db.session.add(employee)
            db.session.commit()
            flash("Employee created successfully", "success")
            return redirect(url_for("admin.employees"))
        except:
            db.session.rollback()
            flash("Duplicate entry detected!", "danger")
            return redirect(url_for("admin.create_employee"))
    return render_template(
        "create_employee.html",
        admin_name=admin_name,
        state_data=state_data
    )

@admin_bp.route("/courses_plans")
@role_required("admin")
def courses_plans():
    courses = AdmissionCourse.query.all()
    registrationPlans = RegistrationPlan.query.all()
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template("courses.html", courses=courses, registrationPlans=registrationPlans, admin_name=admin_name)

@admin_bp.route("/create_course", methods=["GET", "POST"])
@role_required("admin")
def create_course():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = float(request.form.get("price"))

        course = AdmissionCourse(
            title=title,
            description=description,
            price=price,
            discount=Decimal("0.00"),
            real_price=price, 
            status="active"
        )

        db.session.add(course)
        db.session.commit()

        flash("Course created successfully", "success")
        return redirect(url_for("admin.courses_plans"))
    
    return render_template("create_course.html", admin_name=admin_name)
    
@admin_bp.route("/create_registration_plan", methods=["GET", "POST"])
@role_required("admin")
def create_registration_plan():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name

    if request.method == "POST":
        plan_name = request.form.get("plan_name")
        amount = float(request.form.get("amount"))
        partner_commission = float(request.form.get("partner_commission"))

        registration_plan = RegistrationPlan(
            plan_name=plan_name,
            amount=amount,
            partner_commission=partner_commission,
            status="active"
        )

        db.session.add(registration_plan)
        db.session.commit()

        flash("Plan created successfully", "success")
        return redirect(url_for("admin.courses_plans"))

    return render_template("create_registration_plan.html", admin_name=admin_name)

@admin_bp.route("/course/<int:course_id>")
@role_required("admin")
def view_course(course_id):
    course = AdmissionCourse.query.get_or_404(course_id)
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template("view_course.html", admin_name=admin_name, course=course)

@admin_bp.route("/course/update/<int:course_id>", methods=["POST"])
@role_required("admin")
def update_course(course_id):
    course = AdmissionCourse.query.get_or_404(course_id)
    status = request.form.get("status")
    discount = Decimal(request.form.get("discount", 0))

    course.discount = discount
    course.status = status
    course.apply_discount()

    db.session.commit()
    flash("Course updated successfully", "success")

    return redirect(url_for("admin.courses_plans"))

@admin_bp.route("/plan/<int:plan_id>")
@role_required("admin")
def view_plan(plan_id):
    plan = RegistrationPlan.query.get_or_404(plan_id)
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template("view_plan.html", admin_name=admin_name, plan=plan)

@admin_bp.route("/plan/update/<int:plan_id>", methods=["POST"])
@role_required("admin")
def update_plan(plan_id):
    plan = RegistrationPlan.query.get_or_404(plan_id)
    status = request.form.get("status")

    plan.status = status

    db.session.commit()
    flash("Plan updated successfully", "success")

    return redirect(url_for("admin.courses_plans"))

@admin_bp.route("/payments")
@role_required("admin")
def payments():
    payments = Payment.query.all()
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    return render_template("payments.html", payments=payments,  admin_name=admin_name)

@admin_bp.route("/payment/<int:payment_id>/status", methods=["POST"])
@role_required("admin")
def update_partner_payment(payment_id):
    status = request.form.get("status")

    if status not in ["pending", "success", "failed"]:
        flash("Invalid status selected!", "error")
        return redirect(url_for("admin.payments"))

    payment = Payment.query.get_or_404(payment_id)
    payment.status = status

    if status == "success":
        payment.released_date = datetime.utcnow()
    else:
        payment.released_date = None

    db.session.commit()

    flash(f"Payment status updated to {status.upper()}", "success")
    return redirect(url_for("admin.payments"))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@admin_bp.route("/download_leads_template")
@role_required("admin")
def download_leads_template():

    headers = [
        "student_name",
        "mobile",
        "email",
        "current_status",
        "address",
        "remark"
    ]

    def generate():
        yield ",".join(headers) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=leads_template.csv"}
    )

@admin_bp.route("/upload_leads", methods=["GET", "POST"])
@role_required("admin")
def upload_leads():

    if request.method == "POST":
        try:
            employee_id = request.form.get("employee_id")

            if not employee_id:
                flash("Please select employee", "danger")
                return redirect(request.url)

            employee_id = int(employee_id)

            file = request.files.get("file")
            if not file or file.filename == "":
                flash("No file selected", "danger")
                return redirect(request.url)

            if not allowed_file(file.filename):
                flash("Only CSV files allowed", "danger")
                return redirect(request.url)

            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
            file.save(filepath)

            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                required_columns = [
                    "student_name",
                    "mobile",
                    "email",
                    "current_status",
                    "address",
                    "remark"
                ]

                if not all(col in reader.fieldnames for col in required_columns):
                    flash("CSV format invalid", "danger")
                    return redirect(request.url)

                leads_to_insert = []

                for row in reader:
                    # Skip empty rows
                    if not row.get("mobile"):
                        continue

                    leads_to_insert.append({
                        "student_name": row["student_name"],
                        "mobile": row["mobile"],
                        "email": row.get("email"),
                        "current_status": row.get("current_status"),
                        "address": row.get("address"),
                        "remark": row.get("remark"),
                        "status": "Pending",
                        "assigned_to": employee_id
                    })

                if not leads_to_insert:
                    flash("No valid data found in CSV", "warning")
                    return redirect(request.url)

                # 🔥 BULK INSERT (FAST + SAFE)
                db.session.execute(
                    text("""
                        INSERT INTO leads
                        (student_name, mobile, email, current_status,
                         address, remark, status, created_at, assigned_to)
                        VALUES
                        (:student_name, :mobile, :email, :current_status,
                         :address, :remark, :status, NOW(), :assigned_to)
                    """),
                    leads_to_insert
                )

                db.session.commit()

            flash(f"{len(leads_to_insert)} Leads uploaded successfully", "success")

        except Exception as e:
            db.session.rollback()
            print("UPLOAD ERROR:", str(e))  # 🔴 server log ke liye
            flash("Upload failed due to server error", "danger")

        return redirect(url_for("admin.leads"))

    employees = Employee.query.all()
    return render_template("leads.html", employees=employees)

@admin_bp.route("/queries")
@role_required("admin")
def queries():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    support_queries = SupportQuery.query.all()

    return render_template("queries.html", admin_name=admin_name, support_queries=support_queries)

@admin_bp.route("/query/<int:query_id>/status", methods=["POST"])
@role_required("admin")
def update_query_status(query_id):
    status = request.form.get("status")

    if status not in ["pending", "processing", "resolved", "rejected"]:
        flash("Invalid status selected!", "error")
        return redirect(url_for("admin.queries"))

    query = SupportQuery.query.get_or_404(query_id)
    query.status = status

    db.session.commit()

    flash(f"Query status updated to {status.upper()}", "success")
    return redirect(url_for("admin.queries"))

@admin_bp.route("/schemes")
@role_required("admin")
def schemes():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    schemes = Scheme.query.all()

    return render_template("schemes.html", admin_name=admin_name, schemes=schemes)

@admin_bp.route("/schemes/<int:scheme_id>/status", methods=["POST"])
@role_required("admin")
def update_scheme_status(scheme_id):
    status = request.form.get("status")

    if status not in ["active", "inactive"]:
        flash("Invalid status selected!", "error")
        return redirect(url_for("admin.schemes"))

    scheme = Scheme.query.get_or_404(scheme_id)
    scheme.status = status
    db.session.commit()

    flash(f"Scheme status updated to {status.upper()}", "success")
    return redirect(url_for("admin.schemes"))

@admin_bp.route("/create_scheme", methods=["GET", "POST"])
@role_required("admin")
def create_scheme():
    admin_id = get_jwt_identity()
    admin_name = Admin.query.get(admin_id).name
    if request.method == "POST":
        name = request.form.get("name")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        image_file = request.files.get("image")

        UPLOAD_FOLDER = "static/uploads/schemes"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        if image_file:
            try:
                # Open image using Pillow
                img = Image.open(image_file)

                # Convert to RGB (important for PNG with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Create unique name using date + uuid
                today_str = datetime.now().strftime("%Y%m%d")
                unique_id = uuid.uuid4().hex[:8]
                filename = f"scheme_{today_str}_{unique_id}.webp"

                relative_path = f"uploads/schemes/{filename}"
                full_path = os.path.join("static", relative_path)

                # Resize (optional – recommended for popup)
                max_size = (1200, 1200)
                img.thumbnail(max_size)

                # Save as WEBP with quality control
                img.save(full_path, "WEBP", quality=75, optimize=True)

                new_scheme = Scheme(
                    name=name,
                    image=relative_path,
                    start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                    end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                    status="inactive"
                )

                db.session.add(new_scheme)
                db.session.commit()
                flash("Scheme added successfully!", "success")
                return redirect(url_for("admin.schemes"))
            
            except:
                flash("Image upload failed!", "danger")
            return redirect(url_for("admin.create_scheme"))
    return render_template("create_scheme.html", admin_name=admin_name)        