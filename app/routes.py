from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from flask_security import hash_password

import logging
from app.models import User, Story, Chapter
from app.story_service import generate_story

logging.basicConfig(level=logging.DEBUG)

routes_bp = Blueprint('routes', __name__)
from app.db import db
from app.story_service import continue_story_service, rewrite_story_service

# Register route added here
@routes_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        import random
        import string

        email = request.form['email']
        password = request.form['password']
        username = request.form.get('username', ''.join(random.choices(string.ascii_letters + string.digits, k=8)))

        # 使用 current_app 获取 user_datastore
        user_datastore = current_app.extensions['security'].datastore

        # 检查邮箱和用户名是否已经存在
        if user_datastore.find_user(email=email):
            return render_template('register.html', error='Email already registered')
        if user_datastore.find_user(username=username):
            return render_template('register.html', error='Username already taken')

        try:
            user_datastore.create_user(username=username, email=email, password=hash_password(password))
            db.session.commit()  # 保存到数据库
            return redirect(url_for('routes.index'))  # 注册成功后跳转到index.html
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error=str(e))
    return render_template('register.html')

@routes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_datastore = current_app.extensions['security'].datastore
        user = user_datastore.find_user(email=email)
        if user and user.password == password:
            session['user'] = {'email': user.email}
            return redirect(url_for('routes.index'))
        else:
            return 'Invalid credentials', 401
    return render_template('login.html')

@routes_bp.route('/fix_stories', methods=['POST'])
def fix_stories():
    # 获取前4个故事
    stories = Story.query.limit(4).all()
    for story in stories:
        # 将故事分配给其他用户并设置为开放状态
        story.user_id = 2  # 假设用户ID 2是其他用户
        story.is_open = True
    db.session.commit()
    return render_template('fix_stories.html')
@routes_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    open_stories = Story.query.filter_by(is_open=True).limit(4).all()
    return render_template('recommendations.html', stories=open_stories)

@routes_bp.route('/')
def index():
    return render_template('index.html')

@routes_bp.route('/api/stories/<int:story_id>/chapters', methods=['POST'])
def add_chapter(story_id):
    logging.debug(f"Request path: {request.path}")
    data = request.get_json()
    story = Story.query.get_or_404(story_id)
    
    preferences = data.get('preferences', {})
    # 获取前面章节的历史作为context
    context = " ".join([chapter.body for chapter in story.chapters])
    preferences['context'] = context
    new_content = generate_story(preferences)

    if 'body' in new_content:
        new_chapter = Chapter(title="New Chapter", body=new_content['body'], story=story)
    else:
        return jsonify({'error': 'Chapter generation failed'}), 500
    db.session.add(new_chapter)
    db.session.commit()

    return jsonify({'story': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body} for chapter in story.chapters]}), 201

@routes_bp.route('/api/stories', methods=['GET'])
def get_stories():
    stories = Story.query.all()
    return jsonify([{'id': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': chapter.id, 'title': chapter.title, 'body': chapter.body} for chapter in story.chapters]} for story in stories]), 200

@routes_bp.route('/api/stories/<int:id>', methods=['GET'])
def get_story(id):
    story = Story.query.get_or_404(id)
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@routes_bp.route('/api/stories/<int:id>', methods=['DELETE'])
def delete_story(id):
    story = Story.query.get_or_404(id)
    db.session.delete(story)
    db.session.commit()
    return '', 204

@routes_bp.route('/api/stories/<int:id>/continue', methods=['POST'])
def continue_story_route(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = continue_story_service(id, data['preferences'])
    story.body += new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@routes_bp.route('/api/stories/<int:id>/rewrite', methods=['POST'])
def rewrite_story_route(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = rewrite_story_service(id, data['preferences'])
    story.body = new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200


@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200

@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    db.session.delete(chapter)
    db.session.commit()
    return '', 204

@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>/rewrite', methods=['POST'])
def rewrite_chapter(id, chapter_id):
    data = request.get_json()
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    new_content = rewrite_chapter(id, chapter_id, data['preferences'])
    chapter.body = new_content['body']
    db.session.commit()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200
