#!/usr/bin/env bash

# This script builds and runs the Docker container for the Blog Publisher project.
# It is designed to be portable and flexible, automatically detecting the user's
# SSH public key for secure access.

# -----------------------------------------------------------
# SECTION 1: PRE-FLIGHT CHECK - VALIDATE SSH KEY
# -----------------------------------------------------------
echo "🔍 Checking for required SSH key files..."

# Check if the .ssh directory exists
if [ ! -d "$HOME/.ssh" ]; then
    echo "❌ ERROR: The ~/.ssh directory was not found!" >&2
    echo "Please generate an SSH key pair first by running: ssh-keygen -t ed25519" >&2
    exit 1
fi

# Function to find the user's public key for the Docker build
find_public_key() {
    local default_keys=(
        "$HOME/.ssh/id_ed25519.pub"
        "$HOME/.ssh/id_rsa.pub"
        "$HOME/.ssh/id_ecdsa.pub"
    )

    echo "🔑 Looking for SSH public keys..."
    for key_file in "${default_keys[@]}"; do
        if [ -f "$key_file" ]; then
            echo "✅ Found SSH key: $key_file"
            # Validate key format
            if ssh-keygen -l -f "$key_file" >/dev/null 2>&1; then
                echo "✅ SSH key is valid"
                cat "$key_file"
                return 0
            else
                echo "⚠️  SSH key file exists but appears invalid: $key_file"
            fi
        else
            echo "❌ No key found at: $key_file"
        fi
    done
    return 1
}

# Find the SSH public key and store it in a variable
echo "🔍 Detecting SSH public key..."
SSH_PUB_KEY=$(find_public_key)

if [ -z "$SSH_PUB_KEY" ]; then
    echo "❌ ERROR: No valid SSH public key found!" >&2
    echo ""
    echo "📋 To fix this:"
    echo "1. Generate a new SSH key: ssh-keygen -t ed25519 -C 'your-email@example.com'"
    echo "2. Or check existing keys: ls -la ~/.ssh/"
    echo "3. Make sure key files have correct permissions: chmod 644 ~/.ssh/*.pub"
    echo ""
    exit 1
fi

echo "✅ SSH public key detected and validated!"
echo "🔑 Key preview: ${SSH_PUB_KEY:0:50}..."

# -----------------------------------------------------------
# SECTION 2: INTERACTIVE MODE SELECTION
# -----------------------------------------------------------

# Function to prompt for stage
prompt_for_stage() {
    while true; do
        read -p "Choose stage (1-3): " choice
        echo ""
        case $choice in
            1)
                echo "starting"
                return
                ;;
            2)
                echo "development"
                return
                ;;
            3)
                echo "production"
                return
                ;;
            *)
                echo "❌ Invalid choice. Please enter 1, 2, or 3"
                echo ""
                ;;
        esac
    done
}

# Check if .env exists and prompt for update
handle_env_file() {
    if [ -f .env ]; then
        current_mode=$(grep "^MODE=" .env | cut -d'=' -f2)
        echo "📄 Found existing .env file with mode: $current_mode"
        echo ""
        read -p "Update configuration? (y/N): " update_env
        
        if [[ $update_env =~ ^[Yy]$ ]]; then
            echo ""
            echo "📋 Available stages:"
            echo ""
            echo "1) starting    🌱 Simple Flask app, perfect for getting started"
            echo "                  - Minimal dependencies (Flask only)"
            echo "                  - 'Under construction' webpage"
            echo "                  - Quick setup, instant gratification"
            echo ""
            echo "2) development 🔧 Full development environment"
            echo "                  - All dev tools (pytest, black, flake8)"
            echo "                  - Package structure support"
            echo "                  - Interactive bash shell"
            echo ""
            echo "3) production  🚀 Optimized for deployment"
            echo "                  - Full package installation"
            echo "                  - Minimal runtime image"
            echo "                  - Auto-starts blog-publisher command"
            echo ""
            
            mode=$(prompt_for_stage)
            create_env $mode
            echo ""
        else
            echo "ℹ️  Using existing .env configuration"
            current_mode=$(grep "^MODE=" .env | cut -d'=' -f2)
            MODE=$current_mode
            echo ""
        fi
    else
        echo "📄 No .env file found. Let's create one!"
        echo ""
        echo "📋 Available stages:"
        echo ""
        echo "1) starting    🌱 Simple Flask app, perfect for getting started"
        echo "                  - Minimal dependencies (Flask only)"
        echo "                  - 'Under construction' webpage"
        echo "                  - Quick setup, instant gratification"
        echo ""
        echo "2) development 🔧 Full development environment"
        echo "                  - All dev tools (pytest, black, flake8)"
        echo "                  - Package structure support"
        echo "                  - Interactive bash shell"
        echo ""
        echo "3) production  🚀 Optimized for deployment"
        echo "                  - Full package installation"
        echo "                  - Minimal runtime image"
        echo "                  - Auto-starts blog-publisher command"
        echo ""
        
        mode=$(prompt_for_stage)
        create_env $mode
        echo ""
    fi
}

# Create or update .env file
create_env() {
    local mode=$1
    
    echo "📄 Creating .env file with $mode mode..."
    cat > .env << EOF
MODE=$mode
USER_UID=$(id -u)
USER_GID=$(id -g)
FLASK_ENV=development
EOF
    echo "✅ Created .env file"
    MODE=$mode
}

# -----------------------------------------------------------
# SECTION 3: READ ENVIRONMENT VARIABLES
# -----------------------------------------------------------

# Handle .env file interactively
handle_env_file

# Set default values if not present
USER_UID=${USER_UID:-$(id -u)}
USER_GID=${USER_GID:-$(id -g)}

# -----------------------------------------------------------
# SECTION 4: BUILD AND RUN DOCKER CONTAINER
# -----------------------------------------------------------
echo "🐳 Building and running the Docker container..."
echo "Container mode: $MODE"
echo "User ID: $USER_UID"
echo "Group ID: $USER_GID"

# Export variables for docker-compose
export MODE
export USER_UID
export USER_GID
export SSH_PUB_KEY

echo "🔨 Starting build process..."

# Build and start the container with proper error checking
echo "🔨 Building Docker image..."
if ! docker compose build; then
    echo ""
    echo "❌ Docker build failed!"
    echo ""
    echo "🔍 Common causes:"
    echo "1. Dockerfile syntax error"
    echo "2. Missing required files"
    echo "3. Network connectivity issues"
    echo "4. Invalid SSH key format"
    echo ""
    echo "📋 Debugging steps:"
    echo "1. Check build output above for specific errors"
    echo "2. Verify all required files exist: ls -la Dockerfile docker-compose.yml requirements.txt"
    echo "3. Test SSH key format: ssh-keygen -l -f ~/.ssh/id_*.pub"
    echo "4. Clean and retry: docker system prune -f && ./start.sh"
    echo ""
    exit 1
fi

echo "✅ Build completed successfully!"
echo ""
echo "🚀 Starting containers..."

if ! docker compose up --detach; then
    echo ""
    echo "❌ Container startup failed!"
    echo ""
    echo "🔍 Debugging steps:"
    echo "1. Check startup logs: docker compose logs"
    echo "2. Check port conflicts: netstat -tlnp | grep -E '(5000|2222)'"
    echo "3. Verify containers: docker ps -a"
    echo "4. Clean restart: docker compose down && docker compose up -d"
    echo ""
    exit 1
fi

# Wait a moment for services to start
echo "⏳ Waiting for services to start..."
sleep 3

# Verify the container is actually running
CONTAINER_NAME="blog-publisher-$MODE"
if ! docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" --format "{{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
    echo ""
    echo "❌ Container is not running after startup!"
    echo ""
    echo "📋 Container status:"
    docker ps -a --filter "name=$CONTAINER_NAME"
    echo ""
    echo "📋 Container logs:"
    docker compose logs --tail=20
    echo ""
    exit 1
fi

# Test if the web service is responding
echo "🌐 Testing web service..."
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|404\|500"; then
    echo "⚠️  Web service may not be ready yet (this is often normal)"
    echo "   Check logs if issues persist: docker compose logs -f"
else
    echo "✅ Web service is responding"
fi

echo ""
echo "🎉 Container started successfully!"
echo ""
echo "🌐 Web Interface: http://localhost:5000"
echo "🔐 SSH Access: ssh -p 2222 devuser@localhost"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker compose logs -f"
echo "  Stop container: docker compose down"
echo "  Rebuild: docker compose up --build"
echo "  Debug SSH: ./debug-ssh.sh"
echo ""
echo "🔍 If SSH doesn't work immediately:"
echo "  ssh -vvv -p 2222 devuser@localhost"
echo "  docker exec -it $CONTAINER_NAME bash"