from app import db


class Users(db.Model):
    id = db.Column(db.String(80),
                   unique=True,
                   nullable=False,
                   primary_key=True)
    hash = db.Column(db.String())
    cash = db.Column(db.Float, default=10000.)

    def __repr__(self):
        return f"{self.id} - {self.hash} - {self.cash}"


class Transactions(db.Model):
    timestamp = db.Column(db.DateTime, unique=True, primary_key=True)
    type = db.Column(db.String(80))
    symbol = db.Column(db.String)
    shares = db.Column(db.Integer)
    price = db.Column(db.Float, default=10000)
    id = db.Column(db.String(80),
                   nullable=False)


class StockHoldings(db.Model):
    timestamp = db.Column(db.DateTime, unique=True, primary_key=True)
    id = db.Column(db.String(80))
    shares = db.Column(db.Integer)
    symbol = db.Column(db.String)
    name = db.Column(db.String)
    purchase_total = db.Column(db.Integer)


