from extensions import db
from decimal import Decimal
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Partner(db.Model):
    __tablename__ = "partner"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profession = db.Column(db.String(100))
    status = db.Column(
    db.Enum('active', 'inactive', 'blocked', name='partner_status'),
    default='active',
    nullable=False
)   
    bank_name = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(100))
    account_number = db.Column(db.String(30))
    ifsc_code = db.Column(db.String(20))
    bank_proof = db.Column(db.String(255))
    bank_details_locked = db.Column(db.Boolean, default=False)

    firm_category_id = db.Column(
        db.Integer,
        db.ForeignKey('firm_categories.id'),
        nullable=False
    )

    firm_name = db.Column(db.String(150))
    firm_proof = db.Column(db.String(255))
    profile_image = db.Column(db.String(255))
    
    leads = db.relationship('Lead', backref='partner', lazy=True)
    payments = db.relationship('Payment', backref='partner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def profile_complete(self):
        required_fields = [
            self.profession,
            self.bank_name,
            self.account_holder_name,
            self.account_number,
            self.ifsc_code,
            self.bank_proof,
            self.firm_name,
            self.firm_proof,
        ]

        return all(field and str(field).strip() != "" for field in required_fields)


class FirmCategory(db.Model):
    __tablename__ = "firm_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    partners = db.relationship('Partner', backref='firm_category_ref', lazy=True)


class Lead(db.Model):
    __tablename__ = "leads"   

    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255))
    current_status = db.Column(db.String(255))
    state = db.Column(db.String(100))
    district = db.Column(db.String(100))
    address = db.Column(db.String(500))
    status = db.Column(
        db.Enum('Pending', 'In-Process', 'Converted', 'Not Converted', name='lead_status_enum'),
        default='Pending',
        nullable=False
    )
    payment_term = db.Column(
        db.Enum('Cash', 'Online', 'Other', name='payment_term_enum'),
        default=None,
        nullable=True
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey('courses.id', ondelete='SET NULL'),
        nullable=True
    )

    remark = db.Column(db.Text, nullable=True)
    remark_updated_at = db.Column(db.DateTime, nullable=True)  

    registration_plan_id = db.Column(
        db.Integer,
        db.ForeignKey('registration_plans.id', ondelete="SET NULL"),
        nullable=True
    )

    registration_plan = db.relationship(
        "RegistrationPlan",
        backref="leads"
    )

    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey('employee.id', ondelete='SET NULL'),
        nullable=True
    )

    assigned_employee = db.relationship(
        "Employee",
        backref="leads"
    )

    course = db.relationship('AdmissionCourse', backref='leads')
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payment = db.relationship('Payment', backref='lead', uselist=False)


class Employee(db.Model):
    __tablename__ = "employee"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(255))

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(
        db.Enum('sales_executive', 'counselor', 'manager', name='employee_role'),
        nullable=False
    )
    state = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    joining_date = db.Column(db.Date, default=date.today)

    status = db.Column(
        db.Enum('active', 'inactive', 'blocked', name='employee_status'),
        default='active',
        nullable=False
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

class AdmissionCourse(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(5, 2), default=Decimal("0.00"))
    real_price = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(
        db.Enum("active", "inactive", name="course_status"),
        default="active",
        nullable=False
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def apply_discount(self):
        discount_amount = (self.price * self.discount) / Decimal("100")
        self.real_price = self.price - discount_amount


class RegistrationPlan(db.Model):
    __tablename__ = "registration_plans"

    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    partner_commission = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum("active", "inactive", name="plan_status"),
        default="active",
        nullable=False
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Payment(db.Model):
    __tablename__ = "payment"

    id = db.Column(db.Integer, primary_key=True)

    partner_id = db.Column(
        db.Integer,
        db.ForeignKey('partner.id', ondelete="CASCADE"),
        nullable=False
    )

    lead_id = db.Column(
        db.Integer,
        db.ForeignKey('leads.id', ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    commission_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    status = db.Column(
        db.Enum('pending', 'success', 'failed', name='payment_status_enum'),
        default='pending'
    )

    released_date = db.Column(db.DateTime, nullable=True)

class SupportQuery(db.Model):
    __tablename__ = "support_queries"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(100), nullable=False)

    role = db.Column(
        db.Enum("partner", "employee", "other", name="role_enum"),
        nullable=False
    )

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.Enum("pending", "processing", "resolved", "rejected", name="query_status_enum"),
        default="pending",
        nullable=False
    )

    sent_at = db.Column(db.DateTime, default=datetime.utcnow)


class Scheme(db.Model):
    __tablename__ = "schemes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(
    db.Enum('active', 'inactive', name='scheme_status'),
    default='inactive',
    nullable=False
)   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
