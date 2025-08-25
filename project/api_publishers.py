# blog_publisher/api/__init__.py
"""API clients for publishing to various blog platforms."""

# blog_publisher/api/publishers.py
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..models import Setting

class BlogAPI:
    """Main API class for publishing to different blog platforms."""
    
    @staticmethod
    def publish_to_blogger(post, credentials):
        """
        Publish post to Blogger using Google API.
        
        Args:
            post: Post model instance
            credentials: Google OAuth2 credentials
            
        Returns:
            str: External post ID from Blogger
            
        Raises:
            Exception: If publishing fails
        """
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
        """
        Publish post to WordPress using REST API.
        
        Args:
            post: Post model instance
            
        Returns:
            str: External post ID from WordPress
            
        Raises:
            Exception: If publishing fails
        """
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
            auth=(wp_user, wp_password),
            timeout=30
        )
        
        if response.status_code == 201:
            return response.json()['id']
        else:
            raise Exception(f"WordPress API error: {response.text}")

# blog_publisher/api/blogger.py
"""Blogger-specific API functionality."""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..models import Setting

class BloggerAPI:
    """Blogger API client with OAuth2 support."""
    
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    
    @classmethod
    def get_auth_url(cls):
        """
        Get OAuth2 authorization URL for Blogger.
        
        Returns:
            str: Authorization URL for user to visit
        """
        client_id = Setting.get('blogger_client_id')
        client_secret = Setting.get('blogger_client_secret')
        
        if not client_id or not client_secret:
            raise Exception("Blogger OAuth credentials not configured")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:5000/auth/blogger/callback"]
                }
            },
            scopes=cls.SCOPES
        )
        flow.redirect_uri = "http://localhost:5000/auth/blogger/callback"
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # Store state for validation
        Setting.set('blogger_oauth_state', state)
        
        return authorization_url
    
    @classmethod
    def handle_callback(cls, code, state):
        """
        Handle OAuth2 callback and store credentials.
        
        Args:
            code: Authorization code from callback
            state: State parameter for validation
            
        Returns:
            bool: True if successful
        """
        stored_state = Setting.get('blogger_oauth_state')
        if state != stored_state:
            raise Exception("Invalid OAuth state")
        
        client_id = Setting.get('blogger_client_id')
        client_secret = Setting.get('blogger_client_secret')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:5000/auth/blogger/callback"]
                }
            },
            scopes=cls.SCOPES
        )
        flow.redirect_uri = "http://localhost:5000/auth/blogger/callback"
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store credentials securely (in production, use proper encryption)
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        import json
        Setting.set('blogger_credentials', json.dumps(creds_data))
        
        return True
    
    @classmethod
    def get_credentials(cls):
        """
        Get stored Blogger credentials.
        
        Returns:
            Credentials: Google OAuth2 credentials or None
        """
        creds_json = Setting.get('blogger_credentials')
        if not creds_json:
            return None
        
        import json
        creds_data = json.loads(creds_json)
        
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        # Refresh if needed
        if credentials.expired:
            credentials.refresh(Request())
            # Update stored credentials
            updated_creds = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            Setting.set('blogger_credentials', json.dumps(updated_creds))
        
        return credentials

# blog_publisher/api/wordpress.py
"""WordPress-specific API functionality."""

import requests
from ..models import Setting

class WordPressAPI:
    """WordPress REST API client."""
    
    @classmethod
    def test_connection(cls):
        """
        Test WordPress API connection.
        
        Returns:
            dict: Connection test results
        """
        wp_url = Setting.get('wordpress_url')
        wp_user = Setting.get('wordpress_username')
        wp_password = Setting.get('wordpress_password')
        
        if not all([wp_url, wp_user, wp_password]):
            return {'success': False, 'error': 'WordPress credentials not configured'}
        
        try:
            # Test with a simple GET request to posts endpoint
            api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories"
            response = requests.get(
                api_url,
                auth=(wp_user, wp_password),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except requests.exceptions.RequestException:
            return []
    
    @classmethod
    def get_tags(cls):
        """
        Get WordPress tags.
        
        Returns:
            list: Available WordPress tags
        """
        wp_url = Setting.get('wordpress_url')
        wp_user = Setting.get('wordpress_username')
        wp_password = Setting.get('wordpress_password')
        
        if not all([wp_url, wp_user, wp_password]):
            return []
        
        try:
            api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/tags"
            response = requests.get(
                api_url,
                auth=(wp_user, wp_password),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except requests.exceptions.RequestException:
            return []posts"
            response = requests.get(
                api_url,
                auth=(wp_user, wp_password),
                params={'per_page': 1},
                timeout=10
            )
            
            if response.status_code == 200:
                return {'success': True, 'message': 'WordPress connection successful'}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
                
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Connection error: {str(e)}'}
    
    @classmethod
    def get_categories(cls):
        """
        Get WordPress categories.
        
        Returns:
            list: Available WordPress categories
        """
        wp_url = Setting.get('wordpress_url')
        wp_user = Setting.get('wordpress_username')
        wp_password = Setting.get('wordpress_password')
        
        if not all([wp_url, wp_user, wp_password]):
            return []
        
        try:
            api_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/