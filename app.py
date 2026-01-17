from config import Config
from db import init_db, db
from auth import auth
from models import User, URLRecord
from url_routes import urls
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
app.secret_key = Config.SCERET_KEY

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'noreply@example.com')

app.config.from_object(Config)
mail = Mail(app)

# Debug: Check if mail config is loaded
if not app.config['MAIL_USERNAME']:
    print("⚠️  WARNING: MAIL_USERNAME not set. Email features will not work. Set it in .env file.")
else:
    print(f"✓ Mail configured for: {app.config['MAIL_USERNAME']}")

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

def mailSetup():
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT']=587
    app.config['MAIL_USE_TLS']=True
    app.config['MAIL_USERNAME']= os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD']= os.getenv('MAIL_PASSWORD')
    mail= Mail(app)
    return mail
mail=mailSetup()
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        return "Token expired or invalid"

    user = User.query.filter_by(email=email).first()

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        user.set_password(new_password)
        db.session.commit()
        flash("Password updated successfully", "success")
        return redirect(url_for('login'))

    return render_template("reset_password.html", token=token)


@app.route("/")
def home():
    return render_template("homepage.html")  # Ensure you have an index.html file in the templates folder 

@app.route("/about")
def about():
    return render_template("about.html")

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
                print(f'✓ Saved URL record for user {current_user.id}')
            except Exception as e:
                db.session.rollback()
                print(f'✗ Error saving URLRecord: {e}')
        else:
            print(f'Not logged in. current_user: {current_user}, authenticated: {getattr(current_user, "is_authenticated", False)}')

        return render_template("index.html", prediction=my_prediction)
    else:
        return render_template("index.html")
    
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

        msg = Message(
            "Password Reset",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Click to reset password:\n{reset_link}"
        try:
            mail.send(msg)
            flash("Password reset link sent to your email. Check your inbox or spam folder.", "success")
        except Exception as e:
            print("Mail error:", e)
            flash(f"Error sending email. Please try again. Error: {str(e)}", "error")
            return redirect(url_for('forgot_password'))
        
        return redirect(url_for('login'))

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
            flash("Name, email and password are required", "error")
            return redirect(url_for('register'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please use a different email or login.", "error")
            return redirect(url_for('register'))
        if User.query.filter_by(phone=phone).first():
            flash("Phone number already registered. Please use a different phone number.", "error")
            return redirect(url_for('register'))
        
        try:
            user = User(name=name, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)        
            db.session.commit()
            print(f"✓ Registered user id={user.id} email={user.email}")
            # Auto-login after registration
            login_user(user)
            flash("Successfully registered! Redirecting to login...", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {e}")
            flash(f"Registration failed: {str(e)}", "error")
            return redirect(url_for('register'))
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

    # Fetch last 5 searches of the logged-in user
    recent_searches = (
        URLRecord.query
        .filter_by(user_id=current_user.id)
        .order_by(URLRecord.timestamp.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        total_urls=total_urls,
        safe_count=safe_count,
        phishing_count=phishing_count,
        recent_searches=recent_searches,
        user=current_user
    )


 
# Load configuration (reads `DATABASE_URL` env var when provided)
app.config.from_object(Config)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:1234@localhost/Database_URL"


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

# Contact Page Route (GET)
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return render_template('contact.html')
    
    # POST method - handle form submission
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    if not all([name, email, message]):
        flash("All fields are required", "error")
        return redirect(url_for('contact'))
    
    try:
        # Send email to admin
        msg = Message(
            f"New Contact Form Submission from {name}",
            sender=app.config['MAIL_USERNAME'],
            recipients=['Shivayawasthi02@gmail.com']
        )
        msg.body = f"""
New message from: {name}
Email: {email}

Message:
{message}
        """
        mail.send(msg)
        flash("Thank you! Your message has been sent successfully.", "success")
    except Exception as e:
        print(f"Contact form error: {e}")
        flash("Error sending message. Please try again later.", "error")
    
    return redirect(url_for('contact'))

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(urls)

if __name__ == "__main__":
    app.run(debug=True)