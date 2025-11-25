from flask import Blueprint, request, jsonify
from db import db
from models import User
from flask_login import login_user, logout_user

auth = Blueprint("auth", __name__)


# -------- REGISTER --------
@auth.post("/register")
def register():
    data = request.get_json() or {}

    # Basic validation
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if not (name and email and phone and password):
        return jsonify({"error": "name, email, phone and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "Phone already used"}), 400

    user = User(name=name, email=email, phone=phone)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": "Database error", "detail": str(exc)}), 500

    # Auto-login using Flask-Login only after successful commit
    login_user(user)

    return jsonify({"message": "Registered", "user_id": user.id}), 201


# -------- LOGIN --------
@auth.post("/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not (email and password):
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)

    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "name": user.name
    }), 200


# -------- LOGOUT --------
@auth.get("/logout")
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})