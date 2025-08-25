# Factory GitHub App

Minimal webhook handler for OHDSI Study Factory portfolio synchronization.

## Features

- **Webhook Handler**: Receives GitHub webhook events
- **Stage Tracking**: Updates Factory issues when study stages change
- **JWT Authentication**: Secure GitHub App authentication
- **Stateless**: No database required

## Setup

### 1. Create GitHub App

1. Go to Settings → Developer settings → GitHub Apps → New GitHub App
2. Configure:
   - **Name**: Factory Sync App
   - **Homepage URL**: Your app URL
   - **Webhook URL**: `https://your-app.com/webhook`
   - **Webhook secret**: Generate a secure secret
   - **Permissions**:
     - Issues: Read & Write
     - Contents: Read
   - **Subscribe to events**:
     - Issues
3. Generate and download private key

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values:
# - GITHUB_APP_ID
# - GITHUB_APP_PRIVATE_KEY_PATH
# - GITHUB_APP_WEBHOOK_SECRET
# - FACTORY_REPO
```

### 3. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python main.py

# Or with uvicorn
uvicorn main:app --reload
```

### 4. Test

```bash
# Run tests
python test_app.py

# Test webhook with ngrok
ngrok http 8000
# Update GitHub App webhook URL with ngrok URL
```

## Docker Deployment

```bash
# Build image
docker build -t factory-app .

# Run container
docker run -p 8000:8000 \
  -e GITHUB_APP_ID=123456 \
  -e GITHUB_APP_WEBHOOK_SECRET=secret \
  -v /path/to/private-key.pem:/app/private-key.pem \
  factory-app
```

## Cloud Deployment

### Heroku
```bash
heroku create factory-app
heroku config:set GITHUB_APP_ID=123456
heroku config:set GITHUB_APP_WEBHOOK_SECRET=secret
git push heroku main
```

### Google Cloud Run
```bash
gcloud run deploy factory-app \
  --source . \
  --set-env-vars GITHUB_APP_ID=123456
```

## Architecture

```
main.py         - FastAPI application and webhook endpoint
auth.py         - JWT creation and token management
handlers.py     - Event-specific logic
test_app.py     - Test suite
```

## Event Flow

1. Study repository issue gets labeled with `stage:*`
2. GitHub sends webhook to Factory App
3. App verifies signature and processes event
4. App updates Factory tracking issue with new stage
5. Factory portfolio reflects current study status

## Security

- Webhook signatures verified on all requests
- JWT tokens expire after 10 minutes
- Installation tokens cached for 55 minutes
- No secrets in code or logs
- Runs as non-root user in container

## Monitoring

- Health check: `GET /healthz`
- Logs: Application logs to stdout
- Metrics: Add your APM tool (optional)

## Troubleshooting

### App not receiving webhooks
- Check webhook URL in GitHub App settings
- Verify webhook secret matches
- Check Recent Deliveries in GitHub App settings

### Authentication failures
- Verify private key file exists and is readable
- Check APP_ID matches GitHub App
- Ensure app is installed on target repositories

### Token errors
- Installation tokens expire after 1 hour
- JWT must be regenerated every 10 minutes
- Check system time is synchronized