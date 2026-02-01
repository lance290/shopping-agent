# Plan: Procurement Collaboration Links Implementation

## Goal
Implement public sharing links for projects and rows to enable procurement collaboration and user acquisition, with initial 5% share-to-signup conversion rate, advancing North Star metrics through improved procurement process efficiency and measured viral growth.

## Constraints
- Share links must be permanent (no expiration in MVP)
- Shared viewers get read-only access without authentication required
- Maximum 50 share links per project to prevent abuse
- Share creation requires authentication (Clerk)
- Must support viral traffic (100+ concurrent unauthenticated viewers)
- Link generation <200ms, resolution <300ms
- 99.9% availability for business-critical procurement workflows

## Technical Approach

### Backend Infrastructure Validation & Implementation

#### 1. Model Discovery & Validation
```python
# First validate existing models and ownership patterns
# Confirm Project model structure and user relationship
# Validate Row model (vs search results) and persistence
# Audit existing authentication patterns in current routes
```

#### 2. Database Schema (Alembic Migration)
```python
# Extend User model for referral tracking
class User(Base):
    # ... existing fields ...
    referred_by = Column(UUID, ForeignKey("users.id"), nullable=True)
    referral_count = Column(Integer, default=0)
    signup_via_share = Column(Boolean, default=False)
    
# New ShareLink model
class ShareLink(Base):
    __tablename__ = "share_links"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    resource_type = Column(Enum("project", "row"), nullable=False)  # Scope to validated entities
    resource_id = Column(UUID, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    signup_count = Column(Integer, default=0)
    
    # Bidirectional relationships
    creator = relationship("User", back_populates="share_links")
    
    __table_args__ = (Index("ix_resource", "resource_type", "resource_id"),)

# Update User model
class User(Base):
    # ... existing fields ...
    share_links = relationship("ShareLink", back_populates="creator")
```

#### 3. Authentication Pattern Alignment
```python
# Match existing Clerk integration patterns from current codebase
# Use actual auth dependency injection pattern (not assumed Depends structure)
# Validate user ownership using existing model relationships
```

#### 4. Share Creation Endpoints
```python
# Scope to confirmed entities only
@router.post("/projects/{project_id}/share")  # Match existing auth pattern
async def create_project_share(project_id: UUID, current_user=existing_auth_dependency):
    # Validate project ownership using existing patterns
    # Check 50 link limit per project
    # Generate cryptographically secure token
    
@router.post("/rows/{row_id}/share")  # Only if rows are persistent entities
async def create_row_share(row_id: UUID, current_user=existing_auth_dependency):
    # Validate row exists and user has access
    # Follow same patterns as project shares
```

#### 5. Public Share Resolution
```python
@router.get("/share/{token}")  # No auth required
async def resolve_share_link(token: str, ref: Optional[UUID] = None):
    # Public access with full data exposure for viral growth
    # Increment access_count
    # Track referral attribution
    # Return 404 for invalid tokens
```

### Frontend Implementation

#### 1. Route Structure Validation
```tsx
// Confirm Next.js App Router structure matches existing patterns
// Validate share/[token] doesn't conflict with current routing
// Use existing layout and component patterns
```

#### 2. Share Components
```tsx
// components/ShareButton.tsx - Match existing UI patterns
// components/ShareModal.tsx - Use existing modal/toast systems
// Follow current TypeScript and styling conventions
```

#### 3. Public Share Page
```tsx
// [share-route]/[token]/page.tsx - Based on confirmed routing structure
// Public view (no auth) with read-only procurement data
// Prominent signup CTAs with value proposition
// Referral attribution tracking
// 404 handling for invalid tokens
```

#### 4. Viral Growth Features
- Share-to-signup conversion tracking (target 5% baseline)
- Referral attribution via URL parameters
- Signup CTA optimization on shared pages
- Mobile-responsive viral sharing experience

### Analytics & Measurement

#### 1. Conversion Tracking
- Share creation events
- Share access (unauthenticated views)
- Share-to-signup conversions
- Referral attribution success

#### 2. K-Factor Calculation
```
K = (Average shares per user) × (Conversion rate from share to signup)
Initial target: Establish baseline, optimize toward >1.0
```

#### 3. Dashboard Integration
- Leverage existing analytics infrastructure
- Share performance metrics
- Viral coefficient measurement
- User acquisition attribution

## Success Criteria
- [ ] Validate Project and Row models support sharing functionality
- [ ] Share buttons appear on confirmed resource types (projects, rows if persistent)
- [ ] Copy link generates unique shareable URL in <200ms
- [ ] Unauthenticated users view shared content in read-only mode
- [ ] Share links resolve with <300ms latency
- [ ] 5% baseline share-to-signup conversion rate
- [ ] Referral attribution tracks conversions accurately
- [ ] 50 link limit enforced per project
- [ ] Invalid tokens return proper 404
- [ ] Mobile responsive sharing experience

## Dependencies
- **Critical Path**: Validate existing Project/Row model structure and ownership patterns
- Existing Clerk authentication system (pattern confirmation needed)
- Confirmed API endpoints and routing structure
- Existing UI component library and styling system
- Database migration deployment process
- Analytics infrastructure for conversion tracking

## Risks & Mitigations
- **Model validation failure**: Audit existing codebase first, scope to confirmed entities only
- **Auth pattern mismatch**: Align with actual Clerk implementation before development
- **Route conflicts**: Validate Next.js routing structure compatibility
- **Conversion assumptions**: Start with 5% baseline, optimize based on actual data
- **Data exposure**: Audit sensitive procurement data before public sharing
- **Orphaned shares**: Implement cleanup on resource deletion

## North Star Alignment
This feature advances procurement efficiency and measured user acquisition by:
- **Collaborative workflows**: Public sharing enables cross-organizational procurement collaboration
- **User acquisition**: Share-to-signup funnel with baseline 5% conversion tracking
- **Procurement efficiency**: Reduced cycle time through collaborative supplier discovery
- **Market intelligence**: Public procurement data showcases platform value
- **Sustainable growth**: Measured viral mechanics with realistic conversion expectations