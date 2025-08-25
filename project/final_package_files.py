# run.py (main entry point for development)
#!/usr/bin/env python3
"""
Development entry point for Blog Publisher.
Use this file to run the application during development.
"""

import os
from blog_publisher import create_app

if __name__ == '__main__':
    # Get configuration from environment or use default
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create the Flask application
    app = create_app(config_name)
    
    # Run the application
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Blog Publisher on http://{host}:{port}")
    print(f"Debug mode: {debug}")
    print("Press Ctrl+C to stop the server")
    
    app.run(host=host, port=port, debug=debug)

# MANIFEST.in
include README.md
include requirements.txt
include run.py
recursive-include blog_publisher/templates *.html
recursive-include blog_publisher/static *.css *.js *.png *.jpg *.gif
recursive-exclude * __pycache__
recursive-exclude * *.py[co]

# blog_publisher/utils.py
"""Utility functions for the blog publisher."""

import os
import shutil
from pathlib import Path
from .models import Setting, Post, AvailableTag, AvailableCategory
from .app import db
import json

def backup_database(backup_path=None):
    """
    Create a backup of the database and settings.
    
    Args:
        backup_path: Path to save backup file
        
    Returns:
        str: Path to backup file
    """
    if backup_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'backup_blog_publisher_{timestamp}.json'
    
    # Export all data
    data = {
        'posts': [],
        'tags': [],
        'categories': [],
        'settings': {}
    }
    
    # Export posts
    posts = Post.query.all()
    for post in posts:
        data['posts'].append({
            'title': post.title,
            'content': post.content,
            'status': post.status,
            'created_date': post.created_date.isoformat(),
            'published_date': post.published_date.isoformat() if post.published_date else None,
            'blog_target': post.blog_target,
            'external_id': post.external_id,
            'tags': post.tags,
            'categories': post.categories
        })
    
    # Export tags
    tags = AvailableTag.query.all()
    for tag in tags:
        data['tags'].append({
            'name': tag.name,
            'description': tag.description,
            'usage_count': tag.usage_count,
            'created_date': tag.created_date.isoformat()
        })
    
    # Export categories
    categories = AvailableCategory.query.all()
    for category in categories:
        data['categories'].append({
            'name': category.name,
            'description': category.description,
            'usage_count': category.usage_count,
            'created_date': category.created_date.isoformat()
        })
    
    # Export settings (excluding sensitive data)
    settings = Setting.query.all()
    for setting in settings:
        if not setting.key.endswith('_password') and not setting.key.endswith('_secret'):
            data['settings'][setting.key] = setting.value
    
    # Save to file
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return backup_path

def restore_database(backup_path):
    """
    Restore database from backup file.
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        dict: Restoration results
    """
    if not os.path.exists(backup_path):
        return {'success': False, 'error': 'Backup file not found'}
    
    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clear existing data (optional - you might want to merge instead)
        # Post.query.delete()
        # AvailableTag.query.delete()
        # AvailableCategory.query.delete()
        
        results = {
            'posts': 0,
            'tags': 0,
            'categories': 0,
            'settings': 0
        }
        
        # Restore tags
        for tag_data in data.get('tags', []):
            if not AvailableTag.query.filter_by(name=tag_data['name']).first():
                tag = AvailableTag(
                    name=tag_data['name'],
                    description=tag_data.get('description', ''),
                    usage_count=tag_data.get('usage_count', 0)
                )
                db.session.add(tag)
                results['tags'] += 1
        
        # Restore categories
        for cat_data in data.get('categories', []):
            if not AvailableCategory.query.filter_by(name=cat_data['name']).first():
                category = AvailableCategory(
                    name=cat_data['name'],
                    description=cat_data.get('description', ''),
                    usage_count=cat_data.get('usage_count', 0)
                )
                db.session.add(category)
                results['categories'] += 1
        
        # Restore posts
        for post_data in data.get('posts', []):
            post = Post(
                title=post_data['title'],
                content=post_data['content'],
                status=post_data.get('status', 'draft'),
                blog_target=post_data.get('blog_target'),
                external_id=post_data.get('external_id'),
                tags=post_data.get('tags', ''),
                categories=post_data.get('categories', '')
            )
            db.session.add(post)
            results['posts'] += 1
        
        # Restore settings
        for key, value in data.get('settings', {}).items():
            Setting.set(key, value)
            results['settings'] += 1
        
        db.session.commit()
        
        return {'success': True, 'results': results}
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

def init_default_tags():
    """Initialize some default tags for new installations."""
    default_tags = [
        ('tutorial', 'Step-by-step guides and tutorials'),
        ('howto', 'How-to guides and instructions'),
        ('python', 'Python programming content'),
        ('web-development', 'Web development topics'),
        ('tips', 'Quick tips and tricks'),
        ('beginner', 'Content for beginners'),
        ('advanced', 'Advanced topics'),
        ('code', 'Code examples and snippets'),
        ('review', 'Reviews and evaluations'),
        ('news', 'News and updates')
    ]
    
    default_categories = [
        ('Programming', 'Programming and development topics'),
        ('Technology', 'Technology news and reviews'),
        ('Tutorials', 'Educational content and tutorials'),
        ('Personal', 'Personal thoughts and experiences'),
        ('Projects', 'Project showcases and updates')
    ]
    
    for tag_name, description in default_tags:
        AvailableTag.add_tag(tag_name, description)
    
    for cat_name, description in default_categories:
        AvailableCategory.add_category(cat_name, description)

def get_app_info():
    """Get application information."""
    from . import __version__, __author__
    return {
        'version': __version__,
        'author': __author__,
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        'database_path': Setting.get('database_path', 'Unknown'),
        'total_posts': Post.query.count(),
        'total_tags': AvailableTag.query.count(),
        'total_categories': AvailableCategory.query.count(),
        'published_posts': Post.query.filter_by(status='published').count(),
        'draft_posts': Post.query.filter_by(status='draft').count(),
    }