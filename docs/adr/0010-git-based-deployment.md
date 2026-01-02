# ADR-010: Git-Based Deployment Workflow

## Status
Accepted

## Context
We need a deployment workflow that:
- Deploys code from local development to VPS production
- Allows easy rollback if issues occur
- Tracks what's deployed (version control)
- Minimizes deployment steps
- Works for both code and configuration changes

## Decision
We use **Git-based deployment** workflow:
1. Develop locally
2. Commit and push to GitHub
3. SSH into VPS
4. Pull latest code
5. Rebuild frontend (if needed)
6. Restart services

### Implementation Details:
- Repository: GitHub (`gerritsxd/ais-vessel-tracker`)
- Branch: `master` (main production branch)
- VPS location: `/var/www/apihub`
- Deployment steps:
  ```bash
  cd /var/www/apihub
  git pull origin master
  cd frontend && npm run build
  sudo systemctl restart ais-web-tracker
  ```
- No automated CI/CD deployment (manual for now)
- Database migrations: Manual (SQL scripts if needed)

## Consequences

### Positive:
- ✅ **Version control** - All deployments tracked in git history
- ✅ **Easy rollback** - `git checkout <previous-commit>` to rollback
- ✅ **Simple workflow** - Standard git commands, no complex tooling
- ✅ **Code review** - Can review changes before deploying
- ✅ **Branching** - Can use branches for features (merge to master when ready)
- ✅ **No extra tools** - Git is standard, no deployment tools needed

### Negative:
- ❌ **Manual process** - Must SSH and run commands manually
- ❌ **No zero-downtime** - Service restart causes brief downtime
- ❌ **No automated testing** - Must manually test after deployment
- ❌ **Error-prone** - Easy to forget steps (could script it)

### Trade-offs:
- **Simplicity over automation**: Manual deployment is simpler but requires more steps
- **Control over convenience**: Manual gives more control but less convenience
- **Git over specialized tools**: Using standard git vs. deployment-specific tools

## Alternatives Considered

### Automated CI/CD (GitHub Actions)
- **Pros**: Automatic deployment on push, no manual steps
- **Cons**: More complex setup, requires SSH keys/secrets management
- **Future consideration**: Could add automated deployment later

### Docker deployment
- **Pros**: Consistent environment, easy rollback, containerization
- **Cons**: More complex, requires Docker setup, overkill for single VPS
- **Rejected**: Unnecessary complexity for our use case

### Rsync deployment
- **Pros**: Fast file transfer, can exclude files
- **Cons**: No version control, harder to rollback
- **Rejected**: Git provides better version control

### FTP/SFTP deployment
- **Pros**: Simple file transfer
- **Cons**: No version control, manual file management
- **Rejected**: Git is better for version control

## Implementation Details

### Local Development
```bash
# Make changes
git add .
git commit -m "Description of changes"
git push origin master
```

### VPS Deployment
```bash
# SSH into VPS
ssh erik@gerritsxd.com

# Pull latest code
cd /var/www/apihub
git pull origin master

# Rebuild frontend (if frontend changes)
cd frontend
npm run build

# Restart services (if backend changes)
sudo systemctl restart ais-web-tracker
sudo systemctl restart ais-collector  # if needed
```

### Rollback Process
```bash
# On VPS
cd /var/www/apihub
git log --oneline  # Find previous commit
git checkout <previous-commit-hash>
sudo systemctl restart ais-web-tracker
```

## Future Improvements

### Potential Enhancements:
1. **Deployment script** - Automate the deployment steps
2. **GitHub Actions** - Automated deployment on push to master
3. **Health checks** - Verify service is running after deployment
4. **Database migrations** - Automated migration scripts
5. **Blue-green deployment** - Zero-downtime deployments

## Related ADRs
- ADR-007: Systemd services (restarted during deployment)
- ADR-008: Nginx reverse proxy (may need reload after config changes)

## References
- Git documentation: https://git-scm.com/doc
- Deployment guide: `docs/DEPLOYMENT.md`

