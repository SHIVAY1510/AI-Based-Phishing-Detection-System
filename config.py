import os

class Config:
    SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost/Database_URL"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCERET_KEY = "d17a6822af9ea28fe8752ac86d327113"

    #MAIL_SERVER = 'smtp.gmail.com'
    #MAIL_PORT = 587
    #MAIL_USE_TLS = True
    #MAIL_USERNAME = 'yourgmail@gmail.com'
    #MAIL_PASSWORD = 'gmail_app_password'  


#class Config:
#    # Require a Postgres DATABASE_URL for production use. Set it before starting the app.
#    # Example (PowerShell):
#    DATABASE_URL = 'postgresql://postgres:1234@localhost:5432/database_URL'
#    DATABASE_URL = os.getenv("DATABASE_URL")
#    if not DATABASE_URL:
#        raise RuntimeError(
#            "DATABASE_URL is not set. Set the environment variable to your Postgres URI,\n"
#            "for example: postgresql://flaskuser:password1234@localhost:5432/dbname"
#        )
#
#    # Enforce PostgreSQL scheme to avoid accidental SQLite or other DB usage
#    lower = DATABASE_URL.lower()
#    if not (lower.startswith('postgresql://') or lower.startswith('postgres://')):
#        raise RuntimeError("DATABASE_URL must start with postgresql://")
#       #print("⚠️ WARNING: DATABASE_URL is not a PostgreSQL URI. Using fallback local Postgres instead.")
#       #DATABASE_URL = "postgresql://postgres:password1234@localhost:5432/testdb"
#
#    SQLALCHEMY_DATABASE_URI = DATABASE_URL
#    SQLALCHEMY_TRACK_MODIFICATIONS = False
#    # Enable SQLAlchemy echo when SQLALCHEMY_ECHO=1 or true in env for debugging
#    SQLALCHEMY_ECHO = str(os.getenv("SQLALCHEMY_ECHO", "False")).lower() in ("1", "true", "yes")
#    SECRET_KEY = os.getenv("SECRET_KEY", "d17a6822af9ea28fe8752ac86d327113")