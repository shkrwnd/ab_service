#!/bin/bash

# Example usage script for A/B Testing API
# Make sure the API is running on http://localhost:8000

API_URL="http://localhost:8000"
TOKEN="default-dev-token"  # Change this to your actual token

echo "=== A/B Testing API Example Usage ==="
echo ""

# 1. Create an experiment
echo "1. Creating an experiment..."
EXPERIMENT_RESPONSE=$(curl -s -X POST "${API_URL}/experiments" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Button Color Test",
    "description": "Testing red vs blue button colors",
    "variants": [
      {"name": "control", "traffic_percentage": 50.0},
      {"name": "variant_b", "traffic_percentage": 50.0}
    ]
  }')

echo "$EXPERIMENT_RESPONSE" | python3 -m json.tool
EXPERIMENT_ID=$(echo "$EXPERIMENT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Experiment ID: $EXPERIMENT_ID"
echo ""

# 2. Get user assignment (first call - creates assignment)
echo "2. Getting assignment for user_123 (first call)..."
ASSIGNMENT1=$(curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}/assignment/user_123" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$ASSIGNMENT1" | python3 -m json.tool
VARIANT_NAME1=$(echo "$ASSIGNMENT1" | python3 -c "import sys, json; print(json.load(sys.stdin)['variant_name'])")
echo "Assigned to: $VARIANT_NAME1"
echo ""

# 3. Get user assignment again (should be idempotent - same result)
echo "3. Getting assignment for user_123 again (demonstrating idempotency)..."
ASSIGNMENT2=$(curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}/assignment/user_123" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$ASSIGNMENT2" | python3 -m json.tool
VARIANT_NAME2=$(echo "$ASSIGNMENT2" | python3 -c "import sys, json; print(json.load(sys.stdin)['variant_name'])")
echo "Assigned to: $VARIANT_NAME2"
echo ""

if [ "$VARIANT_NAME1" == "$VARIANT_NAME2" ]; then
  echo "✓ Idempotency confirmed: Same variant assigned both times"
else
  echo "✗ Idempotency failed: Different variants assigned"
fi
echo ""

# 4. Get assignment for different user
echo "4. Getting assignment for user_456..."
ASSIGNMENT3=$(curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}/assignment/user_456" \
  -H "Authorization: Bearer ${TOKEN}")

echo "$ASSIGNMENT3" | python3 -m json.tool
echo ""

# 5. Record events
echo "5. Recording events..."

# Get assignment time for user_123
ASSIGNED_AT=$(echo "$ASSIGNMENT1" | python3 -c "import sys, json; print(json.load(sys.stdin)['assigned_at'])")
echo "User_123 was assigned at: $ASSIGNED_AT"

# Record a click event
echo "Recording click event for user_123..."
curl -s -X POST "${API_URL}/events" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user_123\",
    \"type\": \"click\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\",
    \"properties\": {
      \"button\": \"signup\",
      \"page\": \"home\"
    },
    \"experiment_id\": ${EXPERIMENT_ID}
  }" | python3 -m json.tool
echo ""

# Record a purchase event
echo "Recording purchase event for user_123..."
curl -s -X POST "${API_URL}/events" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user_123\",
    \"type\": \"purchase\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\",
    \"properties\": {
      \"amount\": 29.99,
      \"product\": \"widget\"
    },
    \"experiment_id\": ${EXPERIMENT_ID}
  }" | python3 -m json.tool
echo ""

# Record events for user_456
echo "Recording events for user_456..."
curl -s -X POST "${API_URL}/events" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user_456\",
    \"type\": \"click\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\",
    \"experiment_id\": ${EXPERIMENT_ID}
  }" | python3 -m json.tool
echo ""

# 6. Batch event creation
echo "6. Recording batch events..."
curl -s -X POST "${API_URL}/events" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "[
    {
      \"user_id\": \"user_789\",
      \"type\": \"click\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\",
      \"experiment_id\": ${EXPERIMENT_ID}
    },
    {
      \"user_id\": \"user_789\",
      \"type\": \"purchase\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S)\",
      \"experiment_id\": ${EXPERIMENT_ID}
    }
  ]" | python3 -m json.tool
echo ""

# 7. Get experiment results
echo "7. Getting experiment results..."
curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}/results" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
echo ""

# 8. Get results with filters
echo "8. Getting results filtered by event type..."
curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}/results?event_type=purchase" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
echo ""

# 9. Test authentication (should fail)
echo "9. Testing authentication (invalid token - should fail)..."
curl -s -X GET "${API_URL}/experiments/${EXPERIMENT_ID}" \
  -H "Authorization: Bearer invalid-token" | python3 -m json.tool
echo ""

echo "=== Example usage complete ==="

