from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    __bind_key__ = 'gogaledu'
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    role = db.Column(
        db.Enum('user','admin','employee', name='role_enum'),
        default='user'
    )
    
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    profile = db.relationship(
        "UserProfile",
        backref="user",
        uselist=False,
        cascade="all, delete"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class UserProfile(db.Model):
    __bind_key__ = 'gogaledu'
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    father_name = db.Column(db.String(120))
    whatsapp_number = db.Column(db.String(20))

    intermediate_percentage = db.Column(db.String(50))

    percentage_verification_status = db.Column(
        db.Enum('unverified', 'verified', 'failed', name='percentage_verify_enum'),
        default='verified'
    )

    intermediate_roll_number = db.Column(db.String(50))

    graduation_status = db.Column(
        db.Enum('Final Year', 'Completed', 'Not Yet', name='graduation_status_enum'),
        nullable=True
    )

    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    address = db.Column(db.Text)

    profile_photo = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ScholarshipSlab(db.Model):
    __bind_key__ = 'gogaledu'
    __tablename__ = "scholarship_slabs"

    id = db.Column(db.Integer, primary_key=True)
    min_percentage = db.Column(db.Integer, nullable=False)
    max_percentage = db.Column(db.Integer, nullable=False)
    discount_amount = db.Column(db.Integer, nullable=False)

class StudentCourse(db.Model):
    __bind_key__ = "gogaledu"
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)

    pricing = db.relationship("CoursePricing", backref="course", uselist=False)

class CoursePricing(db.Model):
    __bind_key__ = "gogaledu"
    __tablename__ = "course_pricing"

    id = db.Column(db.Integer, primary_key=True)

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id"),
        nullable=False
    )

    base_fee = db.Column(db.Integer, default=32000)
    registration_fee = db.Column(db.Integer, default=5000)
    online_discount = db.Column(db.Integer, default=4000)
    full_payment_discount = db.Column(db.Integer, default=2000)
    laptop_price = db.Column(db.Integer, default=18700)

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

class Student(db.Model):
    __bind_key__ = "gogaledu"
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    course_slug = db.Column(db.String(120))
    payment_id = db.Column(db.String(120))
    order_id = db.Column(db.String(120))
    amount = db.Column(db.Integer)
    payment_status = db.Column(db.String(50))
    mode = db.Column(db.String(20))
    laptop_required = db.Column(db.String(10))
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)

class StudentPayment(db.Model):
    __bind_key__ = "gogaledu"
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50))
    order_id = db.Column(db.String(120))
    payment_id = db.Column(db.String(120))
    amount = db.Column(db.Integer)
    currency = db.Column(db.String(10))
    status = db.Column(db.String(20))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    receipt_url = db.Column(db.Text)

class Order(db.Model):
    __bind_key__ = "gogaledu"
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(120), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    course_slug = db.Column(db.String(120))
    mode = db.Column(db.String(20))
    laptop = db.Column(db.Boolean)
    payment_type = db.Column(db.String(20))
    amount = db.Column(db.Integer)
    status = db.Column(db.String(20), default="created")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Certificate(db.Model):
    __bind_key__ = 'gogaledu'
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)    
    certificate_id = db.Column(db.String(50), unique=True, nullable=False, index=True)    
    student_name = db.Column(db.String(100), nullable=False)
    student_email = db.Column(db.String(120), nullable=False)
    course_name = db.Column(db.String(200), nullable=False)    
    is_valid = db.Column(db.Boolean, default=True)
    file_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "certificateId": self.certificate_id,
            "studentName": self.student_name,
            "courseName": self.course_name,
            "status": "Valid" if self.is_valid else "Invalid",
            "createdAt": self.created_at.strftime("%d %B %Y"),
            "downloadUrl": f"/api/download-certificate/{self.certificate_id}"
        }