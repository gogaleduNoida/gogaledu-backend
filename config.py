import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
    # SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = "mysql://root:0522nivesh123@localhost:3306/admission"
    SQLALCHEMY_BINDS = { "gogaledu": "mysql://root:0522nivesh123@localhost:3306/gogaledu"}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt_dev_secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)    
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_COOKIE_SECURE = False        
    JWT_COOKIE_SAMESITE = "Lax"    
    JWT_COOKIE_CSRF_PROTECT = False

    # JWT_COOKIE_DOMAIN = ".gogaledu.com"
    # SESSION_COOKIE_DOMAIN = ".gogaledu.com"
    
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    UPLOAD_FOLDER = "static/uploads"
    ALLOWED_EXTENSIONS = ("csv",)

    RAZORPAY_KEY_ID=os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_SECRET_KEY=os.getenv("RAZORPAY_SECRET_KEY")


    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
