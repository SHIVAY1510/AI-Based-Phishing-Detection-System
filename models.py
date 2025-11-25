from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
from flask_login import UserMixin


# USER MODEL
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    urls = db.relationship("URLRecord", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# URL MODEL
class URLRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False)
    #user_email = db.Column(db.String(150), db.ForeignKey("user.email"), nullable=False)
    url = db.Column(db.String(350), nullable=False)
    result = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)