#!/usr/bin/env bash

echo "🔒 Security Verification Script"
echo "==============================="

echo ""
echo "🔍 Checking repository for SSH key leaks..."

# Check for SSH key patterns in the repository
KEY_PATTERNS=(
    "ssh-rsa"
    "ssh-ed25519" 
    "ssh-ecdsa"
    "AAAAB3NzaC1"
    "AAAAC3NzaC1"
    "-----BEGIN.*PRIVATE KEY-----"
    "-----BEGIN.*PUBLIC KEY-----"
)

found_secrets=false

for pattern in "${KEY_PATTERNS[@]}"; do
    if grep -r "$pattern" . --exclude-dir=.git --exclude-dir=node_modules --exclude="*.log" 2>/dev/null; then
        echo "⚠️  Found potential SSH key content: $pattern"
        found_secrets=true
    fi
done

if [ "$found_secrets" = true ]; then
    echo ""
    echo "❌ SECURITY ISSUE: SSH key content found in repository!"
    echo "🔧 Please remove any SSH keys from tracked files"
    echo "📋 Check .gitignore and remove sensitive files"
else
    echo "✅ No SSH key content found in repository"
fi

echo ""
echo "🔍 Checking for sensitive files..."

SENSITIVE_FILES=(
    "id_rsa"
    "id_ed25519"
    "id_ecdsa"
    "*.pem"
    "*.key"
    "authorized_keys"
    ".env"
    "secrets.txt"
)

for file_pattern in "${SENSITIVE_FILES[@]}"; do
    if find . -name "$file_pattern" -not -path "./.git/*" -not -path "./node_modules/*" 2>/dev/null | grep -q .; then
        echo "⚠️  Found sensitive files matching: $file_pattern"
        find . -name "$file_pattern" -not -path "./.git/*" -not -path "./node_modules/*"
        found_secrets=true
    fi
done

if [ "$found_secrets" != true ]; then
    echo "✅ No sensitive files found in working directory"
fi

echo ""
echo "🔍 Checking .gitignore coverage..."

if [ -f .gitignore ]; then
    echo "✅ .gitignore exists"
    
    # Check if important patterns are covered
    REQUIRED_PATTERNS=("*.key" "*.pem" ".env" "id_*" ".ssh/")
    missing_patterns=false
    
    for pattern in "${REQUIRED_PATTERNS[@]}"; do
        if ! grep -q "$pattern" .gitignore; then
            echo "⚠️  .gitignore missing pattern: $pattern"
            missing_patterns=true
        fi
    done
    
    if [ "$missing_patterns" != true ]; then
        echo "✅ .gitignore has good security coverage"
    fi
else
    echo "⚠️  No .gitignore file found"
    echo "📋 Create one to prevent sensitive file commits"
fi

echo ""
echo "🔍 Testing error handling in start.sh..."

if [ -f "start.sh" ]; then
    echo "✅ start.sh exists"
    
    # Check if error handling is present
    if grep -q "exit 1" start.sh && grep -q "docker compose build" start.sh; then
        echo "✅ start.sh has proper error handling"
    else
        echo "⚠️  start.sh may need better error handling"
    fi
else
    echo "❌ start.sh not found"
fi

echo ""
echo "🔍 Verifying Docker setup..."

REQUIRED_FILES=("Dockerfile" "docker-compose.yml" "supervisord.conf")
all_files_present=true

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        all_files_present=false
    fi
done

echo ""
echo "📋 Security Summary:"
echo "=================="

if [ "$found_secrets" = true ]; then
    echo "❌ SECURITY ISSUES FOUND - Fix before committing!"
elif [ "$all_files_present" = true ]; then
    echo "✅ Repository appears secure for public sharing"
    echo "✅ No SSH keys or secrets found"
    echo "✅ Required files present"
else
    echo "⚠️  Missing required files but no security issues"
fi

echo ""
echo "🔧 To test the build process:"
echo "  1. Make sure you have SSH keys: ls ~/.ssh/"
echo "  2. Run: ./start.sh"
echo "  3. Verify no secrets in logs: docker compose logs | grep -i 'ssh-'"