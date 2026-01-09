from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_jwt_extended import JWTManager
from .auth import bcrypt

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["JWT_SECRET_KEY"] = "8974474e04dd65e2dead4114a7638d7ec4ee280a2d5a60319e28d074d1ced604"

    db.init_app(app)

    bcrypt.init_app(app)

    JWTManager(app)

    # Import blueprint (blueprint of application)
    from .routes import api
    app.register_blueprint(api)

    return app
