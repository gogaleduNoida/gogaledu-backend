from flask import request, jsonify, Blueprint, send_file, Response
from models import User, ScholarshipSlab, StudentCourse, CoursePricing, Student, StudentPayment, Order, UserProfile, Certificate
from extensions import db   
from flask_jwt_extended import create_access_token, set_access_cookies, verify_jwt_in_request, get_jwt_identity, jwt_required, unset_jwt_cookies
from datetime import datetime, timedelta
from PIL import Image
import os
import razorpay
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from config import Config
import uuid
from functools import wraps
from services.email_service import send_email
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import secrets
import csv  

user_bp = Blueprint("api", __name__)

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if user.role != role:
                return {"message":"Unauthorized"},403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@user_bp.route("/signup", methods=["POST", "GET"])
def signup():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    # Check if already exists
    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({"success": False, "message": "Email already exists"}), 400

    new_user = User(username=username, email=email)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    send_email(
        to_email=email,
        subject="🎉 Registration Successful!",
        template="emails/welcome.html",
        name=username,
        company="GogalEdu Academy",
        date=datetime.now().strftime("%d %B %Y"),
        logo_url="https://gogaledu.com/logo.jpg",
        website_url="https://gogaledu.com",
        address="Muzaffarnagar, Uttar Pradesh",
        phone="+91 7011418073"
    )

    return jsonify({
        "success": True,
        "message": "Signup successful",
        "username": username
    }), 201

@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    if not user.check_password(password):
        return jsonify({"success": False, "message": "Wrong password"}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    response =  jsonify({
        "success": True,
        "message": "Login successful",
        "username": user.username,
        "role": user.role
    })

    set_access_cookies(response, access_token)
    return response, 200

@user_bp.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Logged out"})
    unset_jwt_cookies(response)
    return response

@user_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"success": False, "message": "All fields required"}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    
    if not check_password_hash(user.password_hash, old_password):
        return jsonify({"success": False, "message": "Old password incorrect"}), 400
    
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"success": True, "message": "Password changed successfully"})

@user_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "message": "Email not found"}), 404

    # Generate secure token
    token = secrets.token_urlsafe(32)

    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)

    db.session.commit()

    # Reset link
    reset_link = f"http://localhost:3000/reset-password/{token}"

    send_email(
        to_email=email,
        subject="Reset Your Password",
        template="emails/reset_password.html",
        reset_link=reset_link,
        name=user.username
    )

    return jsonify({"success": True, "message": "Reset email sent"})

@user_bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    data = request.get_json()
    new_password = data.get("new_password")

    if not new_password:
        return jsonify({"success": False, "message": "Password required"}), 400

    user = User.query.filter_by(reset_token=token).first()

    if not user:
        return jsonify({"success": False, "message": "Invalid token"}), 400

    # Check expiry
    if user.reset_token_expiry < datetime.utcnow():
        return jsonify({"success": False, "message": "Token expired"}), 400

    # Update password
    user.password_hash = generate_password_hash(new_password)

    # Clear token
    user.reset_token = None
    user.reset_token_expiry = None

    db.session.commit()

    return jsonify({"success": True, "message": "Password reset successful"})

@user_bp.route('/check-auth', methods=['GET'])
@jwt_required()
def check_auth():
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()


        if not user_id:
            return jsonify({"authenticated": False}), 200

        user = User.query.get(user_id)

        if not user:
            return jsonify({"authenticated": False}), 200

        return jsonify({
            "authenticated": True,
            "username": user.username
        }), 200

    except Exception as e:
        return jsonify({"authenticated": False}), 200
    
@user_bp.route("/scholarship", methods=["POST"])
@jwt_required()
def scholarship():

    user_id = get_jwt_identity()

    data = request.get_json()
    percentage = data.get("percentage")

    if not percentage:
        return jsonify({"message": "Percentage required"}), 400

    user = UserProfile.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"message": "User not found, Firstly complete profile"}), 404

    user.intermediate_percentage = percentage
    db.session.commit()

    return jsonify({
        "message": "Scholarship percentage saved"
    }), 200

@user_bp.route("/scholarship-slabs")
def scholarship_slabs():

    slabs = ScholarshipSlab.query.all()

    result = []

    for slab in slabs:
        result.append({
            "min_percentage": slab.min_percentage,
            "max_percentage": slab.max_percentage,
            "discount_amount": slab.discount_amount
        })

    return jsonify({"slabs":result})

@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():

    user_id = get_jwt_identity()

    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()

    image_url = None

    if profile and profile.profile_photo:
        image_url = f"/static/uploads/users/id_{user.id}/{profile.profile_photo}"

    profile_completed = False

    if profile:
        profile_completed = all([
            profile.father_name,
            profile.whatsapp_number,
            profile.intermediate_roll_number,
            profile.city,
            profile.state,
            profile.address
        ])

    return jsonify({
        "username": user.username,
        "email": user.email,
        "father_name": profile.father_name if profile else None,
        "whatsapp_number": profile.whatsapp_number if profile else None,
        "intermediate_roll_number": profile.intermediate_roll_number if profile else None,
        "percentage_verification_status": profile.percentage_verification_status if profile else None,
        "intermediate_percentage": profile.intermediate_percentage if profile else None,
        "graduation_status": profile.graduation_status if profile else None,
        "city": profile.city if profile else None,
        "state": profile.state if profile else None,
        "address": profile.address if profile else None,
        "profile_photo": image_url,
        "profile_completed": profile_completed
    })

@user_bp.route("/profile", methods=["POST"])
@jwt_required()
def update_profile():

    user_id = get_jwt_identity()
    user = UserProfile.query.filter_by(user_id=user_id).first()

    if not user:
        user = UserProfile(user_id=user_id)
        db.session.add(user)

    user.father_name = request.form.get("father_name")
    user.whatsapp_number = request.form.get("whatsapp_number")
    user.intermediate_roll_number = request.form.get("intermediate_roll_number")
    user.graduation_status = request.form.get("graduation_status")
    user.city = request.form.get("city")
    user.state = request.form.get("state")
    user.address = request.form.get("address")

    UPLOAD_FOLDER = "static/uploads/users"
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_IMAGE_SIZE = 2 * 1024 * 1024

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    user_folder = os.path.join(UPLOAD_FOLDER, f"id_{user_id}")
    os.makedirs(user_folder, exist_ok=True)

    old_photo = user.profile_photo
   
    if "photo" in request.files:
        photo = request.files["photo"]

        if photo.filename == "":
            return jsonify({"message": "No file selected"}), 400

        if not allowed_file(photo.filename):
            return jsonify({"message": "Invalid image format"}), 400

        photo.seek(0, os.SEEK_END)
        size = photo.tell()
        photo.seek(0)

        if size > MAX_IMAGE_SIZE:
            return jsonify({"message": "Image size must be under 2MB"}), 400

        date = datetime.now().strftime("%Y%m%d%H%M%S")

        filename = f"user_{user_id}_{date}.webp"
        path = os.path.join(user_folder, filename)

        image = Image.open(photo)
        image.convert("RGB").save(path, "WEBP", quality=80)

        user.profile_photo = filename

        if old_photo:
            old_path = os.path.join(user_folder, old_photo)
            if os.path.exists(old_path):
                os.remove(old_path)

    db.session.commit()

    return jsonify({"message": "Profile updated successfully"})

@user_bp.route("/course/<slug>", methods=["GET"])
def get_course(slug):

    course = StudentCourse.query.filter_by(slug=slug).first()

    if not course:
        return jsonify({"error": "Course not found"}), 404

    pricing = CoursePricing.query.filter_by(course_id=course.id).first()

    return jsonify({
        "title": course.title,
        "slug": course.slug,
        "pricing": {
            "base_fee": pricing.base_fee,
            "registration_fee": pricing.registration_fee,
            "online_discount": pricing.online_discount,
            "full_payment_discount": pricing.full_payment_discount,
            "laptop_price": pricing.laptop_price
        }
    })

@user_bp.route("/course-confirmation/<slug>", methods=["GET"])
@jwt_required()
def course_confirmation(slug):

    user_id = get_jwt_identity()

    user = UserProfile.query.filter_by(user_id=user_id).first()

    course = StudentCourse.query.filter_by(slug=slug).first()

    if not course:
        return jsonify({"message": "Course not found"}), 404

    pricing = CoursePricing.query.filter_by(course_id=course.id).first()

    # scholarship logic
    scholarship_discount = 0
    verified = False
    percentage = None
    status = None

    if user:
        percentage = user.intermediate_percentage
        status = user.percentage_verification_status

        if status == "verified":
            slabs = ScholarshipSlab.query.all()

            for slab in slabs:

                if percentage and slab.min_percentage <= int(percentage) <= slab.max_percentage:
                    scholarship_discount = slab.discount_amount
                    verified = True
                    break

    return jsonify({

        "course": {
            "title": course.title,
            "slug": course.slug
        },

        "pricing": {
            "base_fee": pricing.base_fee,
            "registration_fee": pricing.registration_fee,
            "online_discount": pricing.online_discount,
            "full_payment_discount": pricing.full_payment_discount,
            "laptop_price": pricing.laptop_price
        },

        "scholarship": {
            "verified": verified,
            "discount": scholarship_discount,
            "percentage": user.intermediate_percentage,
            "status": user.percentage_verification_status
        }

    })

@user_bp.route("/sp-course-confirmation/<slug>", methods=["GET"])
@jwt_required()
def sp_course_confirmation(slug):

    course = StudentCourse.query.filter_by(slug=slug).first()
    if not course:
        return jsonify({"message": "Course not found"}), 404

    pricing = CoursePricing.query.filter_by(course_id=course.id).first()

    return jsonify({
        "course": {
            "title": course.title,
            "slug": course.slug
        },
        "pricing": {
           "base_fee": pricing.base_fee
                   
         }
    })


client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_SECRET_KEY))

def generate_student_id(course_slug):

    year = datetime.now().year
    course_code = course_slug[:2].upper()
    unique = str(uuid.uuid4())[:6].upper()
    return f"GEDU{year}-{course_code}-{unique}"

@user_bp.route("/create-order", methods=["POST"])
@jwt_required()
def create_order():

    user_id = get_jwt_identity()
    data = request.json

    course_slug = data.get("course_slug")
    mode = data.get("mode")
    laptop = data.get("laptop")
    payment_type = data.get("payment_type")

    course = StudentCourse.query.filter_by(slug=course_slug).first()

    if not course:
        return jsonify({"status": "error", "message": "Course not found"}), 404

    pricing = CoursePricing.query.filter_by(course_id=course.id).first()

    amount = pricing.base_fee

    if mode == "online":
        amount -= pricing.online_discount

    if payment_type == "full":
        amount -= pricing.full_payment_discount

    if laptop:
        amount += pricing.laptop_price

    if payment_type == "registration":
        amount = pricing.registration_fee

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })

    new_order = Order(
        order_id=order["id"],
        user_id=user_id,
        course_slug=course_slug,
        mode=mode,
        laptop=laptop,
        payment_type=payment_type,
        amount=amount,
        status="created"
    )

    db.session.add(new_order)
    db.session.commit()

    return jsonify({
        "status": "success",
        "order_id": order["id"]
    })

@user_bp.route("/order/<order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):

    user_id = get_jwt_identity()

    order = Order.query.filter_by(
        order_id=order_id,
        user_id=user_id
    ).first()

    if not order:
        return jsonify({
            "status": "error",
            "message": "Order not found"
        }), 404

    return jsonify({
        "order_id": order.order_id,
        "amount": order.amount,
        "course_slug": order.course_slug,
        "mode": order.mode,
        "laptop": order.laptop
    })

def generate_receipt(student):

    receipts_dir = "static/receipts"

    if not os.path.exists(receipts_dir):
        os.makedirs(receipts_dir)

    path = f"{receipts_dir}/{student.student_id}.pdf"

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    
    logo_path = "static/images/logo.jpg"

    if os.path.exists(logo_path):
        c.drawImage(logo_path, 40, height - 80, width=120, height=50)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, height - 60, "GogalEdu Academy")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(180, height - 75, "Muzaffarnagar, Uttar Pradesh")
    c.drawString(180, height - 90, "Phone: +91 7011418073")

    c.setStrokeColor(colors.grey)
    c.line(40, height - 100, width - 40, height - 100)

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(40, height - 130, "PAYMENT RECEIPT")

    y = height - 160

    c.setFont("Helvetica", 11)

    def draw_row(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(180, y, str(value))
        y -= 20

    draw_row("Student ID", student.student_id)
    draw_row("Name", student.name)
    draw_row("Course", student.course_slug.replace("-", " ").title())

    date = student.enrollment_date.strftime("%d %B %Y")
    draw_row("Enrollment Date", date)

    # ---------------- COURSE DETAILS ----------------
    y -= 10
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Course Details")
    y -= 20

    c.setFont("Helvetica", 11)
    draw_row("Course Duration", "6 Months") 
    draw_row("Mode", student.mode.upper())

    # ---------------- PAYMENT DETAILS ----------------
    y -= 10
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Payment Details")
    y -= 20

    draw_row("Payment ID", student.payment_id)
    draw_row("Order ID", student.order_id)

    amount_text = f"INR {student.amount:,.2f}"
    draw_row("Amount Paid", amount_text)

    # ---------------- LAPTOP SECTION ----------------
    if int(student.laptop_required or 0) == 1:
        y -= 10
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, y, "Laptop Configuration")
        y -= 20

        c.setFont("Helvetica", 11)
        c.drawString(60, y, "- Intel i5 Processor")
        y -= 18
        c.drawString(60, y, "- 8GB RAM")
        y -= 18
        c.drawString(60, y, "- 256GB SSD")
        y -= 18
        c.drawString(60, y, "- Security Amount INR 18,700 (Refundable)")
        y -= 20

    # ---------------- TERMS ----------------
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Terms & Conditions")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(60, y, "- Fees once paid are non-refundable.")
    y -= 15
    c.drawString(60, y, "- Laptop security will be refunded after return.")
    y -= 30

    # ---------------- FOOTER ----------------
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(40, 80, "This is a system-generated receipt.")

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(width - 200, 100, "Authorized Signature")

    c.line(width - 200, 95, width - 80, 95)

    c.save()

    return path

@user_bp.route("/download-receipt/<student_id>", methods=["GET"])
@jwt_required()
def download_receipt(student_id):

    user_id = int(get_jwt_identity())

    student = Student.query.filter_by(student_id=student_id).first()

    if not student:
        return jsonify({"message": "Receipt not found"}), 404

    order = Order.query.filter_by(order_id=student.order_id).first()

    if order.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    path = f"static/receipts/{student_id}.pdf"

    if not os.path.exists(path):
        return jsonify({"message": "Receipt not generated"}), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=f"{student_id}_receipt.pdf"
    )

@user_bp.route("/verify-payment", methods=["POST"])
@jwt_required()
def verify_payment():

    try:

        data = request.get_json() or {}

        order_id = data.get("order_id")
        payment_id = data.get("payment_id")
        signature = data.get("signature")

        if not order_id or not payment_id or not signature:
            return jsonify({"status":"failed","message":"Missing payment data"}),400


        order = Order.query.filter_by(order_id=order_id).first()

        if not order:            
            return jsonify({"status":"failed","message":"Order not found"}),404


        if order.status == "paid":
            return jsonify({"status":"failed","message":"Already processed"}),400


        # verify signature
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id":order_id,
                "razorpay_payment_id":payment_id,
                "razorpay_signature":signature
            })
        except Exception as e:
            print("SIGNATURE ERROR:",e)
            return jsonify({"status":"failed","message":"Invalid signature"}),400


        # fetch razorpay payment
        try:
            razorpay_payment = client.payment.fetch(payment_id)
            print("RAZORPAY DATA:",razorpay_payment)
        except Exception as e:
            print("FETCH ERROR:",e)
            return jsonify({"status":"failed","message":"Razorpay fetch failed"}),400


        if razorpay_payment.get("status") not in ["captured","authorized"]:
            return jsonify({"status":"failed","message":"Payment not captured"}),400


        # amount check
        if(int(razorpay_payment["amount"]) != int(order.amount * 100)
            or razorpay_payment["currency"] != "INR"):
            print("AMOUNT MISMATCH:",razorpay_payment["amount"],order.amount)
            return jsonify({"status":"failed","message":"Amount mismatch"}),400


        student_id = generate_student_id(order.course_slug)
        user = User.query.get(order.user_id)
        profile = UserProfile.query.filter_by(user_id=order.user_id).first()

        student = Student(
            student_id=student_id,
            name=user.username if user.username else "Student",
            email=user.email,
            phone=profile.whatsapp_number if profile else None,
            course_slug=order.course_slug,
            payment_id=payment_id,
            order_id=order_id,
            amount=order.amount,
            payment_status="paid",
            mode=order.mode,
            laptop_required=order.laptop,
            enrollment_date=datetime.utcnow()
        )

        db.session.add(student)


        payment_record = StudentPayment(
            student_id=student_id,
            order_id=order_id,
            payment_id=payment_id,
            amount=order.amount,
            currency="INR",
            status="success",
            payment_date=datetime.utcnow()
        )

        db.session.add(payment_record)


        order.status="paid"

        db.session.commit()


        # receipt optional
        try:
            receipt_path = generate_receipt(student)
            payment_record.receipt_url = receipt_path
            db.session.commit()

            send_email(
                to_email=student.email,
                subject="🎉 Payment Successful - Invoice Attached",
                template="emails/payment_success.html",

                name=student.name,
                student_id=student.student_id,
                payment_id=student.payment_id,
                order_id=student.order_id,
                amount=student.amount,
                course=student.course_slug,
                date=student.enrollment_date.strftime("%d %B %Y"),

                logo_url="https://gogaledu.com/logo.jpg",
                website_url="https://gogaledu.com",
                company="GogalEdu Academy",
                address="Muzaffarnagar, Uttar Pradesh",
                phone="+91 7011418073",

                attachments=[receipt_path]
            )
        except Exception as e:
            print("RECEIPT ERROR:",e)


        return jsonify({
            "status":"success",
            "student_id":student_id,
            "order_id":order_id,
            "amount":order.amount
        })


    except Exception as e:

        print("VERIFY ERROR:",e)

        db.session.rollback()

        return jsonify({
            "status":"error",
            "message":str(e)
        }),500

@user_bp.route("/my-courses", methods=["GET"])
@jwt_required()
def my_courses():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    students = Student.query.filter_by(email=user.email).all()

    courses_data = []

    for s in students:
        course = StudentCourse.query.filter_by(slug=s.course_slug).first()

        payments = StudentPayment.query.filter_by(
            student_id=s.student_id
        ).order_by(StudentPayment.payment_date.desc()).all()

        latest_payment = payments[0] if payments else None

        courses_data.append({
            "title": course.title if course else None,
            "slug": course.slug if course else None,
            "enrollment_date": s.enrollment_date,
            "amount": s.amount,
            "receipt_url": latest_payment.receipt_url if latest_payment else None,
            "payment_status": latest_payment.status if latest_payment else None
        })

    return {"courses": courses_data}

@user_bp.route("/verify-certificate", methods=["POST"])
def verify_certificate():
    try:
        data = request.get_json()
        print(data)

        if not data or "certificate_id" not in data:
            return jsonify({
                "success": False,
                "message": "Certificate ID is required"
            }), 400

        cert_id = data.get("certificate_id").strip().upper()
        print(cert_id)

        certificate = Certificate.query.filter_by(certificate_id=cert_id).first()

        if not certificate:
            return jsonify({
                "success": False,
                "message": "Certificate not found"
            }), 404

        return jsonify({
            "success": True,
            "data": certificate.to_dict(),
            "message": "Certificate verified successfully"
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500

@user_bp.route("/admin/dashboard", methods=["GET"])
@jwt_required()
@role_required("admin")
def dashboard():

    # USERS
    users = db.session.query(
    User.id,
    User.username,
    User.email,
    UserProfile.whatsapp_number
).outerjoin(UserProfile, User.id == UserProfile.user_id)\
 .filter(User.role == "user").all()


    users_data = []

    for u in users:
        users_data.append({
            "id": u.id,
            "name": u.username,
            "email": u.email,
            "phone": u.whatsapp_number
                            })


    # STUDENTS
    students = Student.query.all()

    students_data = []

    for s in students:
        students_data.append({
            "student_id": s.student_id,
            "name": s.name,
            "email": s.email,
            "phone": s.phone,
            "course_slug": s.course_slug,
            "payment_status": s.payment_status
        })


    # EMPLOYEES
    employees = User.query.filter_by(role="employee").all()

    employee_data = []

    for e in employees:
        employee_data.append({
            "id": e.id,
            "name": e.username,
            "email": e.email
        })


    return jsonify({
         "counts": {
        "users": len(users_data),
        "students": len(students_data),
        "employees": len(employee_data)
    },
        "users": users_data,
        "students": students_data,
        "employees": employee_data
    })

@user_bp.route("/admin/create-employee", methods=["POST"])
@jwt_required()
@role_required("admin")
def create_employee():

    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({
            "success": False,
            "message": "All fields required"
        }), 400


    existing = User.query.filter_by(email=email).first()

    if existing:
        return jsonify({
            "success": False,
            "message": "Email already exists"
        }), 400


    employee = User(
        username=username,
        email=email,
        role="employee"
    )

    employee.set_password(password)

    db.session.add(employee)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Employee created successfully"
    }), 201

@user_bp.route("/admin/download-certificates-template")
@jwt_required()
@role_required("admin")
def download_certificates_template():

    headers = [
        "certificate_id",
        "student_name",
        "student_email",
        "course_name"
    ]

    def generate():
        yield ",".join(headers) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment;filename=certificates_template.csv"
        }
    )

@user_bp.route("/admin/create-certificates", methods=["POST"])
@jwt_required()
@role_required("admin")
def upload_certificates():

    file = request.files.get("file")

    if not file:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"success": False, "message": "Only CSV allowed"}), 400

    filepath = os.path.join("uploads", secure_filename(file.filename))
    os.makedirs("uploads", exist_ok=True)
    file.save(filepath)

    inserted = 0
    errors = []

    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            required_columns = [
                "certificate_id",
                "student_name",
                "student_email",
                "course_name"
            ]

            if not all(col in reader.fieldnames for col in required_columns):
                return jsonify({"success": False, "message": "Invalid CSV format"}), 400

            rows = list(reader)

            if len(rows) > 50:
                return jsonify({"success": False, "message": "Max 50 certificates allowed"}), 400

            for row in rows:
                try:
                    cert_id = row["certificate_id"].strip().upper()

                    if not cert_id:
                        continue

                    exists = Certificate.query.filter_by(certificate_id=cert_id).first()
                    if exists:
                        continue

                    file_path = f"static/upload/certificates/{cert_id}.png"

                    cert = Certificate(
                        certificate_id=cert_id,
                        student_name=row["student_name"].strip(),
                        student_email=row["student_email"].strip(),
                        course_name=row["course_name"].strip(),
                        is_valid=True,
                        file_path=file_path
                    )

                    db.session.add(cert)
                    inserted += 1

                except Exception as e:
                    errors.append(str(e))

            try:
                db.session.commit()
            except:
                db.session.rollback()
                return jsonify({"success": False, "message": "Database error"}), 500

        return jsonify({
            "success": True,
            "inserted": inserted,
            "message": f"{inserted} certificates uploaded successfully",
            "errors": errors
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    

@user_bp.route("/employee/users",methods=["GET"])
@jwt_required()
@role_required("employee")
def get_users():

    profiles = db.session.query(
        UserProfile.user_id,
        User.username,
        User.email,
        UserProfile.whatsapp_number,
        UserProfile.intermediate_roll_number,
        UserProfile.intermediate_percentage,
        UserProfile.percentage_verification_status
    ).join(User, User.id == UserProfile.user_id).all()

    users = []

    for p in profiles:
        users.append({
            "user_id": p.user_id,
            "name": p.username,
            "email": p.email,
            "phone": p.whatsapp_number,
            "roll_no": p.intermediate_roll_number,
            "percentage": p.intermediate_percentage,
            "status": p.percentage_verification_status
        })

    return jsonify({"users": users})

@user_bp.route("/employee/verify-percentage/<int:user_id>",methods=["PUT"])
@jwt_required()
@role_required("employee")
def verify_percentage(user_id):

    data = request.get_json()
    status = data.get("status")

    if status not in ["verified", "failed", "unverified"]:
        return {"message": "Invalid status"}, 400

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    if not profile:
        return {"message": "Profile not found"}, 404

    profile.percentage_verification_status = status
    db.session.commit()

    return {"message": "Verification status updated"}


