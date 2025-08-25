# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="blog-publisher",
    version="0.1.0",
    author="Carolyn Boyle",
    author_email="your.email@example.com",
    description="A Flask application for creating and publishing blog posts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carolynboyle/blog-publisher",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Flask",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "blog_publisher": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
    entry_points={
        "console_scripts": [
            "blog-publisher=blog_publisher.cli:main",
        ],
    },
)

# blog_publisher/__init__.py
"""
Blog Publisher - A Flask application for creating and publishing blog posts.
"""

__version__ = "0.1.0"
__author__ = "Carolyn Boyle"

from .app import create_app

__all__ = ["create_app"]

# blog_publisher/config.py
import os
from pathlib import Path

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Instance folder for database and user-specific files
    INSTANCE_PATH = Path.cwd() / 'instance'
    INSTANCE_PATH.mkdir(exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{INSTANCE_PATH / "blog_publisher.db"}'

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DEVELOPMENT = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    DEVELOPMENT = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# blog_publisher/app.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import config

# Initialize extensions
db = SQLAlchemy()

def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    from .routes.main import main_bp
    from .routes.posts import posts_bp
    from .routes.tags import tags_bp
    from .routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp, url_prefix='/posts')
    app.register_blueprint(tags_bp, url_prefix='/tags')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

# blog_publisher/models.py
from datetime import datetime
from .app import db

class Setting(db.Model):
    """Application settings storage."""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    
    @staticmethod
    def get(key, default=None):
        """Get a setting value."""
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value):
        """Set a setting value."""
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

class AvailableTag(db.Model):
    """Available tags for posts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    description = db.Column(db.String(200))
    
    @staticmethod
    def get_all_tags():
        """Get all tags ordered by usage count."""
        return AvailableTag.query.order_by(AvailableTag.usage_count.desc()).all()
    
    @staticmethod
    def add_tag(name, description=''):
        """Add a new tag."""
        tag = AvailableTag.query.filter_by(name=name.strip()).first()
        if not tag:
            tag = AvailableTag(name=name.strip(), description=description)
            db.session.add(tag)
            db.session.commit()
        return tag
    
    @staticmethod
    def increment_usage(tag_names):
        """Increment usage count for tags."""
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
    """Available categories for posts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=0)
    description = db.Column(db.String(200))
    
    @staticmethod
    def get_all_categories():
        """Get all categories ordered by usage count."""
        return AvailableCategory.query.order_by(AvailableCategory.usage_count.desc()).all()
    
    @staticmethod
    def add_category(name, description=''):
        """Add a new category."""
        category = AvailableCategory.query.filter_by(name=name.strip()).first()
        if not category:
            category = AvailableCategory(name=name.strip(), description=description)
            db.session.add(category)
            db.session.commit()
        return category
    
    @staticmethod
    def increment_usage(category_names):
        """Increment usage count for categories."""
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
    """Blog post model."""
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
    
    def __repr__(self):
        return f'<Post {self.title}>'

# blog_publisher/cli.py
import os
import click
from .app import create_app

@click.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config', default='development', help='Configuration to use')
def main(host, port, debug, config):
    """Run the Blog Publisher application."""
    app = create_app(config)
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()