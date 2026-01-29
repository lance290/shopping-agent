# Ticketmaster Integration

## Overview

The shopping agent now integrates with Ticketmaster's Discovery API to search for event tickets. This allows users to search for concerts, sports events, theater shows, and other live events alongside traditional product searches.

## Features

- **Event Search**: Search for events by keyword (e.g., "Notre Dame vs Clemson tickets")
- **Price Information**: Displays minimum ticket prices when available
- **Event Details**: Shows venue name, date, and time in the result title
- **Images**: High-resolution event images from Ticketmaster
- **Direct Links**: Click-through links to purchase tickets on Ticketmaster.com

## Setup

### 1. Get a Ticketmaster API Key

1. Visit the [Ticketmaster Developer Portal](https://developer.ticketmaster.com/)
2. Create a free account or sign in
3. Navigate to "My Apps" in your dashboard
4. Click "Create New App" or use an existing app
5. Copy your API Key (also called "Consumer Key")

### 2. Configure the Backend

Add your Ticketmaster API key to the backend environment variables:

```bash
# In apps/backend/.env
TICKETMASTER_API_KEY=your_api_key_here
```

### 3. Restart the Backend

The Ticketmaster provider will automatically initialize when the API key is present:

```bash
cd apps/backend
./start.sh
```

You should see log messages confirming the provider is initialized:
```
[SourcingRepository] TICKETMASTER_API_KEY present: True
[SourcingRepository] Ticketmaster provider initialized
```

## Usage

### Search Examples

The Ticketmaster provider will automatically be included in searches. It works best with queries containing:

- **Event names**: "Taylor Swift concert"
- **Team names**: "Lakers game"
- **Venue + event**: "Madison Square Garden events"
- **Sport + team**: "Notre Dame vs Clemson tickets"

### Result Format

Ticketmaster results will appear alongside other search results with:
- **Title**: Event name - Venue (Date & Time)
- **Price**: Minimum ticket price (if available)
- **Merchant**: "Ticketmaster"
- **Source**: `ticketmaster`
- **Shipping Info**: Event date/time

Example result:
```
Notre Dame vs Clemson - Notre Dame Stadium (2026-09-15 19:30)
Price: $85.00 USD
Merchant: Ticketmaster
```

## API Details

### Ticketmaster Discovery API

- **Endpoint**: `https://app.ticketmaster.com/discovery/v2/events.json`
- **Rate Limits**: Check your developer portal for specific limits
- **Coverage**: Events in the United States and internationally
- **Data Freshness**: Real-time event data

### Provider Configuration

The provider can be customized via environment variables:

```bash
# Timeout for Ticketmaster API calls (default: 8 seconds)
SOURCING_PROVIDER_TIMEOUT_SECONDS=8
```

### Filtering by Provider

To search only Ticketmaster (or exclude it), use the `providers` parameter in your search request:

```json
{
  "query": "concert tickets",
  "providers": ["ticketmaster"]
}
```

## Troubleshooting

### No Ticketmaster Results

1. **Check API Key**: Verify your API key is valid and active
2. **Check Logs**: Look for error messages in backend logs
3. **Try Specific Queries**: Use event names or team names rather than generic terms
4. **Rate Limits**: Ensure you haven't exceeded your API quota

### Common Log Messages

```
[TicketmasterProvider] Searching with query: 'concert tickets'
[TicketmasterProvider] Found 15 events
[TicketmasterProvider] HTTP error status=401: Unauthorized
```

## Model Context Protocol (MCP)

This integration follows the vision outlined in the product requirements for MCP Shopping Connectors. The Ticketmaster provider is structured to:

1. **Standardized Interface**: Implements the `SourcingProvider` abstract class
2. **Parallel Execution**: Runs alongside other providers with configurable timeouts
3. **Result Normalization**: Converts Ticketmaster event data to standard `SearchResult` format
4. **Error Handling**: Gracefully degrades when API is unavailable

## Future Enhancements

Potential improvements for the Ticketmaster integration:

- **Geographic Filtering**: Filter events by city or venue
- **Date Range**: Search for events within specific date ranges
- **Category Filtering**: Filter by event type (sports, concerts, theater, etc.)
- **Price Range**: Filter by minimum/maximum ticket prices
- **Venue Details**: Show seating charts and venue information
- **Multiple Tickets**: Support searching for specific seat sections or quantities

## References

- [Ticketmaster Discovery API Documentation](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/)
- [MCP Shopping Connectors PRD](/docs/prd/marketplace-pivot/parent.md#mcp-shopping-connectors)
- [Backend Sourcing Providers](/apps/backend/sourcing.py)
