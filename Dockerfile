# Base stage with common setup
#FROM python:3.9-slim as base
# full debian image, need tools that might not be in slim
FROM python:3.9 as base
# Build arguments
ARG SSH_PUB_KEY
ARG USER_UID=1000
ARG USER_GID=1000

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create user with specified UID/GID and setup directories
RUN groupadd -g ${USER_GID} devuser && \
    useradd -u ${USER_UID} -g ${USER_GID} -m -s /bin/bash devuser && \
    mkdir -p /home/devuser/app /home/devuser/logs

# SSH setup with error checking and debugging
# SECURITY NOTE: SSH_PUB_KEY is passed as build arg at runtime only
# No SSH keys are ever stored in the Docker image or filesystem
# Keys are read from local ~/.ssh/ and passed temporarily during build
RUN mkdir -p /home/devuser/.ssh && \
    if [ -n "${SSH_PUB_KEY}" ] && [ "${SSH_PUB_KEY}" != "" ]; then \
        echo "Setting up SSH key..."; \
        echo "${SSH_PUB_KEY}" > /home/devuser/.ssh/authorized_keys; \
        echo "SSH key content:"; \
        head -c 50 /home/devuser/.ssh/authorized_keys; \
        echo "..."; \
    else \
        echo "WARNING: No SSH public key provided!"; \
        echo "# No SSH key provided during build" > /home/devuser/.ssh/authorized_keys; \
    fi && \
    chmod 700 /home/devuser/.ssh && \
    chmod 600 /home/devuser/.ssh/authorized_keys && \
    chown -R devuser:devuser /home/devuser/.ssh && \
    echo "cd ~/app" >> /home/devuser/.bashrc && \
    chown devuser:devuser /home/devuser/.bashrc

# SSH daemon setup with better configuration
RUN mkdir -p /var/run/sshd /var/log && \
    echo "# SSH Configuration" > /etc/ssh/sshd_config && \
    echo "Port 22" >> /etc/ssh/sshd_config && \
    echo "PermitRootLogin no" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config && \
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "AuthorizedKeysFile %h/.ssh/authorized_keys" >> /etc/ssh/sshd_config && \
    echo "ChallengeResponseAuthentication no" >> /etc/ssh/sshd_config && \
    echo "UsePAM yes" >> /etc/ssh/sshd_config && \
    echo "X11Forwarding yes" >> /etc/ssh/sshd_config && \
    echo "PrintMotd no" >> /etc/ssh/sshd_config && \
    echo "AcceptEnv LANG LC_*" >> /etc/ssh/sshd_config && \
    echo "Subsystem sftp /usr/lib/openssh/sftp-server" >> /etc/ssh/sshd_config && \
    echo "LogLevel VERBOSE" >> /etc/ssh/sshd_config

# Create log directories and copy supervisord config
RUN mkdir -p /var/log/supervisor /etc/supervisor/conf.d
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Set working directory for devuser
WORKDIR /home/devuser/app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------------------------------
# STAGE: starting - Simple Flask app for getting started
# --------------------------------------------------------------------------------------
FROM base as starting

# Copy application files
COPY . .

# Create simple starting app
RUN mkdir -p templates && \
    cat > app.py << 'EOF'
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

# Create stage-specific supervisord config for starting mode
RUN sed -i 's|python run.py|python app.py|g' /etc/supervisor/supervisord.conf

# Set permissions
RUN chown -R devuser:devuser /home/devuser/app

EXPOSE 22 5000

# --------------------------------------------------------------------------------------
# STAGE: development - Full development environment
# --------------------------------------------------------------------------------------
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest black flake8 pylint

# Copy application files
COPY . .

# Set permissions
RUN chown -R devuser:devuser /home/devuser/app

EXPOSE 22 5000

# --------------------------------------------------------------------------------------
# STAGE: production - Optimized for deployment  
# --------------------------------------------------------------------------------------
FROM base as production

# Copy application files
COPY . .

# Install production dependencies only
RUN pip install --no-cache-dir gunicorn

# Create production supervisord config with gunicorn
RUN sed -i 's|python run.py|/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 blog_publisher_main:app|g' /etc/supervisor/supervisord.conf

# Set permissions
RUN chown -R devuser:devuser /app

EXPOSE 22 5000