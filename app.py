
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Blog Publisher - Under Construction</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px;">
        <h1>🌱 Blog Publisher - Starting Mode</h1>
        <p>Your blog publisher is up and running!</p>
        <p>This is the minimal starting configuration.</p>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF
