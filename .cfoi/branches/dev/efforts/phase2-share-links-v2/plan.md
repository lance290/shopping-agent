# Plan: Share Links

## Goal
Implement shareable links for projects, rows, and tiles to enhance search discovery and drive North Star metric improvements. Enable shared content to guide users to successful searches through the existing rows_search system, targeting >90% search success rate from shared content and >5% share-to-signup conversion rate.

## Constraints
- Use existing SQLModel patterns with FastAPI backend
- Build on existing session-based auth (AuthSession, AuthLoginCode)
- Build on existing components (Button, Card patterns)
- Maintain existing URL structure conventions
- No breaking changes to existing project/row/tile views
- Integrate with existing ClickoutEvent affiliate tracking system
- Leverage existing rows_search routes and provider adapters

## Technical Approach

### Backend Implementation

**Database Schema (SQLModel)**
```python
# New model in apps/backend/app/models/share_link.py
class ShareLink(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    token: str = Field(unique=True, index=True)  # 32-char random string
    
    # Polymorphic resource reference
    resource_type: str = Field()  # "project", "row", "tile"
    resource_id: int = Field()
    
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime
    access_count: int = 0
    unique_visitors: int = 0
    search_initiated_count: int = 0  # users who searched after viewing share
    search_success_count: int = 0    # successful searches from this share
    signup_conversion_count: int = 0  # signups attributed to this share
    
    __table_args__ = (
        Index('ix_sharelink_resource', 'resource_type', 'resource_id'),
    )

# Extend existing User model
class User:
    referral_share_token: str | None = None  # tracks signup attribution
    signup_source: str | None = None  # "share", "direct", etc.

# Extend existing ClickoutEvent model
class ClickoutEvent:
    share_token: str | None = None  # tracks share attribution
    referral_user_id: int | None = None  # creator of the share link

# New table to track share-driven searches
class ShareSearchEvent(SQLModel, table=True):
    id: int | None = Field(primary_key=True)
    share_token: str = Field(foreign_key="sharelink.token")
    session_id: str | None = None  # anonymous tracking
    user_id: int | None = Field(foreign_key="user.id", nullable=True)
    search_query: str
    search_success: bool = False  # determined by existing search success criteria
    created_at: datetime
```

**Session-Based Anonymous Access**
```python
# Extend existing auth patterns in apps/backend/app/core/auth.py
def get_session_context(request: Request) -> dict:
    """Extend existing session handling to support anonymous share viewers"""
    session_id = request.cookies.get("session_id")
    share_token = request.path_params.get("token") or request.query_params.get("share")
    
    if session_id:
        auth_session = get_auth_session(session_id)  # existing function
        return {
            "user": auth_session.user if auth_session else None,
            "session_id": session_id,
            "is_anonymous_share": bool(share_token and not auth_session),
            "share_token": share_token
        }
    elif share_token:
        # Anonymous share viewer - create temporary session for tracking
        temp_session_id = create_temp_session(share_token)
        return {
            "user": None,
            "session_id": temp_session_id,
            "is_anonymous_share": True,
            "share_token": share_token
        }
    
    return {"user": None, "session_id": None, "is_anonymous_share": False}

# Extend existing auth decorators
def requires_interaction_auth(func):
    """Extend existing auth decorator to block anonymous share viewers"""
    def wrapper(*args, **kwargs):
        context = get_session_context(request)
        if context["is_anonymous_share"]:
            raise HTTPException(401, "Authentication required for interaction")
        return existing_auth_check(func)(*args, **kwargs)  # chain existing logic
    return wrapper
```

**API Routes**
- `POST /api/shares` - Create share link (requires existing auth)
- `GET /api/shares/{token}` - Resolve share link (public, creates temp session)
- `GET /api/shares/{token}/content` - Get shared content (public, read-only)
- `POST /api/shares/{token}/search` - Track search from share (integrates with rows_search)

**Search Integration with Existing rows_search Routes**
```python
# Extend existing apps/backend/app/routes/rows_search.py
@router.post("/search")  # existing route
@track_search_from_share  # new decorator
async def search_rows(request: RowSearchRequest, context: dict = Depends(get_session_context)):
    # Existing search logic unchanged
    results = await existing_search_logic(request)
    
    # New: Track share attribution if present
    if context.get("share_token"):
        await track_share_search_event(
            share_token=context["share_token"],
            session_id=context["session_id"],
            user_id=context.get("user", {}).get("id"),
            query=request.query,
            success=determine_search_success(results)  # existing success criteria
        )
    
    return results
```

**Search Success Rate Enhancement**
```python
# New service in apps/backend/app/services/search_enhancement.py
class SearchEnhancementService:
    def get_shared_content_search_suggestions(self, share_token: str) -> list[str]:
        """Analyze shared content to suggest high-success search queries"""
        share_link = get_share_link(share_token)
        
        if share_link.resource_type == "row":
            row = get_row(share_link.resource_id)
            return generate_search_suggestions_from_row(row)  # use existing row data
        elif share_link.resource_type == "project":
            project = get_project(share_link.resource_id)
            return generate_search_suggestions_from_project(project)
        
        return []
    
    def calculate_share_search_metrics(self) -> dict:
        """Calculate how shares improve search success rates"""
        baseline_rate = get_baseline_search_success_rate()  # existing metric
        share_driven_rate = get_share_driven_search_success_rate()
        
        return {
            "baseline_search_success_rate": baseline_rate,
            "share_driven_search_success_rate": share_driven_rate,
            "improvement_percentage": (share_driven_rate - baseline_rate) / baseline_rate * 100
        }
```

**New Backend Files**
- `apps/backend/app/models/share_link.py`
- `apps/backend/app/routes/shares.py`
- `apps/backend/app/services/share_service.py`
- `apps/backend/app/services/search_enhancement.py`
- `apps/backend/app/decorators/share_tracking.py`
- `migration: add_share_links_and_events.py`

### Frontend Implementation

**Components**
- `ShareButton` component with copy-to-clipboard functionality
- `ReadOnlyBanner` component for anonymous share viewers
- `ShareSearchSuggestions` component showing optimized queries for shared content
- `ShareMetrics` component showing search success improvements

**Session-Based Share Context**
```typescript
// Hook for share context using existing session patterns
export function useShareContext() {
  const { data: session } = useSession(); // existing hook
  const { token } = useParams();
  
  return {
    isAnonymousShare: !!token && !session?.user,
    canInteract: !token || !!session?.user,
    shareToken: token as string,
    sessionId: session?.sessionId
  };
}
```

**Search Integration Components**
```typescript
// Component to enhance search from shared content
export function ShareEnhancedSearch({ shareToken }: { shareToken: string }) {
  const suggestions = useShareSearchSuggestions(shareToken);
  
  return (
    <div>
      <SearchInput defaultSuggestions={suggestions} />
      {/* Integrates with existing rows_search components */}
    </div>
  );
}
```

**Pages**
- `/share/[token]` - Public share view with anonymous session handling
- `/metrics/search-shares` - Search success analytics from shared content
- Add ShareButton to existing pages when user is authenticated

**New Frontend Files**
- `apps/frontend/app/components/ShareButton.tsx`
- `apps/frontend/app/components/ReadOnlyBanner.tsx`
- `apps/frontend/app/components/ShareSearchSuggestions.tsx`
- `apps/frontend/app/share/[token]/page.tsx`
- `apps/frontend/app/metrics/search-shares/page.tsx`
- `apps/frontend/app/hooks/useShareContext.ts`

### Integration Points
- Extend existing session-based auth to support anonymous share viewers with temp sessions
- Integrate with existing rows_search routes to track share-driven searches
- Use existing search success criteria to measure share content impact
- Capture referral_share_token in existing signup flow
- Extend existing ClickoutEvent tracking with share attribution
- Leverage existing provider adapters and search result persistence

## Success Criteria
- [ ] ShareButton renders for authenticated users on projects, rows, tiles
- [ ] `/share/{token}` works for anonymous users with temp session creation
- [ ] Anonymous share viewers see ReadOnlyBanner and cannot interact (session-enforced)
- [ ] Share-driven searches integrate seamlessly with existing rows_search routes
- [ ] Search success rate from shared content reaches >90% (vs current baseline)
- [ ] Share-to-signup conversion rate achieves ≥5%
- [ ] ShareSearchSuggestions improve search discovery from shared content
- [ ] Share metrics dashboard shows search success impact aligned with North Star
- [ ] Broken share links show graceful 404 with search suggestions
- [ ] Performance: Share creation <200ms, resolution <300ms

## Dependencies
- Existing session-based auth (AuthSession, AuthLoginCode models)
- Current rows_search routes and provider adapters
- Existing search success criteria and analytics
- Existing User, Project, Row, Tile models
- Current ClickoutEvent affiliate tracking system
- Existing component library and routing patterns

## Risks
- **Session complexity**: Anonymous temp sessions must not conflict with existing auth flow
- **Search attribution accuracy**: Properly linking shared content to downstream search success
- **Performance with viral growth**: May need caching for popular shared content
- **Token collision**: 32-character tokens with database uniqueness constraint
- **Data privacy**: Audit shared content to exclude sensitive information
- **Search success measurement**: Ensure shared content search success uses same criteria as North Star metrics