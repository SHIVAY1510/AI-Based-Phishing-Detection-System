from config import Config
from db import init_db, db
from auth import auth
from models import User, URLRecord
from url_routes import urls
from utils import get_gravatar_url, get_ui_avatar_url, get_google_profile_picture
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user
from flask_login import LoginManager
import re
import pickle
from flask_mail import Message,Mail
from flask_login import login_required
from itsdangerous import URLSafeTimedSerializer

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Configure mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'noreply@example.com')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS

app.config.from_object(Config)
mail = Mail(app)

# Debug: Check if mail config is loaded
if not app.config['MAIL_USERNAME']:
    print("WARNING: MAIL_USERNAME not set. Email features will not work. Set it in .env file.")
else:
    print(f"Mail configured for: {app.config['MAIL_USERNAME']}")

# Load ML artifacts safely so missing pickles don't crash the whole app at import time.
vector = None
model = None
try:
    with open("vectorizer.pkl", "rb") as f:
        vector = pickle.load(f)
except Exception as e:
    print("Warning: could not load 'vectorizer.pkl' — ML features disabled:", e)

try:
    with open("phishing.pkl", "rb") as f:
        model = pickle.load(f)
except Exception as e:
    print("Warning: could not load 'phishing.pkl' — ML model disabled:", e)

#Password reset token function
def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email,salt='password-reset-salt')

# Returns the email if the token is valid, otherwise returns None
def verify_reset_token(token, expiration=3600): #valid for (3600s) i.e. 1 hour
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email=serializer.loads(token, salt='password-reset-salt',max_age=expiration)
        return email
    except Exception as e:
        return None

#def mailSetup():
 #   app.config['MAIL_SERVER']='smtp.gmail.com'
  #  app.config['MAIL_PORT']=587
   # app.config['MAIL_USE_TLS']=True
   # app.config['MAIL_USERNAME']= os.getenv('MAIL_USERNAME')
   # app.config['MAIL_PASSWORD']= os.getenv('MAIL_PASSWORD')
   # mail= Mail(app)
   # return mail
#mail=mailSetup()
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("Token expired or invalid", "error")
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found", "error")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not new_password or not confirm_password:
            flash("Both password fields are required", "error")
            return render_template("reset_password.html", token=token)
        
        if new_password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("reset_password.html", token=token)
        
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long", "error")
            return render_template("reset_password.html", token=token)
        
        try:
            user.set_password(new_password)
            db.session.commit()
            flash("Password updated successfully", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating password: {str(e)}", "error")
            return render_template("reset_password.html", token=token)

    return render_template("reset_password.html", token=token)


@app.route("/")
def home():
    return render_template("index.html")  # Ensure you have an index.html file in the templates folder

@app.route("/url", methods=["GET", "POST"])
@login_required
def url():
    if request.method == "POST":
        url_input = request.form.get('url')
        if not url_input:
            return render_template("index.html", prediction="Please enter a URL")
        
        cleaned_url = re.sub(r'^https?://(www\.)?', '', url_input)
        my_prediction = "Unable to classify"

        if vector is None or model is None:
            my_prediction = "Model unavailable — cannot classify URL"
        else:
            try:
                vect = vector.transform([cleaned_url])[0]
                my_prediction = model.predict(vect)

                if my_prediction == 'good':
                    my_prediction = "The URL is Legitimate/Safe"
                elif my_prediction == 'bad':
                    my_prediction = "The URL is Phishing"
                else:
                    my_prediction = "Unable to determine the URL status"
            except Exception as e:
                print(f'Error predicting URL: {e}')
                my_prediction = "Error classifying URL"

        # Save the result when a user is logged in (moved outside ML condition)
        if current_user and getattr(current_user, 'is_authenticated', False):
            try:
                save = URLRecord(user_id=current_user.id, url=url_input, result=my_prediction)
                db.session.add(save)
                db.session.commit()
                print(f'[OK] Saved URL record for user {current_user.id}')
            except Exception as e:
                db.session.rollback()
                print(f'[ERROR] Error saving URLRecord: {e}')
        else:
            print(f'Not logged in. current_user: {current_user}, authenticated: {getattr(current_user, "is_authenticated", False)}')

        return render_template("urlcheck.html", prediction=my_prediction)
    else:
        return render_template("urlcheck.html")
    
# Forgot Password Route
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Email not found", "error")
            return redirect(url_for('forgot_password'))

        token = generate_reset_token(email)
        reset_link = url_for('reset_password', token=token, _external=True)

        # Check if email config is set
        if not app.config.get('MAIL_USERNAME'):
            print("[ERROR] Email configuration error: MAIL_USERNAME not set")
            flash("Email service is not configured. Please contact administrator.", "error")
            return redirect(url_for('forgot_password'))

        msg = Message(
            subject="Password Reset Request - Phishing Detection URL System",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"""Hello,

You requested a password reset for your account. Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

Best regards,
Phishing Detection URL System Team"""
        
        msg.html = f"""
<html>
  <body>
    <p>Hello,</p>
    <p>You requested a password reset for your account. Click the link below to reset your password:</p>
    <p><a href="{reset_link}" style="background-color: #2ecc72; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
    <p>This link will expire in 1 hour.</p>
    <p>If you did not request this, please ignore this email.</p>
    <p>Best regards,<br>Phishing Detection URL System Team</p>
  </body>
</html>"""
        
        try:
            mail.send(msg)
            print(f"[OK] Password reset email sent successfully to {email}")
            flash("Password reset link sent to your email. Check your inbox or spam folder.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"[ERROR] Mail error: {e}")
            print(f"Mail config - Server: {app.config.get('MAIL_SERVER')}, Port: {app.config.get('MAIL_PORT')}, Username: {app.config.get('MAIL_USERNAME')}")
            flash(f"Error sending email. Please try again later. Error: {str(e)}", "error")
            return redirect(url_for('forgot_password'))

    return render_template("reset_password.html")

@app.route("/register",methods=["GET", "POST"])
def register():
    if request.method=="POST":
        name=request.form.get('name')
        email=request.form.get('email')
        phone=request.form.get('phone')
        password=request.form.get('password')
        
        # Validate inputs (phone is optional)
        if not all([name, email, password]):
            return "Name, email and password are required", 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return "Email already registered", 400
        if User.query.filter_by(phone=phone).first():
            return "Phone already registered", 400
        
        try:
            user = User(name=name, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)        
            db.session.commit()
            print(f"[OK] Registered user id={user.id} email={user.email}")
            # Auto-login after registration
            login_user(user)
            flash("Successfully Registered")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {e}")
            return f"Registration failed: {e}", 500
    return render_template("registration.html")

@app.route("/login",methods=["GET", "POST"])
def login():
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        user=User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    """Log the user out and redirect to the login page."""
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

#@app.route("/dashboard")
#def dashboard():
#    return render_template("dashboard.html")

@app.route("/dashboard")
@login_required
def dashboard():

    # Total URLs searched by this user
    total_urls = URLRecord.query.filter_by(user_id=current_user.id).count()

    # Safe URL count
    safe_count = URLRecord.query.filter_by(user_id=current_user.id, result="The URL is Legitimate/Safe").count()

    # Phishing URL count
    phishing_count = URLRecord.query.filter_by(user_id=current_user.id, result="The URL is Phishing").count()

    # Recent 10 searches
    recent_searches = URLRecord.query.filter_by(user_id=current_user.id).order_by(URLRecord.timestamp.desc()).limit(10).all()

    # Generate a nice avatar based on user's name with consistent color based on email
    avatar_url = get_ui_avatar_url(current_user.name, current_user.email, size=256)

    return render_template(
        "dashboard.html",
        total_urls=total_urls,
        safe_count=safe_count,
        phishing_count=phishing_count,
        recent_searches=recent_searches,
        user=current_user,
        avatar_url=avatar_url
    )

@app.route("/details/<int:id>")
@login_required
def details(id):
    """Display detailed information about a specific URL record."""
    # Fetch the URL record and ensure it belongs to the current user
    record = URLRecord.query.filter_by(id=id, user_id=current_user.id).first()
    
    if not record:
        flash("URL record not found or you don't have permission to view it.", "error")
        return redirect(url_for("dashboard"))
    
    return render_template("details.html", record=record)

@app.route("/about")
def about():
    """Display the About page."""
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Display the Contact page and handle contact form submissions."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        
        # Validate form data
        if not name or not email or not message:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("contact"))
        
        try:
            # Send email to admin
            msg = Message(
                subject=f"New Contact Message from {name}",
                recipients=[app.config['MAIL_USERNAME']],
                body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
            )
            mail.send(msg)
            
            # Send confirmation email to user
            confirmation_msg = Message(
                subject="We received your message",
                recipients=[email],
                body=f"Hi {name},\n\nThank you for contacting us. We have received your message and will get back to you soon.\n\nBest regards,\nPhishing Detection URL System Team"
            )
            mail.send(confirmation_msg)
            
            flash("Your message has been sent successfully! We will get back to you soon.", "success")
            return redirect(url_for("contact"))
        except Exception as e:
            print(f"Error sending email: {e}")
            flash(f"Failed to send message. Please try again later. Error: {str(e)}", "error")
            return redirect(url_for("contact"))
    
    return render_template("contact.html")

# Load configuration (reads `DATABASE_URL` env var when provided)
app.config.from_object(Config)

init_db(app)

with app.app_context():
    db.create_all()

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(urls)

if __name__ == "__main__":
    app.run(debug=True)