from config import Config
from db import init_db, db
from auth import auth
from models import User, URLRecord
from url_routes import urls
from flask import Flask, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user
from flask_login import LoginManager
import re
import pickle

app = Flask(__name__)
app.secret_key = Config.SCERET_KEY

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

@app.route("/")
def home():
    return render_template("homepage.html")  # Ensure you have an index.html file in the templates folder 

@app.route("/url", methods=["GET", "POST"])
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
            print(f"✓ Registered user id={user.id} email={user.email}")
            # Auto-login after registration
            login_user(user)
            return redirect(url_for("home"))
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
            flash("Logged in successfully.")
            return redirect(url_for("home"))
        else:
            return "Invalid credentials. Please try again."         
    return render_template("login.html")


 
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

# Register blueprints
app.register_blueprint(auth)
app.register_blueprint(urls)

if __name__ == "__main__":
    app.run(debug=True)