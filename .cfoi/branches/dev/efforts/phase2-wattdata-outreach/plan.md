# Plan: Intelligent Vendor Outreach for Search Result Enhancement

## Goal
Implement AI-driven vendor outreach system that automatically expands search results by identifying gaps in provider coverage and intelligently reaching out to missing vendors to improve search success rates and multi-provider procurement outcomes.

## Constraints
- Email-only outreach (no SMS/phone calls in MVP)
- Maximum 1 reminder email per vendor
- Must comply with CAN-SPAM (unsubscribe, physical address, honest subjects)
- WattData query response time <5s, email batch send <30s
- Usage limits: 50 vendors/row/24h, 200 vendors/user/24h, 10k platform/24h
- Vendor contact info never exposed to buyers

## Technical Approach

### SearchIntent Integration
- Add foreign key relationship: `Row.search_intent_id` → `SearchIntent.id`
- SearchIntent stores: `query_text`, `category`, `location`, `budget_range`, `service_requirements`
- Gap analysis and outreach triggers use SearchIntent data via `row.search_intent` relationship
- Migrate existing Row queries to populate search_intent_id from current query/location patterns

### Outreach Service
- **OutreachService**: Standard service following existing LLM integration patterns in `services/outreach_service.py`
- Analyzes Row.search_intent and existing results using current LLM service integration
- Triggers when: B2B/local service categories + <3 search results + location-specific queries
- Uses SearchIntent.category and SearchIntent.query_text for outreach necessity determination
- Evaluates coverage gaps using SearchIntent requirements vs existing result capabilities

### Backend Models (SQLAlchemy)
```python
# Add to Row model
class Row(Base):
    # Existing fields...
    search_intent_id: int = Column(Integer, ForeignKey('search_intents.id'))
    outreach_status: str = Column(String(50), default='none')  # none, analyzing, active, complete
    outreach_vendor_count: int = Column(Integer, default=0)
    outreach_sent_at: datetime = Column(DateTime, nullable=True)
    gap_analysis_complete: bool = Column(Boolean, default=False)
    
    # Relationship
    search_intent = relationship("SearchIntent", back_populates="rows")

# New models
class OutreachEvent(Base):
    id: int = Column(Integer, primary_key=True)
    row_id: int = Column(Integer, ForeignKey('rows.id'))
    vendor_email: str = Column(String(255))
    vendor_name: str = Column(String(255))
    vendor_source: str = Column(String(100))  # wattdata, manual
    message_id: str = Column(String(255))  # email service tracking ID
    magic_token: str = Column(String(500))  # JWT token for vendor response
    sent_at: datetime = Column(DateTime, nullable=True)
    opened_at: datetime = Column(DateTime, nullable=True)
    clicked_at: datetime = Column(DateTime, nullable=True)
    quote_submitted_at: datetime = Column(DateTime, nullable=True)
    opt_out: bool = Column(Boolean, default=False)
    user_id: int = Column(Integer, ForeignKey('users.id'))
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    row = relationship("Row", back_populates="outreach_events")

class SearchIntent(Base):
    id: int = Column(Integer, primary_key=True)
    query_text: str = Column(Text)
    category: str = Column(String(100))
    location: str = Column(String(255))
    budget_range: str = Column(String(100))
    service_requirements: str = Column(Text)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    rows = relationship("Row", back_populates="search_intent")
```

### Authentication & Authorization
```python
# Magic link token structure
class VendorMagicToken(BaseModel):
    vendor_email: str
    vendor_name: str
    row_id: int
    user_id: int  # Original search owner
    search_intent_id: int
    exp: int
    issued_at: int

# Token validation service
class VendorAuthService:
    def generate_magic_token(self, vendor_email: str, row_id: int) -> str:
        row = db.query(Row).filter(Row.id == row_id).first()
        payload = VendorMagicToken(
            vendor_email=vendor_email,
            vendor_name=vendor_name,
            row_id=row_id,
            user_id=row.user_id,
            search_intent_id=row.search_intent_id,
            exp=int(time.time()) + (7 * 24 * 3600),  # 7 days
            issued_at=int(time.time())
        )
        return jwt.encode(payload.dict(), settings.JWT_SECRET, algorithm='HS256')
    
    def validate_vendor_token(self, token: str) -> VendorMagicToken:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
            return VendorMagicToken(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
```

### New Backend Routes (FastAPI)
```python
# Add to existing routes/rows.py
@auth_required
@router.post("/api/rows/{row_id}/outreach")
async def trigger_outreach(
    row_id: int, 
    current_user: ClerkUser,
    background_tasks: BackgroundTasks
):
    row = get_user_row(row_id, current_user.id)  # Verify ownership
    if row.search_intent is None:
        raise HTTPException(status_code=400, detail="Row missing search intent")
    
    background_tasks.add_task(outreach_pipeline, row_id, current_user.id)
    return {"status": "outreach_initiated"}

# New routes/outreach.py
@router.post("/api/outreach/webhook")  # Public for email service webhooks
async def handle_email_events(webhook_data: dict):
    # Update OutreachEvent with delivery/open/click tracking
    pass

@router.get("/api/outreach/respond/{token}")  # Public magic link
async def handle_vendor_response(token: str):
    token_data = VendorAuthService().validate_vendor_token(token)
    row = db.query(Row).filter(Row.id == token_data.row_id).first()
    return {
        "search_requirements": row.search_intent.service_requirements,
        "location": row.search_intent.location,
        "budget_range": row.search_intent.budget_range,
        "vendor_context": {
            "email": token_data.vendor_email,
            "name": token_data.vendor_name
        }
    }

@router.post("/api/outreach/quote/{token}")
async def submit_vendor_quote(token: str, quote_data: dict):
    token_data = VendorAuthService().validate_vendor_token(token)
    
    # Create quote record associated with original row
    quote = VendorQuote(
        row_id=token_data.row_id,
        vendor_email=token_data.vendor_email,
        vendor_name=token_data.vendor_name,
        quote_data=quote_data,
        submitted_at=datetime.utcnow()
    )
    
    # Send in-app notification to original searcher
    await send_quote_notification(token_data.user_id, quote)
    
    return {"status": "quote_submitted"}
```

### SSE Implementation (New)
```python
# Add new routes/sse.py
from sse_starlette.sse import EventSourceResponse
import asyncio

class OutreachEventManager:
    def __init__(self):
        self.connections: Dict[int, List[asyncio.Queue]] = {}
    
    async def add_connection(self, row_id: int) -> asyncio.Queue:
        if row_id not in self.connections:
            self.connections[row_id] = []
        queue = asyncio.Queue()
        self.connections[row_id].append(queue)
        return queue
    
    async def broadcast_outreach_event(self, row_id: int, event_data: dict):
        if row_id in self.connections:
            for queue in self.connections[row_id]:
                await queue.put(event_data)

outreach_events = OutreachEventManager()

@router.get("/api/sse/outreach/{row_id}")
async def outreach_events_stream(row_id: int, current_user: ClerkUser = Depends(get_current_user)):
    # Verify user owns this row
    row = get_user_row(row_id, current_user.id)
    
    async def event_generator():
        queue = await outreach_events.add_connection(row_id)
        try:
            while True:
                event = await queue.get()
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"])
                }
        except asyncio.CancelledError:
            # Clean up connection
            if row_id in outreach_events.connections:
                outreach_events.connections[row_id].remove(queue)
    
    return EventSourceResponse(event_generator())
```

### Background Processing Architecture
```python
# services/task_queue.py - Simple in-process task queue for MVP
import asyncio
from typing import Callable, Any
from queue import Queue
import threading

class BackgroundTaskQueue:
    def __init__(self):
        self.task_queue = Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def add_task(self, func: Callable, *args, **kwargs):
        self.task_queue.put((func, args, kwargs))
    
    def _worker(self):
        while True:
            func, args, kwargs = self.task_queue.get()
            try:
                if asyncio.iscoroutinefunction(func):
                    asyncio.run(func(*args, **kwargs))
                else:
                    func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background task failed: {e}")
            finally:
                self.task_queue.task_done()

# Use in FastAPI dependency
task_queue = BackgroundTaskQueue()

# Outreach pipeline implementation
async def outreach_pipeline(row_id: int, user_id: int):
    """Complete outreach workflow"""
    try:
        # 1. Gap Analysis
        gaps = await analyze_search_gaps(row_id)
        await outreach_events.broadcast_outreach_event(row_id, {
            "type": "gap_analysis_complete",
            "data": {"gaps_found": len(gaps)}
        })
        
        # 2. Vendor Discovery
        vendors = await discover_vendors_for_gaps(row_id, gaps)
        await outreach_events.broadcast_outreach_event(row_id, {
            "type": "vendors_discovered", 
            "data": {"vendor_count": len(vendors)}
        })
        
        # 3. Send Outreach Emails
        sent_count = await send_outreach_emails(row_id, vendors)
        await outreach_events.broadcast_outreach_event(row_id, {
            "type": "outreach_sent",
            "data": {"emails_sent": sent_count}
        })
        
    except Exception as e:
        logger.error(f"Outreach pipeline failed for row {row_id}: {e}")
        await outreach_events.broadcast_outreach_event(row_id, {
            "type": "outreach_error",
            "data": {"error": str(e)}
        })
```

### Notification System Implementation
```python
# services/notification_service.py - New service for user notifications
class NotificationService:
    async def send_quote_notification(self, user_id: int, quote: VendorQuote):
        """Send in-app notification about new vendor quote"""
        notification = UserNotification(
            user_id=user_id,
            type="vendor_quote_received",
            title=f"New quote from {quote.vendor_name}",
            message=f"Received quote for your {quote.row.search_intent.category} search",
            data={"row_id": quote.row_id, "quote_id": quote.id},
            created_at=datetime.utcnow()
        )
        db.add(notification)
        await db.commit()
        
        # Broadcast via SSE if user is connected
        await outreach_events.broadcast_outreach_event(quote.row_id, {
            "type": "quote_received",
            "data": {
                "vendor_name": quote.vendor_name,
                "quote_preview": quote.quote_data.get("summary", "")
            }
        })

# Add UserNotification model
class UserNotification(Base):
    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey('users.id'))
    type: str = Column(String(100))
    title: str = Column(String(255))
    message: str = Column(Text)
    data: str = Column(JSON)  # Additional context data
    read_at: datetime = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

### WattData Integration
- Create `services/vendor_search_service.py` using direct HTTP client approach
- Implement vendor search with Redis caching (90-day TTL)
- Add exponential backoff and circuit breaker for API reliability
- Query vendors using SearchIntent location and category data via `row.search_intent` relationship
- Filter out vendors already present in existing search results

### Email Template System
- Store templates in **EmailTemplate** database table
- Template variables: `{vendor_name}`, `{search_description}`, `{buyer_location}`, `{category}`, `{magic_link}`
- Context injection via Jinja2 templating using SearchIntent data from `row.search_intent`
- Default templates for each category with fallback to generic B2B template
- Template management via admin interface (future enhancement)

### Email Service Integration
- Create `services/transactional_email_service.py` (SendGrid/Postmark)
- Generate personalized emails using database templates + SearchIntent context
- Create JWT magic link tokens with vendor/search context using VendorAuthService
- Track delivery/opens/clicks via webhook integration

### Frontend Components (Next.js/React)
- Extend `SearchResults.tsx` to show "Expanding results..." during outreach
- Add outreach status to existing provider status display patterns
- Connect to new SSE endpoint `/api/sse/outreach/{row_id}` for real-time updates
- Display "X additional vendors contacted" in search results
- Create `VendorQuoteForm.tsx` for magic link destination page

### Database Migration
```sql
-- Alembic migration
ALTER TABLE rows ADD COLUMN search_intent_id INTEGER;
ALTER TABLE rows ADD COLUMN outreach_status VARCHAR(50) DEFAULT 'none';
ALTER TABLE rows ADD COLUMN outreach_vendor_count INTEGER DEFAULT 0;
ALTER TABLE rows ADD COLUMN outreach_sent_at TIMESTAMP;
ALTER TABLE rows ADD COLUMN gap_analysis_complete BOOLEAN DEFAULT FALSE;

CREATE TABLE search_intents (
    id SERIAL PRIMARY KEY,
    query_text TEXT,
    category VARCHAR(100),
    location VARCHAR(255),
    budget_range VARCHAR(100),
    service_requirements TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE outreach_events (
    id SERIAL PRIMARY KEY,
    row_id INTEGER REFERENCES rows(id),
    vendor_email VARCHAR(255),
    vendor_name VARCHAR(255),
    vendor_source VARCHAR(100),
    message_id VARCHAR(255),
    magic_token VARCHAR(500),
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    quote_submitted_at TIMESTAMP,
    opt_out BOOLEAN DEFAULT FALSE,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(100),
    title VARCHAR(255),
    message TEXT,
    data JSONB,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rows_search_intent ON rows(search_intent_id);
CREATE INDEX idx_outreach_events_row_id ON outreach_events(row_id);
CREATE INDEX idx_outreach_events_sent_at ON outreach_events(sent_at);
CREATE INDEX idx_user_notifications_user_id ON user_notifications(user_id);
```

## Success Criteria
- [ ] OutreachService correctly identifies B2B/local service searches requiring outreach using SearchIntent data
- [ ] Search success rate improves by 25% for categories with outreach
- [ ] Average provider count per search increases from 2.3 to 4.1
- [ ] Outreach triggers automatically for <3 result searches in B2B categories
- [ ] Magic links route vendors to quote form with proper search context from JWT tokens
- [ ] Vendor quotes integrate seamlessly with existing search results via new notification system
- [ ] SSE broadcasts outreach progress via new `/api/sse/outreach/{row_id}` endpoint
- [ ] Clerk authentication properly protects user-specific outreach data with row ownership verification
- [ ] WattData vendor queries complete in <5s with 95% success rate
- [ ] Email compliance achieves <0.1% spam complaint rate
- [ ] Outreach-generated quotes improve price range coverage by 40%

## Dependencies
- **WattData API integration** for vendor discovery
- **New SearchIntent model and Row relationship** for gap analysis context
- **Existing LLM service** for category classification and outreach determination
- **Transactional email service** (SendGrid/Postmark) account
- **New SSE infrastructure** for real-time outreach updates
- **New background task queue system** for async outreach processing
- **New notification system** for buyer quote alerts
- **Clerk auth system** for user context and permissions
- **Redis cache** for WattData response caching
- **JWT token system** for vendor magic link authentication

## Risks
- **Low search result improvement** - Monitor success rate metrics, adjust trigger thresholds
- **WattData API reliability** - Implement circuit breaker, graceful degradation to cached results  
- **Email deliverability issues** - Domain authentication, sender reputation monitoring
- **Service over-triggering outreach** - Tune classification thresholds based on SearchIntent category performance
- **Vendor response quality** - Implement vendor rating system, filter low-quality responders
- **Performance impact on search** - Async background processing via task queue, no blocking operations
- **Privacy compliance** - Implement vendor consent tracking, data retention policies
- **Magic link security** - JWT expiration (7 days), rate limiting on quote submission endpoint
- **Background task reliability** - Task queue persistence, error handling and retry logic
- **SSE connection management** - Connection cleanup, memory usage monitoring