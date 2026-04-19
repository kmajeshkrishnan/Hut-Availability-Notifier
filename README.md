# Opfinger Hütte Availability Notifier

A robust monitoring service that tracks the availability of the Opfinger Hütte (forest hut) in Freiburg, Germany. The service automatically scrapes the official booking website and provides a REST API to query availability data.

## Features

- **Automated Monitoring**: Scrapes availability data every 30 minutes (configurable)
- **Status Tracking**: Monitors weekend availability (Fridays and Saturdays) for the next 3 months
- **Change Detection**: Logs notifications when availability status changes
- **REST API**: Provides endpoints to query availability and notification history
- **Health Monitoring**: Comprehensive health checks and status endpoints
- **Data Cleanup**: Automatic cleanup of old data to prevent database bloat
- **Error Handling**: Robust error handling with retry logic and logging
- **Docker Support**: Easy deployment with Docker Compose

## Status Types

- **free** (green): Available for booking
- **booked** (red): Fully booked

## API Endpoints

### Health & Monitoring
- `GET /` - Basic status information
- `GET /health` - Comprehensive health check
- `GET /stats` - Application statistics
- `GET /scheduler/status` - Scheduler status

### Data Endpoints
- `GET /availability?status={free|booked}&limit=100` - Get availability data
- `GET /notifications?limit=20` - Get recent notifications

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hut-availability-notifier
   ```

2. **Create environment file**
   ```bash
   cp sample_env .env
   # Edit .env with your database credentials
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Check the application**
   ```bash
   # Check if the service is running
   curl http://localhost:8005/health
   
   # View API documentation
   open http://localhost:8005/docs
   ```

## Configuration

The application uses environment variables for configuration. Copy `sample_env` to `.env` and modify as needed:

```env
POSTGRES_USER=freiburg_user
POSTGRES_PASSWORD=supersecret
POSTGRES_DB=freiburg_db
DB_HOST=db
DB_PORT=5432
CHECK_INTERVAL_MINUTES=30
```

### Available Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | user | Database username |
| `POSTGRES_PASSWORD` | password | Database password |
| `POSTGRES_DB` | db | Database name |
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 5432 | Database port |
| `CHECK_INTERVAL_MINUTES` | 30 | Scraping interval in minutes |
| `MONTHS_AHEAD` | 3 | Number of months ahead to check for availability |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

**Note:** `max_availability_age_days` is automatically calculated as `(MONTHS_AHEAD * 30) + 30` to ensure data cleanup doesn't remove records that are still being monitored.

## Development

### Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database**
   ```bash
   # Start PostgreSQL
   docker run -d --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
   ```

3. **Set environment variables**
   ```bash
   export POSTGRES_USER=user
   export POSTGRES_PASSWORD=password
   export POSTGRES_DB=db
   export DB_HOST=localhost
   ```

4. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
   ```

### Project Structure

```
app/
├── main.py          # FastAPI application
├── config.py        # Configuration management
├── database.py      # Database connection and session management
├── models.py        # SQLAlchemy models
├── crud.py          # Database operations
├── scraper.py       # Web scraping logic
└── scheduler.py      # Background job scheduling
```

## Monitoring

### Health Checks

The application provides several health check endpoints:

- **Basic Health**: `GET /health` - Returns overall system health
- **Database**: Checks database connectivity
- **Scheduler**: Verifies background job status

### Logging

The application uses structured logging with the following levels:
- **DEBUG**: Detailed debugging information
- **INFO**: General information about operations
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages for failed operations
- **CRITICAL**: Critical errors that may cause service failure

Logs are written to both console and `app.log` file.

### Metrics

Access application statistics via the `/stats` endpoint:
- Total availability records
- Count by status (free/booked)
- Scheduler status
- Last update timestamp

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check database credentials in `.env`
   - Ensure PostgreSQL is running
   - Verify network connectivity

2. **Scraping Failures**
   - Check internet connectivity
   - Verify the target website is accessible
   - Review logs for specific error messages

3. **Scheduler Not Running**
   - Check `/scheduler/status` endpoint
   - Review application logs
   - Restart the application if needed

### Log Analysis

```bash
# View application logs
docker-compose logs -f app

# Check specific log levels
docker-compose logs app | grep ERROR
docker-compose logs app | grep WARNING
```

## Security Considerations

- Database credentials are stored in environment variables
- No authentication is implemented (consider adding for production)
- Input validation is performed on all API endpoints
- SQL injection protection via SQLAlchemy ORM

## Production Deployment

### Recommended Production Settings

1. **Environment Variables**
   ```env
   LOG_LEVEL=WARNING
   CHECK_INTERVAL_MINUTES=15
   ```

2. **Database**
   - Use a managed PostgreSQL service
   - Enable connection pooling
   - Set up regular backups

3. **Monitoring**
   - Set up health check monitoring
   - Configure log aggregation
   - Monitor database performance

4. **Security**
   - Add API authentication
   - Use HTTPS
   - Implement rate limiting
   - Regular security updates

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8005/docs
- **ReDoc**: http://localhost:8005/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Create an issue in the repository
