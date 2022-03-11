import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
uri = os.getenv("DATABASE_URL")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # create table
    """try:
        db.execute("CREATE TABLE IF NOT EXISTS buy_info (id_user, symbol TEXT NOT NULL, company_name TEXT NOT NULL, price_symbol REAL,date_buy TEXT NOT NULL, number_shares INTEGER, FOREIGN KEY(id_user) REFERENCES users(id))")
    except:
        return apology("cannot execute")"""

    try:
        row1 = db.execute(
        "SELECT  cash, symbol, company_name, price_symbol, date_buy FROM users, buy_info WHERE id = ? GROUP BY (buy_info.symbol, users.cash)", session["user_id"])
    except:
        return apology("row1 error line 57")

    try:
        symbols = db.execute("SELECT DISTINCT(symbol) FROM users, buy_info WHERE id = ?", session["user_id"])
    except:
        return apology("error line 63")

    number = {}

    for symbol in symbols:
        sum_shares = db.execute(
            "SELECT SUM(number_shares) as na FROM users, buy_info WHERE id = ? AND symbol=?", session["user_id"], symbol["symbol"])
        if symbol["symbol"] not in number:
            number[symbol["symbol"]] = sum_shares[0]["na"]
        else:
            number[symbol["symbol"]] += sum_shares[0]["na"]

    total = 0
    for row in row1:
        total = total + number[row["symbol"]] * row["price_symbol"]

    return render_template("portfolio.html", row1=row1, number_of_shares=number, total=total, leng_row=len(row1))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # if request via get
    if request.method == "GET":
        return render_template("buy.html")

    else:
        # get user input
        name_symbol = request.form.get("symbol")
        number_of_shares = request.form.get("shares")
        lookup_result = lookup(name_symbol)
        # if no input or invalid
        try:
            int_number_of_shares = int(number_of_shares)
        except:
            return apology("invalid number of shares")
        if not name_symbol or not number_of_shares or not lookup_result or not int(number_of_shares) or int(number_of_shares) < 1:
            return apology("enter valid symbol and shares")
        else:
            # create table
            # db.execute("CREATE TABLE IF NOT EXISTS buy_info (id_user, symbol TEXT NOT NULL, company_name TEXT NOT NULL, price_symbol REAL,date_buy TEXT NOT NULL, number_shares INTEGER, FOREIGN KEY(id_user) REFERENCES users(id))")

            # check if the user cab buy
            rows = db.execute("select cash from users where id = ?", session["user_id"])[0]
            cash_user = float(rows["cash"])
            if cash_user < lookup_result["price"] * int(number_of_shares):
                return apology("cannot offerd")

            date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO buy_info (id_user, symbol, company_name, price_symbol, date_buy, number_shares) VALUES(?, ?, ?, ?, ?, ?)",

                       session["user_id"], lookup_result["symbol"], lookup_result["name"], lookup_result["price"], date_now, int(number_of_shares))

            # Update user cash
            new_cash = cash_user - lookup_result["price"] * int(number_of_shares)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, session["user_id"])
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    row1 = db.execute("SELECT symbol, number_shares, price_symbol, date_buy FROM buy_info WHERE id_user=?", session["user_id"])
    return render_template("history.html", row1=row1, leng_row=len(row1))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    request_via_get = True
    # if request via get
    if request.method == "GET":
        return render_template("quote.html", request_via_get=request_via_get)

    # if request via post
    else:
        request_via_get = False
        lookup_result = lookup(request.form.get("symbol"))
        if lookup_result:
            return render_template("quote.html", request_via_get=request_via_get, lookup_result=lookup_result)

        else:
            return apology("invalid symbol")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # if request is via post
    if request.method == "POST":

        # user input
        user_name = request.form.get("username")
        pass_word = request.form.get("password")
        confirmation_pass = request.form.get("confirmation")

        if not user_name or not pass_word or not confirmation_pass:
            return apology("must have username and password")

        # check for duplicate usernames or dissimilarities passwords
        user_match = db.execute("SELECT * FROM users WHERE username = ?", user_name)

        if len(user_match) != 0:
            return apology("username exist")

        if pass_word != confirmation_pass:
            return apology("password not confirmed")

        # encrypt password
        hash_password = generate_password_hash(pass_word)

        # insert user to database
        db.execute("INSERT INTO  users (username, hash) VALUES(?, ?)", user_name, hash_password)

        # log the user in
        row = db.execute("SELECT * FROM users WHERE username = ?", user_name)
        session["user_id"] = row[0]["id"]
        return redirect("/")

    # if request is via get
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # number of shares displayed and can be sold
    symbols = db.execute("SELECT DISTINCT(symbol) FROM users, buy_info WHERE id = ?", session["user_id"])

    number = {}

    for symbol in symbols:
        sum_shares = db.execute(
            "SELECT SUM(number_shares) as na FROM users, buy_info WHERE id = ? AND symbol=?", session["user_id"], symbol["symbol"])
        if symbol["symbol"] not in number:
            number[symbol["symbol"]] = sum_shares[0]["na"]
        else:
            number[symbol["symbol"]] += sum_shares[0]["na"]
    # REQUEST via get
    if request.method == "GET":
        row1 = db.execute("SELECT DISTINCT(symbol) from buy_info WHERE id_user = ?", session["user_id"])
        return render_template("sell.html", row1=row1, leng_row=len(row1), number_of_shares=number)

    # request via post
    else:
        name_symbol = request.form.get("symbol")
        number_of_shares = request.form.get("shares")
        lookup_result = lookup(name_symbol)

        # if no input or invalid input
        if not name_symbol or not number_of_shares or not lookup_result:
            return apology("enter valid symbol and shares")
        else:
            # check if the number of shares sold greater than number of shares owned
            shares_owned = number[name_symbol]
            if int(shares_owned) < int(number_of_shares):
                return apology("too many shares")

            rows = db.execute("select cash from users where id = ?", session["user_id"])[0]
            cash_user = float(rows["cash"])
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO buy_info (id_user, symbol, company_name, price_symbol, date_buy, number_shares) VALUES(?, ?, ?, ?, ?, ?)",
                       session["user_id"], lookup_result["symbol"], lookup_result["name"], lookup_result["price"], date_now, (-1) * int(number_of_shares))

            # Update user cash
            new_cash = cash_user + lookup_result["price"] * int(number_of_shares)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_cash, session["user_id"])
            # if the user buy all of his stocks of a symbol
            """if int(shares_owned) == int(number_of_shares):
                db.execute("DELETE FROM buy_info WHERE symbol = ?", name_symbol)"""
            return redirect("/")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    # if the request via get
    if request.method == "GET":
        return render_template("changepass.html")

    # if the request via post
    else:
        # collect user input
        currentpass = request.form.get("currentpass")
        newpass = request.form.get("password")
        confiramation_pass = request.form.get("confirmation")

        # if no input
        if not currentpass or not newpass or not confiramation_pass:
            return apology("must enter all field")

        # compare current password from user with actual pass
        actual_pass_hash = db.execute("SELECT hash FROM users where id = ?", session["user_id"])[0]["hash"]

        if not check_password_hash(actual_pass_hash, currentpass):
            return apology("password incorrect")

        # of the user does not confirm his password
        if newpass != confiramation_pass:
            return apology("confirm your password")

        newpass_hash = generate_password_hash(newpass)

        # update password in database
        db.execute("UPDATE users SET hash = ? WHERE id = ? AND hash = ?", newpass_hash, session["user_id"], actual_pass_hash)

        # redirect user for main route
        return redirect("/")
