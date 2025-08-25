# Security Notes

## SSH Key Handling

This project requires SSH access to the development container but **never stores SSH keys in the repository or Docker images**.

### How SSH Keys Are Handled

1. **Runtime Only**: SSH public keys are read from your local `~/.ssh/` directory at build time
2. **Build Arguments**: Keys are passed as Docker build arguments (not stored in images)
3. **Temporary**: Keys exist only in the running container, not in image layers
4. **Local Source**: Only YOUR keys from YOUR machine are used

### What Gets Built Into the Container

- ✅ SSH daemon configuration
- ✅ User account setup
- ✅ Directory structure
- ❌ **NO SSH KEYS** (added at runtime only)

### What's Protected by .gitignore

- SSH key files (`*.pub`, `id_*`, etc.)
- Environment files (`.env`, `*.secret`)
- Database files (`*.db`, `instance/`)
- Build artifacts and logs

### Verification

You can verify no SSH keys are in the repository:

```bash
# Search for potential SSH key content
grep -r "ssh-" . --exclude-dir=.git
grep -r "AAAAB3NzaC1" . --exclude-dir=.git
grep -r "ssh-rsa\|ssh-ed25519\|ssh-ecdsa" . --exclude-dir=.git

# Should return no results in source files
```

### For Contributors

If you fork this repository:

1. Your SSH keys remain on YOUR machine only
2. No SSH keys will ever be committed to version control
3. Each user's container uses their own SSH keys
4. Multiple developers can work safely without key conflicts

### Build Process Security

```bash
# Keys are read from local system
SSH_PUB_KEY=$(cat ~/.ssh/id_*.pub)

# Passed as build argument (not stored in image)
docker build --build-arg SSH_PUB_KEY="$SSH_PUB_KEY" .

# Container gets the key for SSH access
# Image layers contain NO key material
```

This approach ensures that:
- SSH keys never leak into version control
- Each developer uses their own keys
- No secrets are embedded in Docker images
- The repository can be safely public