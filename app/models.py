from flask_sqlalchemy import SQLAlchemy
from .auth import hash_pin
from . import db

class Account(db.Model):

    __tablename__ = "accounts"   # must match your real MySQL table name

    id = db.Column(
        db.Integer, 
        primary_key=True
    )

    first_name = db.Column(
        db.String(50), 
        nullable=True
    )

    last_name = db.Column(
        db.String(50), 
        nullable=True
    )

    balance = db.Column(
        db.Numeric(11, 2), 
        nullable=False, 
        default=0.00
    )

    pin_hash = db.Column(
        db.String(255), 
        nullable=True
    )

    deleted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    username = db.Column(
        db.String(25), 
        nullable=False, 
        unique=True
    )

    role = db.Column(
        db.String(25), 
        nullable=False, 
        default="user"
    )

#here was a roblem got removed
    
    def set_pin(self, pin):
        self.pin_hash = hash_pin(pin)

    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    
class BusinessAccount(db.Model):
    __tablename__ = "business_accounts"

    id = db.Column(
        db.Integer, 
        primary_key=True
    )

    business_name = db.Column(
        db.String(50), 
        nullable=False, 
        unique=True
    )

    balance = db.Column(
        db.Numeric(11, 2), 
        nullable=False, 
        default=0.00
    )

    pin_hash = db.Column(
        db.String(255), 
        nullable=False
    )
    
    deleted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False
    )

    owner = db.relationship("Account", backref="owned_businesses")

    def set_pin(self, pin: str):
        self.pin_hash = hash_pin(str(pin))


class BusinessMember(db.Model):
    __tablename__ = "business_members"

    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business_accounts.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("accounts.id"),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="worker"
    )

    business = db.relationship("BusinessAccount", backref="members")
    user = db.relationship("Account", backref="business_memberships")
