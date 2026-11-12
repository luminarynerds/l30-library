#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Quick manual test of reading lists endpoints using curl
# Assumes API is running on localhost:8000

BASE_URL="${API_URL:-http://localhost:8000}"
API_PREFIX="/api/v1/indie"

echo "=================================================="
echo "Indie Reading Lists API - Manual Test Script"
echo "=================================================="
echo "Base URL: $BASE_URL"
echo ""

# Note: For authenticated requests, you'll need to add a valid token
# TOKEN="your-jwt-token-here"
# AUTH_HEADER="-H \"Authorization: Bearer $TOKEN\""

echo "1. Get all public reading lists"
echo "GET $BASE_URL$API_PREFIX/reading-lists"
curl -s "$BASE_URL$API_PREFIX/reading-lists" | python3 -m json.tool | head -30
echo ""
echo "Press Enter to continue..."
read

echo "2. Get public reading lists (paginated)"
echo "GET $BASE_URL$API_PREFIX/reading-lists/public?page=1&per_page=5"
curl -s "$BASE_URL$API_PREFIX/reading-lists/public?page=1&per_page=5" | python3 -m json.tool
echo ""
echo "Press Enter to continue..."
read

echo "3. Get specific reading list details"
echo "GET $BASE_URL$API_PREFIX/reading-lists/1"
curl -s "$BASE_URL$API_PREFIX/reading-lists/1" | python3 -m json.tool
echo ""
echo "Press Enter to continue..."
read

echo "=================================================="
echo "Authenticated Requests (require valid token)"
echo "=================================================="
echo ""

# Uncomment and set TOKEN to test authenticated endpoints
: '
echo "4. Create a new reading list"
echo "POST $BASE_URL$API_PREFIX/reading-lists"
curl -X POST "$BASE_URL$API_PREFIX/reading-lists" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Test List",
    "description": "Created via curl",
    "is_public": true
  }' | python3 -m json.tool
echo ""

echo "5. Add book to reading list"
echo "POST $BASE_URL$API_PREFIX/reading-lists/1/items"
curl -X POST "$BASE_URL$API_PREFIX/reading-lists/1/items" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "ebook_id": 1,
    "notes": "Added via curl test",
    "display_order": 0
  }' | python3 -m json.tool
echo ""

echo "6. Get my reading lists"
echo "GET $BASE_URL$API_PREFIX/users/me/reading-lists"
curl -s "$BASE_URL$API_PREFIX/users/me/reading-lists" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "7. Update reading list"
echo "PATCH $BASE_URL$API_PREFIX/reading-lists/1"
curl -X PATCH "$BASE_URL$API_PREFIX/reading-lists/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Updated Title",
    "is_public": false
  }' | python3 -m json.tool
echo ""

echo "8. Check which lists contain a book"
echo "GET $BASE_URL$API_PREFIX/ebooks/1/in-lists"
curl -s "$BASE_URL$API_PREFIX/ebooks/1/in-lists" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "9. Remove book from list"
echo "DELETE $BASE_URL$API_PREFIX/reading-lists/1/items/1"
curl -X DELETE "$BASE_URL$API_PREFIX/reading-lists/1/items/1" \
  -H "Authorization: Bearer $TOKEN" \
  -v
echo ""

echo "10. Delete reading list"
echo "DELETE $BASE_URL$API_PREFIX/reading-lists/1"
curl -X DELETE "$BASE_URL$API_PREFIX/reading-lists/1" \
  -H "Authorization: Bearer $TOKEN" \
  -v
echo ""
'

echo "=================================================="
echo "Test Complete!"
echo "=================================================="
echo ""
echo "To test authenticated endpoints:"
echo "1. Login to get a JWT token"
echo "2. Set TOKEN variable in this script"
echo "3. Uncomment the authenticated test section"
echo ""
