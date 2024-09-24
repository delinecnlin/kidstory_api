from flask import request, jsonify, render_template
import logging

logging.basicConfig(level=logging.DEBUG)
from app import app, db
from app.models import User, Story, Chapter
from app.story_service import generate_story, fetch_recommendations
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

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    recommendations = fetch_recommendations()
    return jsonify(recommendations), 200

@app.route('/api/stories', methods=['POST'])
def create_story():
    logging.debug(f"Request path: {request.path}")
    data = request.get_json()
    user = User.query.filter_by(username='default_user').first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    story = generate_story(data['preferences'])
    new_story = Story(title="Generated Story", body="", author=user)
    db.session.add(new_story)
    db.session.commit()

    new_chapter = Chapter(title="Chapter 1", body=story['body'], story=new_story)
    db.session.add(new_chapter)
    db.session.commit()

    return jsonify({'story': new_story.id, 'title': new_story.title, 'body': new_story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body}]}), 201

@app.route('/api/stories', methods=['GET'])
def get_stories():
    stories = Story.query.all()
    return jsonify([{'id': story.id, 'title': story.title, 'body': story.body} for story in stories]), 200

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

@app.route('/api/stories/<int:id>/chapters', methods=['POST'])
def add_chapter(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_chapter = Chapter(title=data['title'], body=data['body'], story=story)
    db.session.add(new_chapter)
    db.session.commit()
    return jsonify({'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body}), 201

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
