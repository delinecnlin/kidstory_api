from flask import request, jsonify, render_template
import logging

logging.basicConfig(level=logging.DEBUG)
from app import app, db
from app.models import User, Story, Chapter
from app.story_service import generate_story
from app.models import Story
from app.hello import hello

@app.route('/')
def index():
    return render_template('index.html')

@app.before_request
def create_default_user():
    if not User.query.filter_by(username='default_user').first():
        default_user = User(username='default_user', email='default@example.com')
        db.session.add(default_user)
        db.session.commit()

@app.route('/api/fix_stories', methods=['POST'])
def fix_stories():
    # 获取前4个故事
    stories = Story.query.limit(4).all()
    for story in stories:
        # 将故事分配给其他用户并设置为开放状态
        story.user_id = 2  # 假设用户ID 2是其他用户
        story.is_open = True
    db.session.commit()
    return render_template('fix_stories.html')
def get_recommendations():
    recommendations = User.query.filter(User.username != 'default_user').limit(4).all()
    recommendations_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in recommendations]
    return jsonify(recommendations), 200

@app.route('/api/stories/<int:story_id>/chapters', methods=['POST'])
def add_chapter(story_id):
    logging.debug(f"Request path: {request.path}")
    data = request.get_json()
    story = Story.query.get_or_404(story_id)
    
    preferences = data.get('preferences', {})
    new_content = generate_story(preferences)

    if 'body' in new_content:
        new_chapter = Chapter(title="New Chapter", body=new_content['body'], story=story)
    else:
        return jsonify({'error': 'Chapter generation failed'}), 500
    db.session.add(new_chapter)
    db.session.commit()

    return jsonify({'story': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body}]}), 201

@app.route('/api/stories', methods=['GET'])
def get_stories():
    stories = Story.query.all()
    return jsonify([{'id': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': chapter.id, 'title': chapter.title, 'body': chapter.body} for chapter in story.chapters]} for story in stories]), 200

@app.route('/api/stories/<int:id>', methods=['GET'])
def get_story(id):
    story = Story.query.get_or_404(id)
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@app.route('/api/stories/<int:id>', methods=['DELETE'])
def delete_story(id):
    story = Story.query.get_or_404(id)
    db.session.delete(story)
    db.session.commit()
    return '', 204

@app.route('/api/stories/<int:id>/continue', methods=['POST'])
def continue_story(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = continue_story(id, data['preferences'])
    story.body += new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@app.route('/api/stories/<int:id>/rewrite', methods=['POST'])
def rewrite_story(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = rewrite_story(id, data['preferences'])
    story.body = new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200


@app.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200

@app.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    db.session.delete(chapter)
    db.session.commit()
    return '', 204

@app.route('/api/stories/<int:id>/chapters/<int:chapter_id>/rewrite', methods=['POST'])
def rewrite_chapter(id, chapter_id):
    data = request.get_json()
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    new_content = rewrite_chapter(id, chapter_id, data['preferences'])
    chapter.body = new_content['body']
    db.session.commit()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200
