#!/usr/bin/env python3
"""
Minimal run.py for testing Docker setup.
Replace this with your actual application later.
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <h1>🔧 Development Mode - Minimal Test</h1>
    <p>Docker setup is working!</p>
    <p>Replace this with your actual blog_publisher_main.py</p>
    '''

@app.route('/health')
def health():
    return {'status': 'ok', 'mode': 'development_test'}

if __name__ == '__main__':
    print("Starting minimal test Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)