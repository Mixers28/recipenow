# Backend Logging Guide

This guide explains how to use the logging system in the RecipeNow API backend.

## Overview

The backend uses Python's standard `logging` module with a centralized configuration that writes logs to:
- **Console**: Real-time output during development and production
- **App Log File**: `/var/log/recipe-now/app.log` - All application logs
- **Error Log File**: `/var/log/recipe-now/error.log` - Error-level logs and above

## Accessing Logs

### Local Development
```bash
# View console output during local development
python -m uvicorn main:app --reload

# Check log files (if running with file logging enabled)
tail -f logs/app.log
tail -f logs/error.log
```

### Production (Railway)
```bash
# SSH into Railway container or use Railway CLI
railway logs

# View specific log file
cat /var/log/recipe-now/app.log
```

## Log Format

- **Console**: `LEVEL - Message`
- **File**: `TIMESTAMP [Module:LineNumber] LEVEL - Message`

Example log file output:
```
2024-01-10 14:30:45,123 [routers.recipes:187] ERROR - List recipes failed: Database connection error
2024-01-10 14:30:46,456 [routers.pantry:92] INFO - Operation successful: create_pantry_item
```

## Using Logging in Code

### Basic Usage

In any module, import and use the logger:

```python
from logging_config import get_logger

logger = get_logger(__name__)

# Log at different levels
logger.debug("Debug message - detailed info for developers")
logger.info("Info message - general information")
logger.warning("Warning message - something unexpected")
logger.error("Error message - something went wrong")
logger.critical("Critical message - system failure")
```

### Using Error Handler

For standardized error handling and logging, use the `error_handler` module:

```python
from error_handler import APIError
from fastapi import HTTPException

try:
    # Some operation
    result = do_something()
except ValueError as e:
    raise APIError.handle_validation_error(
        operation="create_recipe",
        error=e,
        user_id=user_id,
        extra_context={"recipe_title": title}
    )
except Exception as e:
    raise APIError.handle_generic_error(
        operation="create_recipe",
        error=e,
        user_id=user_id,
        extra_context={"recipe_title": title}
    )
```

### Example in a Route Handler

```python
from fastapi import APIRouter, Depends
from logging_config import get_logger
from error_handler import APIError

logger = get_logger(__name__)
router = APIRouter()

@router.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: str, user_id: str = None):
    try:
        APIError.log_operation_start("get_recipe", user_id, {"recipe_id": recipe_id})

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Your business logic here
        recipe = repo.get_by_id(recipe_id)
        if not recipe:
            raise APIError.handle_not_found_error("Recipe", recipe_id, user_id)

        APIError.log_operation_success("get_recipe", user_id)
        return recipe

    except HTTPException:
        raise
    except Exception as e:
        raise APIError.handle_generic_error(
            "get_recipe",
            e,
            user_id,
            {"recipe_id": recipe_id}
        )
```

## Log Levels Explained

- **DEBUG** (10): Detailed information, typically of interest only when diagnosing problems
- **INFO** (20): Confirmation that things are working as expected
- **WARNING** (30): An indication that something unexpected happened, or indicative of some problem in the future
- **ERROR** (40): A serious problem, a software component has failed
- **CRITICAL** (50): A serious error, the program itself may be unable to continue running

## Common Logging Patterns

### 1. Database Operations

```python
logger.info(f"Fetching recipe with ID: {recipe_id}")
try:
    recipe = repo.get_by_id(recipe_id)
except Exception as e:
    logger.error(f"Failed to fetch recipe {recipe_id}: {str(e)}", exc_info=True)
    raise
```

### 2. API Requests

```python
logger.info(f"Processing request: {request.method} {request.url.path}")
# ... handle request ...
logger.info(f"Request completed successfully with status {status_code}")
```

### 3. Business Logic

```python
APIError.log_operation_start("match_recipes", user_id)
try:
    matches = algorithm.find_matches(pantry_items)
    APIError.log_operation_success("match_recipes", user_id)
except Exception as e:
    raise APIError.handle_generic_error("match_recipes", e, user_id)
```

## Request IDs (For Tracing)

The middleware automatically captures `x-request-id` headers for request tracing:

```python
# Frontend can send request ID
fetch("/api/recipes", {
    headers: {
        "x-request-id": "request-12345"
    }
})
```

All logs for this request will be tagged with `[request-12345]` making it easy to trace through the entire request lifecycle.

## Environment-Specific Configuration

The logging level can be controlled via the `setup_logging()` function in `main.py`:

```python
# Development
setup_logging(log_level="DEBUG")

# Production
setup_logging(log_level="INFO")
```

## Log File Rotation

Log files automatically rotate when they reach 10MB:
- Old log files are numbered: `app.log.1`, `app.log.2`, etc.
- The system keeps the 5 most recent rotated log files
- Older logs are automatically deleted

## Troubleshooting

### I don't see my logs
1. Check the log level setting in `main.py`
2. Ensure logger is created with: `logger = get_logger(__name__)`
3. Check file permissions on `/var/log/recipe-now` directory

### Logs are incomplete
1. Check disk space: `df -h /var/log`
2. Verify log file permissions: `ls -la /var/log/recipe-now/`
3. Check if log rotation is working properly

### Need more verbose logging
Temporarily change `setup_logging(log_level="DEBUG")` in `main.py` for detailed output

## Integration with Monitoring

These structured logs can be integrated with monitoring services:
- **Railway**: View in Railway dashboard
- **Sentry**: Send error logs to Sentry for tracking
- **ELK Stack**: Parse logs with Elasticsearch/Logstash
- **Datadog**: Stream logs to Datadog for monitoring

For each service, you would add an additional handler in `logging_config.py`.
