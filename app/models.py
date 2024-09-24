from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    preferences = db.Column(db.JSON, nullable=True)
    stories = db.relationship('Story', backref='author', lazy='dynamic')

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    body = db.Column(db.Text)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'))

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    body = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    chapters = db.relationship('Chapter', backref='story', lazy='dynamic')
