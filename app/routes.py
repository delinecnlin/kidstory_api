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

@app.route('/api/stories/<int:id>/chapters', methods=['POST'])
def add_chapter(id):
    logging.debug(f"Request path: {request.path}")
    data = request.get_json()
    story = Story.query.get_or_404(id)
    
    # 手动设置 preferences 的值进行测试
    preferences = {
        "characters": "小红帽，大灰狼",
        "by_characters": "",
        "history": "第一章小红帽出生了，大灰狼在做菜，第二章小红帽去世了"
    }
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
