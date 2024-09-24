from flask import request, jsonify, render_template
from app import app, db
from app.models import User, Story
from app.story_service import generate_story
from app.hello import hello

@app.before_request
def create_default_user():
    if not User.query.filter_by(username='default_user').first():
        default_user = User(username='default_user', email='default@example.com')
        db.session.add(default_user)
        db.session.commit()
def index():
    return render_template('index.html')

@app.route('/api/stories', methods=['POST'])
def create_story():
    data = request.get_json()
    user = User.query.filter_by(username='default_user').first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    story = generate_story(data['preferences'])
    new_story = Story(title=story['title'], body=story['body'], author=user)
    db.session.add(new_story)
    db.session.commit()
    return jsonify({'story': new_story.id}), 201
