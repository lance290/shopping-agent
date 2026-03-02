# User Isolation - TODO

**Date**: 2026-01-09
**Priority**: High
**Status**: Pending

## Issue
Currently all users see everyone else's chats/searches. Need to isolate data by user.

## What needs to change
1. Associate `Row` records with a `user_id` (foreign key to `User`)
2. Filter all queries by the authenticated user's ID
3. Update API endpoints to only return/modify user's own data

## Affected areas
- `apps/backend/models.py` - Add `user_id` to `Row` model
- `apps/backend/main.py` - Filter CRUD operations by user
- Possibly frontend if any client-side filtering needed

## Notes
- User model already exists from auth implementation
- Session contains email, can look up user ID from that
