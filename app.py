from flask import Flask, redirect, url_for
from config import Config
from extensions import db, jwt, cors
from admin.routes import admin_bp
from partner.routes import partner_bp
from auth.routes import auth_bp
from employee.routes import employee_bp
from user.routes import user_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)    
    jwt.init_app(app)
    # cors.init_app(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)

    cors.init_app(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": "http://localhost:3000"}}
)

    @app.context_processor
    def inject_user():
        from flask_jwt_extended import verify_jwt_in_request, get_jwt
        try:
            verify_jwt_in_request(optional=True)
            claims = get_jwt()
            return {
                "current_user": {
                    "name": claims.get("name"),
                    "role": claims.get("role")
                } if claims else None
            }
        except Exception as e:
            return {"current_user": None}

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        return redirect(url_for("auth.login"))

    @jwt.expired_token_loader
    def expired_callback(jwt_header, jwt_payload):
        return redirect(url_for("auth.login"))

    @jwt.invalid_token_loader
    def invalid_callback(reason):
        return redirect(url_for("auth.login"))

    @jwt.revoked_token_loader
    def revoked_callback(jwt_header, jwt_payload):
        return redirect(url_for("auth.login"))
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(partner_bp, url_prefix="/partner")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(employee_bp, url_prefix="/employee")
    app.register_blueprint(user_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return "<h1>Welcome to Gogaledu - website under maintenance </h1>"

    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
# app = create_app()
