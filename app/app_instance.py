from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import Config
from flask_security import SQLAlchemyUserDatastore, Security
from app.models import User, Role
from app.db import db

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from app import models

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)
    # 注册蓝图
    from app.routes import routes_bp
    app.register_blueprint(routes_bp)

    return app

app = create_app()
