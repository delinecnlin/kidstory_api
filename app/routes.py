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

@app.route('/api/stories', methods=['POST'])
def create_story():
    data = request.get_json()
    user = User.query.filter_by(username='default_user').first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    story = generate_story(data['preferences'])
    new_story = Story(title=story.get('title', 'Untitled'), body=story.get('body', ''), author=user)
    db.session.add(new_story)
    db.session.commit()
    return jsonify({'story': new_story.id, 'title': new_story.title, 'body': new_story.body}), 201

@app.route('/api/recommendations', methods=['GET'])
def recommend_stories():
    user = User.query.filter_by(username='default_user').first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # 假设我们有一个简单的推荐算法
    recommended_stories = Story.query.filter_by(user_id=user.id).limit(5).all()
    recommendations = [{'id': story.id, 'title': story.title, 'body': story.body} for story in recommended_stories]
    return jsonify(recommendations), 200
