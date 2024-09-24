from flask import request, jsonify
from app import app, db
from app.models import User, Story
from app.story_service import generate_story

@app.route('/api/stories', methods=['POST'])
def create_story():
    data = request.get_json()
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    story = generate_story(data['preferences'])
    new_story = Story(title=story['title'], body=story['body'], author=user)
    db.session.add(new_story)
    db.session.commit()
    return jsonify({'story': new_story.id}), 201
