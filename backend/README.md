# Email Server Backend

A Python FastAPI backend for email management with AWS SES integration, Redis caching, and comprehensive API endpoints.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Redis**: Caching and data storage
- **AWS SES**: Email sending service integration
- **Rate Limiting**: Configurable email sending rate limits
- **Contact Management**: CSV upload, contact lists, and filtering
- **Email Templates**: Create and manage email templates
- **Email Tracking**: Open and click tracking
- **Scheduled Emails**: Schedule emails for future delivery
- **File Uploads**: Image and file upload support

## Quick Start

### Prerequisites

- Python 3.11+
- Redis server
- AWS SES account with credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
uvicorn main:app --reload
```

### Using Docker

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

## Configuration

Environment variables (see `.env.example`):

- `PORT`: Server port (default: 3001)
- `NODE_ENV`: Environment (development/production)
- `REDIS_URL`: Redis connection URL
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_DEFAULT_REGION`: AWS region
- `AWS_SES_FROM_EMAIL`: Default sender email
- `SENDER_NAME`: Sender name for emails
- `EMAIL_RATE_LIMIT_MS`: Minimum interval between emails (ms)
- `EMAIL_MAX_PER_MINUTE`: Max emails per minute
- `EMAIL_MAX_PER_HOUR`: Max emails per hour

## API Endpoints

### Contacts
- `GET /api/contacts` - List contacts with filtering
- `GET /api/contacts/filters` - Get filter values
- `POST /api/contacts/upload-csv` - Upload CSV contacts
- `GET /api/contacts/lists` - Get contact lists
- `POST /api/contacts/lists` - Create contact list
- `GET /api/contacts/lists/{list_id}` - Get contacts in list
- `POST /api/contacts/lists/{list_id}/upload-csv` - Upload to list
- `DELETE /api/contacts/lists/{list_id}` - Delete contact list

### Templates
- `GET /api/templates` - List templates
- `GET /api/templates/{id}` - Get template
- `POST /api/templates` - Create template
- `PUT /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

### Emails
- `GET /api/emails` - List sent emails
- `GET /api/emails/scheduled` - List scheduled emails
- `GET /api/emails/{id}` - Get email detail
- `POST /api/emails/send` - Send email immediately
- `POST /api/emails/preview` - Preview email
- `POST /api/emails/schedule` - Schedule email
- `POST /api/emails/{id}/cancel` - Cancel scheduled email

### Tracking
- `GET /api/track/open/{tracking_id}.png` - Track email open
- `GET /api/track/click/{tracking_id}` - Track link click

### Uploads
- `POST /api/uploads/image` - Upload image
- `POST /api/uploads/image-base64` - Upload base64 image

### Rate Limiting
- `GET /api/rate-limit/config` - Get rate limiter config
- `PUT /api/rate-limit/config` - Update rate limiter config
- `POST /api/rate-limit/reset` - Reset rate limiter

## Testing

Run tests with pytest:
```bash
pytest
```

## Deployment

### Docker Deployment

```bash
docker-compose up -d
```

### Production Deployment

1. Set up environment variables
2. Build Docker image:
```bash
docker build -t email-server .
```
3. Run with proper environment configuration

### Manual Deployment

1. Install dependencies
2. Configure environment variables
3. Run with production settings:
```bash
uvicorn main:app --host 0.0.0.0 --port 3001
```

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
└── app/
    ├── api/              # API route definitions
    │   ├── contacts.py
    │   ├── templates.py
    │   ├── emails.py
    │   ├── tracking.py
    │   ├── uploads.py
    │   └── rate_limit.py
    ├── data/             # Data access layer
    │   ├── contacts.py
    │   ├── emails.py
    │   ├── templates.py
    │   └── redis_client.py
    ├── models/           # Pydantic models
    │   ├── contact.py
    │   ├── email.py
    │   ├── template.py
    │   └── rate_limit.py
    ├── services/         # Business logic
    │   └── email_service.py
    ├── utils/            # Utility functions
    │   ├── helpers.py
    │   └── rate_limiter.py
    └── middleware/       # Middleware
        └── error_handler.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.