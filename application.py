import os

from flask import Flask, session, render_template, request, url_for, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from my_lib import login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# prevent responses being cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    ''' Homepage '''
    return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    ''' User login page '''
    if request.method == "POST":

        # Clear session to prevent users accessing others accounts (forget other user_id)
        session.clear();

        # Check username exists

        # Check if password correct

        # If all fine, save user_id in session and then redirect to homepage
        return redirect(url_for('/'))

    res = db.execute("INSERT INTO users (name, password) VALUES ('barl', 'yat')")

    # if request.method == "GET"
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    ''' User register page '''
    if request.method == "POST":

        # Check if username already taken

        # Check password and confirmation password match

        # if all fine, insert data into database and redirect to login page
        return redirect(url_for('login'))

    # if request.method == "GET"
    return render_template("register.html")
