from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from flask_security import hash_password, login_required, verify_password

import logging

import requests
from app.models import User, Story, Chapter
from app.speech import transcribe_audio
import os
import tempfile
from app.story_service import generate_chapter_content, generate_story_title
import requests

logging.basicConfig(level=logging.DEBUG)

routes_bp = Blueprint('routes', __name__)
from app.db import db
from app import oauth
from app.story_service import rewrite_story_service
from app.image_service import generate_image
import openai
import requests

# Google OAuth 回调处理
@routes_bp.route('/auth/google')
def auth_google():
    redirect_uri = url_for('routes.auth_callback', _external=True)
    import secrets
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@routes_bp.route('/auth/callback')
def auth_callback():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = oauth.google.parse_id_token(token, nonce=nonce)
    
    # 根据从 Google 返回的用户信息处理登录或注册
    if not user_info:
        return jsonify({"error": "Failed to authenticate with Google"}), 400
    
    user_datastore = current_app.extensions['security'].datastore
    user = user_datastore.find_user(email=user_info['email'])
    current_app.logger.debug(f"User found: {user}")

    # 如果用户不存在，注册新用户
    if not user:
        user = user_datastore.create_user(
            email=user_info['email'],
            username=user_info.get('name', user_info['email']),
            password=hash_password('default_password')  # 设置默认密码
        )
        db.session.commit()

    # 登录用户
    current_app.logger.debug(f"User ID: {user.id}")
    session['user'] = {'id': user.id, 'email': user.email, 'username': user.username, 'type': 'google'}
    current_app.logger.debug(f"User session set: {session['user']}")

    return redirect(url_for('routes.index'))

# Register route added here
@routes_bp.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        action = request.form['action']
        email = request.form['email']
        password = request.form['password']
        user_datastore = current_app.extensions['security'].datastore

        if action == 'register':
            import random
            import string
            username = request.form.get('username', ''.join(random.choices(string.ascii_letters + string.digits, k=8)))

            if user_datastore.find_user(email=email):
                return render_template('auth.html', error='Email already registered')
            if user_datastore.find_user(username=username):
                return render_template('auth.html', error='Username already taken')

            try:
                user_datastore.create_user(username=username, email=email, password=hash_password(password))
                db.session.commit()
                return redirect(url_for('routes.index'))
            except Exception as e:
                db.session.rollback()
                return render_template('auth.html', error=str(e))

        elif action == 'login':
            user = user_datastore.find_user(email=email)
            if user:
                current_app.logger.debug(f"User found: {user}")
                current_app.logger.debug(f"Input password: {password}")
                current_app.logger.debug(f"Stored password hash: {user.password}")
                password_match = verify_password(password, user.password)
                current_app.logger.debug(f"Password match result: {password_match}")
                if password_match:
                    session['user'] = {'id': user.id, 'email': user.email, 'username': user.username, 'type': 'local'}
                    current_app.logger.debug(f"User ID: {user.id}")
                    current_app.logger.debug(f"User session set: {session['user']}")
                    return redirect(url_for('routes.index'))
                else:
                    current_app.logger.error(f"Password mismatch for user {email}")
                    return render_template('auth.html', error='Invalid password')
            else:
                current_app.logger.error(f"User not found: {email}")
                return render_template('auth.html', error='User not found')

    users = User.query.all()
    return render_template('auth.html', users=users)

@routes_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user_datastore = current_app.extensions['security'].datastore
        user = user_datastore.find_user(email=session['user']['email'])

        current_app.logger.debug(f"Input current password: {current_password}")
        current_app.logger.debug(f"Stored password hash: {user.password}")
        if not user or not verify_password(current_password, user.password):
            return render_template('auth.html', error='Current password is incorrect')

        if new_password != confirm_password:
            return render_template('auth.html', error='New passwords do not match')

        try:
            user.password = hash_password(new_password)
            db.session.commit()
            return redirect(url_for('routes.index'))
        except Exception as e:
            db.session.rollback()
            return render_template('auth.html', error=str(e))

    return render_template('auth.html')

@routes_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('routes.index'))

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
@routes_bp.route('/stories', methods=['GET'])
def view_stories():
    user_email = session.get('user', {}).get('email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    stories = Story.query.filter_by(user_id=user.id).all()
    user_stories = stories  # 确保 user_stories 被定义
    return render_template('recommendations.html', stories=stories, user_stories=user_stories)

@routes_bp.route('/')
def index():
    user_email = session.get('user', {}).get('email')
    if not user_email:
        return redirect(url_for('routes.auth'))

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return redirect(url_for('routes.auth'))

    recent_chapters = Chapter.query.order_by(Chapter.id.desc()).limit(5).all()
    chapters_with_story_info = [
        {
            "chapter": chapter,
            "story": Story.query.get(chapter.story_id),
            "chapter_number": idx + 1
        }
        for idx, chapter in enumerate(recent_chapters)
    ]

    user_stories = Story.query.filter_by(user_id=user.id).all()
    return render_template('index.html', chapters_with_story_info=chapters_with_story_info, user_stories=user_stories)

@routes_bp.route('/api/stories/<int:story_id>/chapters', methods=['POST'])
def add_chapter(story_id):
    data = request.get_json()
    preferences = data.get('preferences', {})

    story = Story.query.get_or_404(story_id)
    context = " ".join([chapter.body for chapter in story.chapters])
    preferences['context'] = context
    new_content = generate_chapter_content(preferences)
    if 'body' in new_content:
        new_chapter = Chapter(title="New Chapter", body=new_content['body'], story=story)
        db.session.add(new_chapter)
        db.session.commit()
        return jsonify({'story': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body} for chapter in story.chapters]}), 201
    else:
        return jsonify({'error': 'Failed to generate story. Please try again later.'}), 500

@routes_bp.route('/api/stories/new', methods=['POST'])
def create_story():
    data = request.get_json()
    preferences = data.get('preferences', {})

    current_app.logger.debug(f"Session data: {session}")
    if 'user' not in session or 'id' not in session['user']:
        return jsonify({'error': 'User not logged in or user ID not found in session'}), 401

    new_content = generate_chapter_content(preferences)
    if 'body' in new_content:
        title_content = generate_story_title(preferences)
        if 'title' in title_content:
            new_story = Story(title=title_content['title'], body="", excerpt=title_content['excerpt'], user_id=session['user']['id'])
            new_story.image_url = title_content['image_url']
            db.session.add(new_story)
            db.session.commit()
            new_chapter = Chapter(title="New Chapter", body=new_content['body'], story=new_story)
            db.session.add(new_chapter)
            db.session.commit()
            return jsonify({'story': new_story.id, 'title': new_story.title, 'body': new_story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body}]}), 201
        else:
            return jsonify({'error': 'Failed to generate story title. Please try again later.'}), 500
    else:
        return jsonify({'error': 'Failed to generate story. Please try again later.'}), 500



@routes_bp.route('/stories/<int:id>', methods=['GET'])
def get_story(id):
    story = Story.query.get_or_404(id)
    return render_template('story.html', story=story)

@routes_bp.route('/api/stories/<int:id>', methods=['DELETE'])
def delete_story(id):
    story = Story.query.get_or_404(id)
    # 删除相关章节
    for chapter in story.chapters:
        db.session.delete(chapter)
    db.session.delete(story)
    db.session.commit()
    return '', 204


@routes_bp.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        files = {'file': (file.filename, file.stream, file.mimetype)}
        response = requests.post('http://flaz2.southeastasia.azurecontainer.io:3000/api/v1/uploadimage', files=files)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to upload image"}), response.status_code
    return redirect(url_for('routes.index'))


@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200

@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    db.session.delete(chapter)
    db.session.commit()
    return jsonify({'message': 'Chapter deleted successfully'}), 200

@routes_bp.route('/api/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    audio_data = audio_file.read()
    transcription = transcribe_audio(audio_data)

    return jsonify({'transcription': transcription})

@routes_bp.route('/api/user_stories', methods=['GET'])
def get_user_stories():
    user_email = session.get('user', {}).get('email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401

    user = User.query.filter_by(email=user_email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    stories = Story.query.filter_by(user_id=user.id).all()
    user_stories = []
    for story in stories:
        user_stories.append({
            'id': story.id,
            'title': story.title,
            'body': story.body,
            'image_url': story.image_url,
            'chapters': [{'id': chapter.id, 'title': chapter.title, 'body': chapter.body} for chapter in story.chapters]
        })

    return jsonify(user_stories), 200
