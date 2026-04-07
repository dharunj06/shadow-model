# GitHub Actions CI/CD Pipeline Setup

Your project now has a complete GitHub Actions pipeline with build, test, and push capabilities. Follow these steps to configure GitHub environments for approval gates.

## 1. Create GitHub Environments

Navigate to your repository settings and create environments for deployment approval gates:

### Using GitHub UI:
1. Go to **Settings** → **Environments** → **New Environment**
2. Create these environments:
   - `staging`
   - `production`

### Using GitHub CLI:
```bash
# Create staging environment
gh api repos/{owner}/{repo}/environments \
  -X POST \
  -f name='staging' \
  -f deployment_branch_policy='{"protected_branches": true}'

# Create production environment
gh api repos/{owner}/{repo}/environments \
  -X POST \
  -f name='production' \
  -f deployment_branch_policy='{"protected_branches": true}'
```

## 2. Configure Approval Requirements (Optional)

For **production** environment, require approvals:

### Using GitHub UI:
1. Go to **Settings** → **Environments** → **production**
2. Enable **Required reviewers**
3. Add team members or your GitHub username
4. Check **Prevent reviewers from approving their own deployments**

### Using GitHub CLI:
```bash
gh api repos/{owner}/{repo}/environments/production \
  -X PUT \
  -F 'required_approvers=1' \
  -F 'reviewers=[{"type":"User","id":REVIEWER_ID}]'
```

## 3. Pipeline Workflow

### On Pull Request:
- ✅ Runs backend tests (pytest + linting with ruff)
- ✅ Runs frontend tests (npm lint + npm build)
- ❌ Does **NOT** build or push Docker images

### On Push to Main:
- ✅ Runs all tests
- ✅ Builds 4 Docker images:
  - `mlops-backend:latest`
  - `mlops-frontend:latest`
  - `mlops-model-v1:latest`
  - `mlops-model-v2:latest`
- ✅ Pushes images to GitHub Container Registry (ghcr.io)
- ✅ Publishes summary with image tags

## 4. Docker Images Location

All images are pushed to:
```
ghcr.io/{github-username}/shadowml-{service}:latest
```

Example:
```bash
ghcr.io/myusername/shadowml-backend:latest
ghcr.io/myusername/shadowml-frontend:latest
ghcr.io/myusername/shadowml-model-v1:latest
ghcr.io/myusername/shadowml-model-v2:latest
```

## 5. Update docker-compose.yml to Use Pipeline Images

After pipeline completes, update your `docker-compose.yml`:

```yaml
services:
  backend:
    image: ghcr.io/{github-username}/shadowml-backend:latest
  
  frontend:
    image: ghcr.io/{github-username}/shadowml-frontend:latest
  
  model_v1:
    image: ghcr.io/{github-username}/shadowml-model-v1:latest
  
  model_v2:
    image: ghcr.io/{github-username}/shadowml-model-v2:latest
```

Then deploy:
```bash
docker compose pull
docker compose up -d
```

## 6. Monitor Pipeline

### View Logs:
- Go to **Actions** tab in your repository
- Click on the workflow run to see detailed logs

### Common Issues:

**Tests failing?**
- Check backend: `cd backend && pytest tests/ -v`
- Check frontend: `cd frontend && npm run build`

**Images not pushing?**
- Verify `GITHUB_TOKEN` has `packages: write` permission
- Check that you're pushing to main branch

## 7. Next Steps (Optional)

To add deployment to production, update `.github/workflows/ci-cd.yml`:

```yaml
deploy:
  name: Deploy to Production
  runs-on: ubuntu-latest
  needs: build-images
  if: github.ref == 'refs/heads/main'
  environment: production  # Requires approval!
  
  steps:
    - name: Deploy
      run: |
        docker compose pull
        docker compose up -d
```

---

**Questions?** Check the [GitHub Actions documentation](https://docs.github.com/en/actions) or view the workflow file at `.github/workflows/ci-cd.yml`
