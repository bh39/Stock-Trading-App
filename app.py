import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd, change

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.before_first_request
def create_tables():
    db.create_all()


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQLAlchemy()
db.init_app(app)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

from model import Users, Transactions, StockHoldings


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session['user_id']
    user = Users.query.filter_by(id=user_id).first()
    my_stocks = StockHoldings.query.filter_by(id=user_id).all()
    total = 0
    for stock in my_stocks:
        stock.current_price = usd(float(lookup(stock.symbol)['price']))
        worth = float(lookup(stock.symbol)['price']) * stock.shares
        stock.worth = usd(worth)
        stock.average_price_per_share = usd(stock.purchase_total / stock.shares)
        stock.change = change(worth, stock.purchase_total)
        stock.purchase_total = usd(stock.purchase_total)
        total += worth

    total += user.cash
    total = usd(total)
    return render_template('index.html', stocks=my_stocks, cash=usd(user.cash), total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get('quote')
        shares = int(request.form.get('shares'))
        user_id = session['user_id']
        if not symbol:
            return apology('invalid quote', 403)
        if not shares:
            return apology('invalid number of shares', 403)

        user = Users.query.filter_by(id=user_id).first()
        if not user:
            return apology('User not found', 403)

        stock_info = lookup(request.form.get('quote'))
        price = float(stock_info['price'])

        if user.cash < float(price) * int(shares):
            return apology('Not enough cash for this transaction')
        else:
            new_transaction = Transactions(timestamp=datetime.now(), id=user_id, type='BUY', symbol=symbol,
                                           shares=shares, price=price)
            db.session.add(new_transaction)
            user.cash -= price * shares
            stock_holding = StockHoldings.query.filter_by(id=user_id, symbol=symbol).first()
            if not stock_holding:
                new_stock_holding = StockHoldings(timestamp=datetime.now(), id=user_id, shares=shares, symbol=symbol, name = stock_info['name'], purchase_total = price * shares)
                db.session.add(new_stock_holding)
            else:
                stock_holding.shares += shares
                stock_holding.purchase_total += price * shares
            db.session.commit()
            return render_template('buy_success.html', name=stock_info['name'], symbol=symbol, price=usd(price),
                                   cash=usd(user.cash))

    return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session['user_id']
    histories = Transactions.query.filter_by(id=user_id).order_by(desc(Transactions.timestamp)).all()
    for history in histories:
        history.timestamp = history.timestamp.strftime("%m/%d/%Y %H:%M:%S")
        history.price = usd(history.price)
    return render_template('history.html', user=user_id, histories=histories)


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
        user = Users.query.filter_by(id=request.form.get('username')).first()

        if not user:
            return apology('username is invalid', 403)
        else:
            if not check_password_hash(user.hash, request.form.get("password")):
                return apology('password is invalid', 403)
            # Remember which user has logged in
            session["user_id"] = user.id

        # Ensure username exists and password is correct
        # if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
        #     return apology("invalid username and/or password", 403)

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
    if request.method == "POST":
        print(request.form.get('quote'))
        result = lookup(request.form.get('quote'))
        if not result:
            return apology('invalid symbol', 403)
        return render_template("quote_display.html", price=usd(result['price']), name=result['name'],
                               symbol=result['symbol'])
    return render_template("quote.html")


@app.route("/chart", methods=["GET", "POST"])
def chart():
    return apology("TODO", 404)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 403)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 403)
        user = Users(id=request.form.get('username'), hash=generate_password_hash(request.form.get('password')))
        print(user)
        # try:
        db.session.add(user)
        db.session.commit()
        # except:
        #     return apology("user already exists", 403)
        print('ok')
        return render_template("login.html")

    else:
        return render_template('register.html')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session['user_id']
    if request.method == "POST":
        symbol = request.form.get('symbols')
        shares = int(request.form.get('shares'))
        if not symbol:
            return apology("invalid symbol", 403)
        elif not shares:
            return apology("invalid shares", 403)

        current_holding = StockHoldings.query.filter_by(id=user_id, symbol=symbol).first()
        if not current_holding:
            return apology("you do not own shares of this stock", 403)
        if current_holding.shares < shares:
            return apology("selling more shares than you own", 403)
        else:
            current_holding.shares -= shares
            if current_holding.shares == 0:
                db.session.delete(current_holding)
            stock_info = lookup(symbol)
            price = float(stock_info['price'])
            user = Users.query.filter_by(id=user_id).first()
            user.cash += price * shares
            new_transaction = Transactions(timestamp=datetime.now(), id=user_id, type='SELL', symbol=symbol,
                                           shares=shares, price=price)
            db.session.add(new_transaction)
            db.session.commit()
            return render_template('sell_success.html', name = stock_info['name'], symbol = symbol, price = price, cash = usd(user.cash))

    my_stocks = []
    my_stock_holding = StockHoldings.query.filter_by(id = user_id).all()
    for stock in my_stock_holding:
        my_stocks.append(stock.symbol)
    print(my_stocks)
    return render_template('sell.html', stocks=my_stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
