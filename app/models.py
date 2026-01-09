from flask_sqlalchemy import SQLAlchemy
from .auth import hash_pin
from . import db

class Account(db.Model):

    __tablename__ = "accounts"   # must match your real MySQL table name

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    balance = db.Column(db.Numeric(11, 2), nullable=False, default=0.00)
    pin_hash = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(255), nullable=False)
    
    def set_pin(self, pin):
        self.pin_hash = hash_pin(pin)

    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
        #hallo