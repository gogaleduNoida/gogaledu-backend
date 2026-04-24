from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_jwt_extended import get_jwt_identity
from models import Lead, Employee
from extensions import db
from auth.routes import role_required
from datetime import datetime
import pytz

employee_bp = Blueprint("employee", __name__, template_folder="templates/employee")

IST = pytz.timezone("Asia/Kolkata")

def utc_to_ist(dt):
    if not dt:
        return None
    return dt.replace(tzinfo=pytz.utc).astimezone(IST)

@employee_bp.route("/workbench", methods=["GET"])
@role_required("employee")
def workbench():
    employee_id = get_jwt_identity()
    employee = Employee.query.get_or_404(employee_id)

    if employee.status != "active":
        flash("Your account is blocked by Admin", "error")
        return redirect(url_for("auth.logout"))

    leads = Lead.query.filter_by(
        assigned_to=employee.id
    ).all()

    for l in leads:
        l.remark_updated_at_ist = utc_to_ist(l.remark_updated_at)

    return render_template("workbench.html", employee=employee, leads=leads)


@employee_bp.route("/add-remark", methods=["POST"])
@role_required("employee")
def add_remark():
    employee_id = get_jwt_identity()
    employee = Employee.query.get_or_404(employee_id)

    if employee.status != "active":
        flash("Your account is blocked by Admin", "error")
        return redirect(url_for("auth.logout"))

    lead_id = request.form.get("lead_id")
    remark = request.form.get("remark")

    if not lead_id or not remark:
        flash("Remark is required", "error")
        return redirect(url_for("employee.workbench"))

    lead = Lead.query.get_or_404(lead_id)

    lead.remark = remark
    lead.remark_updated_at = datetime.utcnow() 
    db.session.commit()

    flash("Remark saved successfully", "success")
    return redirect(url_for("employee.workbench"))
