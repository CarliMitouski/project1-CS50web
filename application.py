import os

from flask import Flask, session, render_template, request, url_for, redirect, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.security import check_password_hash, generate_password_hash
from my_lib import login_required
import requests

# import requests
# res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "KEY", "isbns": "9781632168146"})
# print(res.json())

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


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    ''' Homepage '''
    if request.method == "POST":
        books = []
        search = request.form["search"].strip();

        # Check each isbn, title, author and year until match (or not)

        # check if search is an int
        try:
            search = int(search);
            year_check = db.execute(f"SELECT title, author, isbn FROM books WHERE year = :Year", {"Year": search}).fetchall()
            isbn_check = db.execute(f"SELECT title, author, isbn FROM books WHERE isbn LIKE \'%{search}%\'").fetchall()
            if year_check or isbn_check:
                return render_template("search.html", books=year_check + isbn_check)

        except:
            # if seach is a str
            title_check = db.execute(f"SELECT title, author, isbn FROM books WHERE title LIKE \'%{search}%\'").fetchall()
            author_check = db.execute(f"SELECT title, author, isbn FROM books WHERE author LIKE \'%{search}%\'").fetchall()
            isbn_check = db.execute(f"SELECT title, author, isbn FROM books WHERE isbn LIKE \'%{search}%\'").fetchall()
            if title_check or author_check or isbn_check:
                return render_template("search.html", books=title_check + author_check + isbn_check)

        return render_template("search.html", books=[["NA"]])

    # if request.method == "GET"
    return render_template("search.html")


@app.route("/logout")
def logout():
    ''' Log user out '''

    # Clear previous users session
    session.clear()

    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    ''' User login page '''
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Clear session to prevent users accessing others accounts (forget other user_id)
        session.clear();

        # Check username exists
        name_check = db.execute("SELECT name FROM users WHERE name = :Name", {"Name": username}).fetchall()
        if name_check == []:
            return render_template("error.html", code=403, msg="Can NOT find username.")

        # Check if password correct
        hash = db.execute("SELECT password FROM users WHERE name = :Name", {"Name": username}).fetchall()[0][0]
        if not check_password_hash(hash, password):
            return render_template("error.html", code=403, msg="Incorrect password.")

        # If all fine, save user_id in session and then redirect to homepage
        user_id = db.execute("SELECT id FROM users WHERE name = :Name", {"Name": username}).fetchall()[0][0]
        print(user_id)
        session["user_id"] = user_id

        return redirect(url_for("index"))

    # if request.method == "GET"
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    ''' User register page '''
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Check if username already taken
        name_check = db.execute("SELECT name FROM users WHERE name = :name", {"name": username}).fetchall()
        if name_check != []:
            return render_template("error.html", code=403, msg="Name taken.")

        # Check password and confirmation password match
        if password != confirmation:
            return render_template("error.html", code=403, msg="passwords do NOT match.")

        # if all fine, insert data into database and redirect to login page
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (name, password) VALUES (:Name, :Password)",
                    {"Name": username, "Password": hash})
        db.commit()

        return redirect(url_for('login'))

    # if request.method == "GET"
    return render_template("register.html")



@app.route("/<bookisbn>", methods=["GET", "POST"])
@login_required
def goodreads_API(bookisbn):
    ''' Page with book info (ratings and reviews) and
    input box for user to make review '''
    if request.method == "POST":
        # Take rating and review made by user and store into 'reviews' table
        # and then reload page with now updated rating and review(s)
        rating = request.form.get("rating")
        review = request.form.get("review")

        # Check rating and review actually entered
        if not rating:
            return render_template("error.html", code="400", msg="Please enter a rating")

        if not review:
            return render_template("error.html", code="400", msg="Please write a review")

        bookisbn = bookisbn.split(" ")[1] # remove 'isbn: ' part of string
        bookisbn_id = db.execute("SELECT id FROM books WHERE isbn = :Isbn", {"Isbn": bookisbn}).fetchall()
        db.execute("INSERT INTO reviews (user_id, book_id, user_comment, user_rating) VALUES (:User_id, :Book_id, :User_comment, :User_rating)",
                   {"User_id": session["user_id"], "Book_id": bookisbn_id[0][0], "User_comment": review, "User_rating": rating})
        db.commit()

    # if request.method == "GET"
    try:
        # Check isbn exists, if yes continue getting title and author from database,
        # else return error page
        data = db.execute("SELECT title, author FROM books WHERE isbn = :Isbn", {"Isbn": bookisbn}).fetchall()[0];

        # Send request to goodreads API and using json-ed response pass to books.html
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "wLFlJUFFRQuF4KnqtFr6sA", "isbns": str(bookisbn)})
        book = res.json()['books'][0]
        bookinfo = ['isbn: ' + str(book['isbn']),
                    'ratings count: ' + str(book['ratings_count']),
                    'reviews count: ' + str(book['reviews_count']),
                    'average rating: ' + str(book['average_rating'])]

        # Check database for reviews
        bookisbn = bookisbn.split(" ")[0] # remove 'isbn: ' part of string
        reviews_check = db.execute("SELECT * FROM books JOIN reviews ON reviews.book_id = books.id WHERE isbn = :Isbn", {"Isbn": bookisbn}).fetchall()

        # Get names for each comment
        reviews_names = []
        for _ in reviews_check:
            reviews_names.append(_[6])

        for i in range(len(reviews_names)):
            name_db = db.execute("SELECT name FROM users WHERE id = :Id", {"Id": reviews_names[i]}).fetchall()[0][0]
            reviews_names[i] = name_db

        review_data = []
        for book, user in zip(reviews_check, reviews_names):
            review_data.append([book, user])

        return render_template("book.html", bookinfo=bookinfo, data=data, bookreviews=review_data)

    except:
        return render_template("error.html", code=404, msg="isbn could NOT be found.")
