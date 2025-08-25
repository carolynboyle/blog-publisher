# simple_app.py (Starting Mode App for Gunicorn)
from flask import Flask, render_template_string
import os

# Create the Flask application instance
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'

# Read the application mode from the environment variable
mode = os.environ.get('APP_MODE', 'starting')

# Define the HTML template for the starting page
STARTING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog Publisher - {{ mode|title }} Mode</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .mode-container {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem 0;
        }
        .mode-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 2rem;
            margin: 1rem;
        }
        .mode-indicator {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .mode-starting { background: #e3f2fd; color: #1976d2; }
        .mode-development { background: #fff3e0; color: #f57c00; }
        .mode-production { background: #e8f5e8; color: #388e3c; }
    </style>
</head>
<body>
    <div class="mode-container">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="mode-card text-center">
                        <span class="mode-indicator mode-{{ mode }}">{{ mode|title }} Mode</span>
                        <h1 class="display-4 mb-4">🚧 Blog Publisher</h1>
                        
                        {% if mode == 'starting' %}
                            <div class="alert alert-info">
                                <strong>Starting Mode Active!</strong><br>
                                Perfect for getting your feet wet. Simple Flask app running.
                            </div>
                            <h3>Ready to switch modes?</h3>
                            <p>Edit <code>.env</code> file and change <code>MODE=starting</code> to:</p>
                            <div class="row mt-4">
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h5>Development Mode</h5>
                                            <code>MODE=development</code>
                                            <p class="mt-2">Full dev environment with all tools</p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h5>Production Mode</h5>
                                            <code>MODE=production</code>
                                            <p class="mt-2">Full package installation</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {% endif %}
                        
                        <div class="mt-4">
                            <a href="/test" class="btn btn-primary me-2">Test Route</a>
                            <a href="/mode" class="btn btn-outline-secondary">Mode Info</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(STARTING_TEMPLATE, mode=mode)

@app.route('/test')
def test():
    return {
        'status': 'success',
        'mode': mode,
        'message': f'Flask is working in {mode} mode!',
        'container': 'Docker adaptive environment'
    }

@app.route('/mode')
def mode_info():
    return {
        'current_mode': mode,
        'available_modes': ['starting', 'development', 'production'],
        'switch_instructions': 'Edit .env file and change MODE variable, then: docker-compose up --build -d'
    }

# The 'if __name__ == "__main__":' block is removed because Gunicorn will run the app directly.
# The 'app' instance is exposed to Gunicorn, which handles the running of the server.
