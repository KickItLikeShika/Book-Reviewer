import os, json
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
from flask_login import logout_user, login_required, LoginManager
import gc
from flask_session import Session
import requests
from helpers import login_required

# Start a flask app
app = Flask(__name__)

# Connect to thea database
engine = create_engine("postgres://qrugxbfzhodefb:67970bf8ea7c2b5d9fde6f6c2d6e971a0c43b652e16abadd740d831ff1527e12@ec2-34-193-232-231.compute-1.amazonaws.com:5432/dals1ukovsebn9")
db = scoped_session(sessionmaker(bind=engine))

app.secret_key = 'super secret key'

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# Sessions
Session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# The main route
@app.route("/")
@login_required
def index():
    """Display the search box."""
    # Render the home page
    print(session["username"])
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register with a username and a password."""
    # POST
    if request.method == 'POST':
        # Get the username and the password
        username = request.form.get("username")
        password = request.form.get("password")
        # Username session
        session["username"] = username
        # Determine if the username is in the Database 
        if db.execute("SELECT * FROM users WHERE username = :username",
                    {"username": username}).rowcount == 1:
            # If True return error
            flash("Username is taken")
            return render_template("register.html")
        # If False register
        db.execute("INSERT INTO users (username, password) VALUES(:username, :password)",
                    {"username": username, "password": password})
        # Save the changes to the database
        db.commit()
        # Go to the main page
        return redirect("/")
    # GET
    else:
        # Display the reigster page
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in with the username and the password."""
    # Forget any username
    session.clear()
    # POSt
    if request.method == 'POST':
        # Get the username and the password
        username = request.form.get("username")
        password = request.form.get("password")
        # THe sessions for the current username
        session["username"] = username
        # See if the username and the password in the database
        if db.execute("SELECT * FROM users WHERE username = :username AND password = :password",
                    {"username": username, "password": password}).rowcount == 1:
            # If True go to the main page
            return redirect("/")
        # If False display error
        flash("Invalid username or password")
        return render_template("login.html")
    # GET
    else:
        # Display the login page
        return render_template("login.html")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Search for books."""
    # If no search diplay error
    if not request.form.get("search"):
        return render_template("error.html")

    # Getting the search
    srchs = "%" + request.form.get("search") + "%"
    # Capitalize the first letters
    srchs = srchs.title()

    # See if there is any match in the database
    rows = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn LIKE :srchs OR \
                        title LIKE :srchs OR \
                        author LIKE :srchs LIMIT 15",
                        {"srchs": srchs})
    # If no match display error
    if rows.rowcount == 0:
        return render_template("error.html")

    # List all the results
    books = rows.fetchall()
    # Display the results
    return render_template("search_res.html", srchs=books)

@app.route("/book/<isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
    """The book page."""
    # Intialize a warning varialbe
    warning = ""
    # Get the current logged in username
    username = session.get('username') 
    session["reviews"] = []
    # Get the isbn of the book and the username of the user to see if it's the second review
    secondreview = db.execute("SELECT * FROM reviews WHERE isbn = :isbn AND username= :username",{"username": username, "isbn": isbn}).fetchone()
    
    # If the first review then submit it
    if request.method == "POST" and secondreview == None:
        # Get the review content and the rating
        review = request.form.get('textarea') 
        rating = request.form.get('stars')
        # Submit the review
        db.execute("INSERT INTO reviews (isbn, review, rating, username) VALUES (:a, :b, :c, :d)",{"a": isbn, "b": review, "c": rating, "d": username})
        # Save to the database
        db.commit()
    
    # If second review display warning
    if request.method == "POST" and secondreview!=None:
        warning = "Sorry. You cannot add second review."
    
    # API request to Goodreads
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "AxbGBzQ7eIylIV9m7m9pw", "isbns": isbn})
    # Get the number of the ratings and the average rate for each book from Goodreads API
    average_rating = res.json()['books'][0]['average_rating']
    work_ratings_count = res.json()['books'][0]['work_ratings_count']
    reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn",{"isbn":isbn}).fetchall() 
    
    # Append reviews to make all the user see it
    for y in reviews:
        session['reviews'].append(y)  
    
    # Get the isbn of the book
    data = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
    # Display the book page and submit the reviews
    return render_template("book.html", data=data, reviews=session['reviews'], average_rating=average_rating, work_ratings_count=work_ratings_count, username=username, warning=warning)


@app.route("/api/<isbn>", methods = ["GET"])
@login_required
def api(isbn):
    """API request from Goodreads."""
    # Get the isbn
    data = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    
    # If nothing found return not found
    if data == None:
        return ('NOT FOUND')

    # Make the API req
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "AxbGBzQ7eIylIV9m7m9pw", "isbns": isbn})
    # The avreage rating for each book
    average_rating = res.json()['books'][0]['average_rating']
    # The total ratings for each book
    work_ratings_count = res.json()['books'][0]['work_ratings_count']
    
    # API req JSON
    x = {
    "title": data.title,
    "author": data.author,
    "year": data.year,
    "isbn": isbn,
    "review_count": work_ratings_count,
    "average_score": average_rating
    }
    
    # Mkae it JSON
    api = json.dumps(x)
    with open('templates/api.json', 'w') as outfile:
        json.dump(api, outfile)
    # Display the json 
    return render_template("api.json", api=api)

@app.route("/logout")
@login_required
def logout():
    """Logout."""
    # Clear the sessions
    session.clear()
    gc.collect()
    return redirect("/login")