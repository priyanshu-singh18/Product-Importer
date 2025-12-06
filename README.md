# Acme Product Importer

A production-ready Django application for importing and managing products from CSV files. Designed with **Clean Architecture** principles, supports async processing of up to 500,000 products with real-time progress updates.

## 🏗️ Architecture Highlights

- **Clean Architecture** with Repository, Service, and Strategy patterns
- **Type-Safe DTOs** using Pydantic for validation at boundaries
- **Async Processing** via Celery for handling large CSV imports
- **Presigned URL Uploads** - clients upload directly to storage (S3/R2/Local)
- **Real-time Progress** via Django Channels WebSocket
- **Extensible Design** - swap storage backends, webhook dispatchers, validators
- **Production-Ready** - Docker, CI/CD, comprehensive testing

## 🚀 Features

✅ **CSV Import** - Upload up to 500k products with chunked processing  
✅ **Real-time Progress** - WebSocket updates during import (status, stage, percentage)  
✅ **Product CRUD** - Full REST API with filters, pagination, search  
✅ **Bulk Operations** - Bulk delete with confirmation  
✅ **Webhooks** - Configurable webhooks with HMAC signing and delivery tracking  
✅ **SKU Uniqueness** - Case-insensitive SKU deduplication  
✅ **Category & Tags** - Flexible product organization  
✅ **API Documentation** - Auto-generated Swagger/ReDoc

## 📋 Tech Stack

| Component      | Technology                            |
| -------------- | ------------------------------------- |
| **Framework**  | Django 4.2 + Django REST Framework    |
| **Database**   | PostgreSQL with optimized indexes     |
| **Task Queue** | Celery + Redis                        |
| **Real-time**  | Django Channels (WebSocket)           |
| **Storage**    | Cloudflare R2 (S3-compatible) / Local |
| **Validation** | Pydantic v2 for type-safe DTOs        |
| **Deployment** | Docker + Docker Compose               |
| **API Docs**   | drf-spectacular (Swagger/ReDoc)       |

## 🏃 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL 15+
- Redis 7+

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd Product-Importer
cp .env.example .env
```

### 2. Run with Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# In another terminal, run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

**Services**:

- API: http://localhost:8000
- Admin: http://localhost:8000/admin
- API Docs: http://localhost:8000/api/docs/
- WebSocket: ws://localhost:8000/ws/import/{job_id}/

### 3. Local Development (Alternative)

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup PostgreSQL locally or use docker-compose for just db & redis
docker-compose up db redis -d

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run Django server (in one terminal)
python manage.py runserver

# Run Celery worker (in another terminal)
celery -A acme_importer worker -l info

# Run Celery beat (optional, for scheduled tasks)
celery -A acme_importer beat -l info
```

## 📡 API Usage

### CSV Import Flow (Presigned URL)

#### Step 1: Get Presigned Upload URL

```bash
curl -X POST http://localhost:8000/api/imports/presign/ \
  -H "Content-Type: application/json" \
  -d '{"filename": "products.csv"}'
```

Response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_url": "http://localhost:8000/api/storage/upload/",
  "fields": { "key": "imports/550e8400.../products.csv" },
  "expires_in": 3600
}
```

#### Step 2: Upload CSV to Storage

```bash
# For local storage
curl -X POST http://localhost:8000/api/storage/upload/ \
  -F "key=imports/550e8400.../products.csv" \
  -F "file=@scripts/sample_data/products_sample.csv"

# For S3/R2, use the presigned URL with multipart form upload
```

#### Step 3: Mark Upload Complete

```bash
curl -X POST http://localhost:8000/api/imports/{job_id}/complete/
```

Response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "ws_url": "/ws/import/550e8400-e29b-41d4-a716-446655440000/"
}
```

#### Step 4: Connect WebSocket for Progress

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/ws/import/550e8400-e29b-41d4-a716-446655440000/"
);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.percent}% - ${data.stage}`);
};
```

### Product Management

List products with filters:

```bash
curl http://localhost:8000/api/products/?sku=LAPTOP&active=true&page=1
```

Create product:

```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "NEW-001",
    "name": "New Product",
    "description": "Description here",
    "price": "99.99",
    "active": true
  }'
```

Bulk delete all products:

```bash
curl -X POST http://localhost:8000/api/products/bulk-delete/ \
  -H "X-Confirm-Delete: DELETE"
```

### Webhooks

Create webhook:

```bash
curl -X POST http://localhost:8000/api/webhooks/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Import Completion Webhook",
    "url": "https://webhook.site/unique-url",
    "event": "import.completed",
    "secret": "my-secret-key",
    "enabled": true
  }'
```

Test webhook:

```bash
curl -X POST http://localhost:8000/api/webhooks/{webhook_id}/test/
```

Response:

```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 145,
  "response_body": "OK"
}
```

## 🏛️ Clean Architecture Design

### Layer Separation

```
┌─────────────────────────────────────────────────────────┐
│  Presentation Layer (views.py, serializers.py)         │
│  - DRF ViewSets                                         │
│  - Request/Response handling                            │
├─────────────────────────────────────────────────────────┤
│  Service Layer (services.py)                            │
│  - ImportService, ProductService                        │
│  - Business logic (framework-agnostic)                  │
│  - Uses Pydantic DTOs                                   │
├─────────────────────────────────────────────────────────┤
│  Repository Layer (repositories.py)                     │
│  - ProductRepository, ImportJobRepository               │
│  - Abstract data access                                 │
├─────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                    │
│  - StorageBackend (S3/Local)                           │
│  - WebhookDispatcher (HTTP/Kafka)                      │
│  - ProgressNotifier (WebSocket/SSE)                     │
└─────────────────────────────────────────────────────────┘
```

### Extensibility Examples

**Swap Storage Backend:**

```python
# In settings.py
STORAGE_BACKEND = 's3'  # or 'local', 'azure'

# Easy to add new backend:
class AzureBlobStorage(StorageBackend):
    def generate_presigned_upload(self, key, expires_in):
        # Azure implementation
        pass
```

**Add Custom Validator:**

```python
@ProductValidatorRegistry.register
def validate_price_range(row: dict) -> Optional[str]:
    price = row.get('price')
    if price and float(price) > 10000:
        return "Price exceeds maximum limit"
```

**Swap Webhook Dispatcher:**

```python
class KafkaWebhookDispatcher(WebhookDispatcher):
    def dispatch(self, event, payload):
        # Send to Kafka topic instead of HTTP
        producer.send('webhook-events', value=payload)
```

## 📊 Database Schema

**Key Design Decisions:**

- `sku_normalized` for case-insensitive uniqueness
- Optimized indexes on frequently queried fields
- Foreign key relationships with `SET_NULL` for data integrity
- UUID primary keys for import jobs (distributed systems friendly)

**Models:**

- `Product` - Main product model with SKU, name, price, active status
- `Category`, `Tag` - Flexible product organization
- `ImportJob` - Tracks CSV import jobs with progress
- `ImportError` - Audit log for import validation errors
- `Webhook` - Webhook configuration with HMAC signing
- `WebhookDelivery` - Delivery tracking for debugging

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=products --cov=webhooks --cov=core

# Run specific test
pytest products/tests/test_services.py::test_import_service
```

## 🔐 Security

- HMAC webhook signing (SHA-256)
- Bulk delete protection (requires confirmation header)
- Input validation via Pydantic
- SQL injection protection (Django ORM)
- CORS configuration for production

## 📈 Performance Optimizations

1. **Chunked Processing** - Process 10k products at a time
2. **bulk_create with update_conflicts** - Single SQL statement for upsert
3. **Database Indexes** - On sku_normalized, active, status, created_at
4. **Prefetch Related** - Reduce N+1 queries for categories/tags
5. **Async Workers** - Celery prevents timeout on large imports
6. **Direct Storage Upload** - Clients upload to S3/R2, bypassing Django

## 🚢 Deployment

### Render (Recommended for Demo)

1. **Create Render Account** - Free tier available
2. **Create Services**:

   - Web Service (Django)
   - Background Worker (Celery)
   - PostgreSQL database
   - Redis instance

3. **Environment Variables**:

   ```
   DATABASE_URL=<from Render PostgreSQL>
   REDIS_URL=<from Render Redis>
   SECRET_KEY=<generate secure key>
   STORAGE_BACKEND=s3
   R2_BUCKET_NAME=<your bucket>
   R2_ENDPOINT_URL=<cloudflare R2 URL>
   R2_ACCESS_KEY_ID=<your key>
   R2_SECRET_ACCESS_KEY=<your secret>
   ```

## 📖 API Documentation

Visit `/api/docs/` for interactive Swagger UI or `/api/redoc/` for ReDoc documentation.

## 🤝 Interview Talking Points

1. **Clean Architecture** - Business logic separated from framework
2. **SOLID Principles** - Dependency inversion, single responsibility
3. **Production Patterns** - Presigned URLs avoid timeout, chunking for memory
4. **Extensibility** - Strategy pattern for storage, adapter for webhooks
5. **Type Safety** - Pydantic DTOs catch errors at boundaries
6. **Real-world Scale** - Handles 500k products with progress tracking
7. **Testability** - Mock storage/repos easily for unit tests

## 📝 License

MIT License
