from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import sqlite3
from datetime import datetime
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog_publisher.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    
    @staticmethod
    def get(key, default=None):
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value):
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

class AvailableTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    description = db.Column(db.String(200))
    
    @staticmethod
    def get_all_tags():
        return AvailableTag.query.order_by(AvailableTag.usage_count.desc()).all()
    
    @staticmethod
    def add_tag(name, description=''):
        tag = AvailableTag.query.filter_by(name=name.strip()).first()
        if not tag:
            tag = AvailableTag(name=name.strip(), description=description)
            db.session.add(tag)
            db.session.commit()
        return tag
    
    @staticmethod
    def increment_usage(tag_names):
        if not tag_names:
            return
        tag_list = [tag.strip() for tag in tag_names.split(',') if tag.strip()]
        for tag_name in tag_list:
            tag = AvailableTag.query.filter_by(name=tag_name).first()
            if tag:
                tag.usage_count += 1
            else:
                # Auto-add new tags
                AvailableTag.add_tag(tag_name)
        db.session.commit()

class AvailableCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    description = db.Column(db.String(200))
    
    @staticmethod
    def get_all_categories():
        return AvailableCategory.query.order_by(AvailableCategory.usage_count.desc()).all()
    
    @staticmethod
    def add_category(name, description=''):
        category = AvailableCategory.query.filter_by(name=name.strip()).first()
        if not category:
            category = AvailableCategory(name=name.strip(), description=description)
            db.session.add(category)
            db.session.commit()
        return category
    
    @staticmethod
    def increment_usage(category_names):
        if not category_names:
            return
        category_list = [cat.strip() for cat in category_names.split(',') if cat.strip()]
        for category_name in category_list:
            category = AvailableCategory.query.filter_by(name=category_name).first()
            if category:
                category.usage_count += 1
            else:
                # Auto-add new categories
                AvailableCategory.add_category(category_name)
        db.session.commit()

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, published, scheduled
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    published_date = db.Column(db.DateTime)
    blog_target = db.Column(db.String(50))  # blogger, wordpress
    external_id = db.Column(db.String(100))  # ID from the blog platform
    tags = db.Column(db.String(500))
    categories = db.Column(db.String(500))

class BlogAPI:
    @staticmethod
    def publish_to_blogger(post, credentials):
        try:
            service = build('blogger', 'v3', credentials=credentials)
            blog_id = Setting.get('blogger_blog_id')
            
            blog_post = {
                'title': post.title,
                'content': post.content,
            }
            
            if post.tags:
                blog_post['labels'] = [tag.strip() for tag in post.tags.split(',')]
            
            result = service.posts().insert(blogId=blog_id, body=blog_post).execute()
            return result['id']
        except HttpError as e:
            raise Exception(f"Blogger API error: {e}")
    
    @staticmethod
    def publish_to_wordpress(post):
        wp_url = Setting.get('wordpress_url')
        wp_user = Setting.get('wordpress_username')
        wp_password = Setting.get('wordpress_password')
        
        if not all([wp_url, wp_user, wp_password]):
            raise Exception("WordPress credentials not configured")
        
        api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            'title': post.title,
            'content': post.content,
            'status': 'publish'
        }
        
        if post.categories:
            # This is simplified - in reality, you'd need to map category names to IDs
            data['categories'] = [cat.strip() for cat in post.categories.split(',')]
        
        if post.tags:
            data['tags'] = [tag.strip() for tag in post.tags.split(',')]
        
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            auth=(wp_user, wp_password)
        )
        
        if response.status_code == 201:
            return response.json()['id']
        else:
            raise Exception(f"WordPress API error: {response.text}")

# Routes
@app.route('/')
def index():
    # Check if app is configured
    if not Setting.get('configured'):
        return redirect(url_for('setup'))
    
    posts = Post.query.order_by(Post.created_date.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/setup')
def setup():
    return render_template('setup.html')

@app.route('/setup', methods=['POST'])
def setup_post():
    # Save blog configuration
    blog_type = request.form.get('blog_type')
    Setting.set('blog_type', blog_type)
    
    if blog_type == 'blogger':
        Setting.set('blogger_blog_id', request.form.get('blogger_blog_id'))
        Setting.set('blogger_client_id', request.form.get('blogger_client_id'))
        Setting.set('blogger_client_secret', request.form.get('blogger_client_secret'))
    elif blog_type == 'wordpress':
        Setting.set('wordpress_url', request.form.get('wordpress_url'))
        Setting.set('wordpress_username', request.form.get('wordpress_username'))
        Setting.set('wordpress_password', request.form.get('wordpress_password'))
    
    Setting.set('configured', 'true')
    flash('Configuration saved successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/settings')
def settings():
    current_settings = {
        'blog_type': Setting.get('blog_type'),
        'blogger_blog_id': Setting.get('blogger_blog_id'),
        'blogger_client_id': Setting.get('blogger_client_id'),
        'wordpress_url': Setting.get('wordpress_url'),
        'wordpress_username': Setting.get('wordpress_username'),
    }
    return render_template('settings.html', settings=current_settings)

@app.route('/settings', methods=['POST'])
def settings_post():
    blog_type = request.form.get('blog_type')
    Setting.set('blog_type', blog_type)
    
    if blog_type == 'blogger':
        Setting.set('blogger_blog_id', request.form.get('blogger_blog_id'))
        Setting.set('blogger_client_id', request.form.get('blogger_client_id'))
        Setting.set('blogger_client_secret', request.form.get('blogger_client_secret'))
    elif blog_type == 'wordpress':
        Setting.set('wordpress_url', request.form.get('wordpress_url'))
        Setting.set('wordpress_username', request.form.get('wordpress_username'))
        Setting.set('wordpress_password', request.form.get('wordpress_password'))
    
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/new_post')
def new_post():
    return render_template('editor.html', post=None)

@app.route('/edit_post/<int:post_id>')
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('editor.html', post=post)

@app.route('/save_post', methods=['POST'])
def save_post():
    data = request.get_json()
    
    if data.get('id'):
        post = Post.query.get(data['id'])
        post.title = data['title']
        post.content = data['content']
        post.tags = data.get('tags', '')
        post.categories = data.get('categories', '')
    else:
        post = Post(
            title=data['title'],
            content=data['content'],
            tags=data.get('tags', ''),
            categories=data.get('categories', ''),
            blog_target=Setting.get('blog_type')
        )
        db.session.add(post)
    
    # Update tag and category usage counts
    AvailableTag.increment_usage(post.tags)
    AvailableCategory.increment_usage(post.categories)
    
    db.session.commit()
    return jsonify({'success': True, 'id': post.id})

@app.route('/publish_post', methods=['POST'])
def publish_post():
    data = request.get_json()
    post_id = data.get('id')
    
    if not post_id:
        return jsonify({'success': False, 'error': 'Post ID required'})
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'success': False, 'error': 'Post not found'})
    
    try:
        blog_type = Setting.get('blog_type')
        
        if blog_type == 'blogger':
            # This would require OAuth2 flow implementation
            external_id = 'blogger_post_id'  # Placeholder
        elif blog_type == 'wordpress':
            external_id = BlogAPI.publish_to_wordpress(post)
        else:
            return jsonify({'success': False, 'error': 'No blog platform configured'})
        
        post.status = 'published'
        post.published_date = datetime.utcnow()
        post.external_id = str(external_id)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Post published successfully!'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('index'))

# Tag Management Routes
@app.route('/api/tags')
def get_tags():
    tags = AvailableTag.get_all_tags()
    return jsonify([{'name': tag.name, 'usage_count': tag.usage_count, 'description': tag.description} for tag in tags])

@app.route('/api/categories')
def get_categories():
    categories = AvailableCategory.get_all_categories()
    return jsonify([{'name': cat.name, 'usage_count': cat.usage_count, 'description': cat.description} for cat in categories])

@app.route('/manage_tags')
def manage_tags():
    tags = AvailableTag.get_all_tags()
    categories = AvailableCategory.get_all_categories()
    return render_template('manage_tags.html', tags=tags, categories=categories)

@app.route('/add_tag', methods=['POST'])
def add_tag():
    data = request.get_json()
    tag_name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not tag_name:
        return jsonify({'success': False, 'error': 'Tag name is required'})
    
    try:
        tag = AvailableTag.add_tag(tag_name, description)
        return jsonify({'success': True, 'tag': {
            'id': tag.id,
            'name': tag.name,
            'description': tag.description,
            'usage_count': tag.usage_count
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Tag already exists'})

@app.route('/add_category', methods=['POST'])
def add_category():
    data = request.get_json()
    category_name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not category_name:
        return jsonify({'success': False, 'error': 'Category name is required'})
    
    try:
        category = AvailableCategory.add_category(category_name, description)
        return jsonify({'success': True, 'category': {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'usage_count': category.usage_count
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Category already exists'})

@app.route('/delete_tag/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    tag = AvailableTag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = AvailableCategory.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'success': True})

# Initialize database
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)