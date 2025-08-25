# blog_publisher/routes/__init__.py
"""Route blueprints for the blog publisher application."""

# blog_publisher/routes/main.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from ..models import Setting, Post
from ..app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main dashboard showing all posts."""
    # Check if app is configured
    if not Setting.get('configured'):
        return redirect(url_for('main.setup'))
    
    posts = Post.query.order_by(Post.created_date.desc()).all()
    return render_template('index.html', posts=posts)

@main_bp.route('/setup')
def setup():
    """Initial setup page."""
    return render_template('setup.html')

@main_bp.route('/setup', methods=['POST'])
def setup_post():
    """Handle setup form submission."""
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
    return redirect(url_for('main.index'))

@main_bp.route('/settings')
def settings():
    """Settings page."""
    current_settings = {
        'blog_type': Setting.get('blog_type'),
        'blogger_blog_id': Setting.get('blogger_blog_id'),
        'blogger_client_id': Setting.get('blogger_client_id'),
        'wordpress_url': Setting.get('wordpress_url'),
        'wordpress_username': Setting.get('wordpress_username'),
    }
    return render_template('settings.html', settings=current_settings)

@main_bp.route('/settings', methods=['POST'])
def settings_post():
    """Handle settings form submission."""
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
    return redirect(url_for('main.settings'))

# blog_publisher/routes/posts.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from ..models import Post, Setting, AvailableTag, AvailableCategory
from ..api.publishers import BlogAPI
from ..app import db

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/new')
def new_post():
    """Create new post page."""
    return render_template('editor.html', post=None)

@posts_bp.route('/edit/<int:post_id>')
def edit_post(post_id):
    """Edit existing post page."""
    post = Post.query.get_or_404(post_id)
    return render_template('editor.html', post=post)

@posts_bp.route('/save', methods=['POST'])
def save_post():
    """Save post as draft."""
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

@posts_bp.route('/publish', methods=['POST'])
def publish_post():
    """Publish post to blog platform."""
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

@posts_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """Delete a post."""
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('main.index'))

# blog_publisher/routes/tags.py
from flask import Blueprint, render_template, request, jsonify
from ..models import AvailableTag, AvailableCategory
from ..app import db

tags_bp = Blueprint('tags', __name__)

@tags_bp.route('/manage')
def manage_tags():
    """Tag and category management page."""
    tags = AvailableTag.get_all_tags()
    categories = AvailableCategory.get_all_categories()
    return render_template('manage_tags.html', tags=tags, categories=categories)

@tags_bp.route('/add', methods=['POST'])
def add_tag():
    """Add a new tag."""
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

@tags_bp.route('/delete/<int:tag_id>', methods=['POST'])
def delete_tag(tag_id):
    """Delete a tag."""
    tag = AvailableTag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    return jsonify({'success': True})

@tags_bp.route('/categories/add', methods=['POST'])
def add_category():
    """Add a new category."""
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

@tags_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    """Delete a category."""
    category = AvailableCategory.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'success': True})

# blog_publisher/routes/api.py
from flask import Blueprint, jsonify
from ..models import AvailableTag, AvailableCategory

api_bp = Blueprint('api', __name__)

@api_bp.route('/tags')
def get_tags():
    """Get all available tags."""
    tags = AvailableTag.get_all_tags()
    return jsonify([{
        'name': tag.name, 
        'usage_count': tag.usage_count, 
        'description': tag.description
    } for tag in tags])

@api_bp.route('/categories')
def get_categories():
    """Get all available categories."""
    categories = AvailableCategory.get_all_categories()
    return jsonify([{
        'name': cat.name, 
        'usage_count': cat.usage_count, 
        'description': cat.description
    } for cat in categories])