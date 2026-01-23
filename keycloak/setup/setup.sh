#!/bin/sh
set -e

# --- Configuration ---
KC_HEALTH_URL="${KC_HEALTH_URL:-http://keycloak:9000}"
KC_URL="${KC_URL:-http://keycloak:8080}"

# Validate required variables
if [ -z "$BOOTSTRAP_USER" ]; then echo "BOOTSTRAP_USER is not set"; exit 1; fi
if [ -z "$BOOTSTRAP_PASS" ]; then echo "BOOTSTRAP_PASS is not set"; exit 1; fi
if [ -z "$BACKEND_CLIENT_ID" ]; then echo "BACKEND_CLIENT_ID is not set"; exit 1; fi
if [ -z "$BACKEND_CLIENT_SECRET" ]; then echo "BACKEND_CLIENT_SECRET is not set"; exit 1; fi

# Helper: Check for errors in JSON response
check_response() {
    RESP=$1
    CONTEXT=$2
    if [ -z "$RESP" ]; then echo "Error: Empty response for $CONTEXT"; exit 1; fi
    if echo "$RESP" | grep -q '"error"'; then echo "Error in response for $CONTEXT: $RESP"; exit 1; fi
}

echo "--- Keycloak Setup Script ---"

echo "1. Waiting for Keycloak Health ($KC_HEALTH_URL)..."
until curl -s -f "$KC_HEALTH_URL/health/ready" > /dev/null; do
    echo "   Keycloak not ready, retrying..."
    sleep 3
done

echo "2. Authenticating as Bootstrap Admin..."
TOKEN_RESP=$(curl -s -H "X-Forwarded-Proto: https" -d "client_id=admin-cli" -d "username=$BOOTSTRAP_USER" -d "password=$BOOTSTRAP_PASS" -d "grant_type=password" "$KC_URL/realms/master/protocol/openid-connect/token")
check_response "$TOKEN_RESP" "Authentication"
TOKEN=$(echo "$TOKEN_RESP" | jq -r .access_token)

if [ "$TOKEN" = "null" ]; then echo "Error: Failed to obtain access token."; exit 1; fi

kcurl() {
    METHOD=$1
    URL=$2
    shift 2
    curl -s -X "$METHOD" -H "X-Forwarded-Proto: https" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$@" "$URL"
}

echo "2.5. Disabling SSL Requirement for Master and App Realms..."
kcurl PUT "$KC_URL/admin/realms/master" -d '{"sslRequired": "none"}'
kcurl PUT "$KC_URL/admin/realms/$REALM" -d '{"sslRequired": "none"}'

# --- Service Account Setup ---

echo "3. Configuring Backend Client ($BACKEND_CLIENT_ID)..."
CLIENTS_RESP=$(kcurl GET "$KC_URL/admin/realms/$REALM/clients?clientId=$BACKEND_CLIENT_ID")
check_response "$CLIENTS_RESP" "Get Backend Client"
EXISTING_ID=$(echo "$CLIENTS_RESP" | jq -r '.[0].id')

# Enable directAccessGrantsEnabled so this client can be used for user login via backend
CLIENT_PAYLOAD="{\"clientId\": \"$BACKEND_CLIENT_ID\", \"secret\": \"$BACKEND_CLIENT_SECRET\", \"serviceAccountsEnabled\": true, \"standardFlowEnabled\": false, \"directAccessGrantsEnabled\": true, \"publicClient\": false, \"enabled\": true}"

if [ "$EXISTING_ID" = "null" ]; then
    echo "   Creating new client..."
    kcurl POST "$KC_URL/admin/realms/$REALM/clients" -d "$CLIENT_PAYLOAD"
    CID_UUID=$(kcurl GET "$KC_URL/admin/realms/$REALM/clients?clientId=$BACKEND_CLIENT_ID" | jq -r '.[0].id')
else
    echo "   Updating existing client..."
    kcurl PUT "$KC_URL/admin/realms/$REALM/clients/$EXISTING_ID" -d "$CLIENT_PAYLOAD"
    CID_UUID=$EXISTING_ID
fi

echo "4. Assigning 'manage-users' role to Service Account..."
SA_USER_ID=$(kcurl GET "$KC_URL/admin/realms/$REALM/clients/$CID_UUID/service-account-user" | jq -r .id)

# Fetch 'realm-management' client ID in pixel-canvas realm
CLIENTS_LIST=$(kcurl GET "$KC_URL/admin/realms/$REALM/clients?first=0&max=200")
MGMT_CID=$(echo "$CLIENTS_LIST" | jq -r '.[] | select(.clientId=="realm-management") | .id')

if [ -z "$MGMT_CID" ] || [ "$MGMT_CID" = "null" ]; then
    echo "Error: Could not find realm-management client in $REALM"
    exit 1
fi

ROLE_INFO=$(kcurl GET "$KC_URL/admin/realms/$REALM/clients/$MGMT_CID/roles/manage-users")
check_response "$ROLE_INFO" "Get manage-users role"

kcurl POST "$KC_URL/admin/realms/$REALM/users/$SA_USER_ID/role-mappings/clients/$MGMT_CID" -d "[$ROLE_INFO]"

# --- Permanent Human Admin Setup ---

if [ -n "$PERM_ADMIN_USER" ]; then
    echo "5. Configuring Permanent Admin ($PERM_ADMIN_USER)..."
    USERS_RESP=$(kcurl GET "$KC_URL/admin/realms/master/users?username=$PERM_ADMIN_USER")
    USER_ID=$(echo "$USERS_RESP" | jq -r '.[0].id')

    if [ "$USER_ID" = "null" ]; then
        echo "   Creating user..."
        kcurl POST "$KC_URL/admin/realms/master/users" -d "{\"username\": \"$PERM_ADMIN_USER\", \"enabled\": true}"
        USERS_RESP=$(kcurl GET "$KC_URL/admin/realms/master/users?username=$PERM_ADMIN_USER")
        USER_ID=$(echo "$USERS_RESP" | jq -r '.[0].id')
        
        echo "   Setting password..."
        kcurl PUT "$KC_URL/admin/realms/master/users/$USER_ID/reset-password" -d "{\"type\": \"password\", \"value\": \"$PERM_ADMIN_PASS\", \"temporary\": false}"
        
        echo "   Granting 'admin' Realm Role..."
        
        ADMIN_ROLE_INFO=$(kcurl GET "$KC_URL/admin/realms/master/roles/admin")
        check_response "$ADMIN_ROLE_INFO" "Get admin realm role"
        
        kcurl POST "$KC_URL/admin/realms/master/users/$USER_ID/role-mappings/realm" -d "[$ADMIN_ROLE_INFO]"
        
    else
        echo "   User already exists, skipping."
    fi
fi

echo "--- Setup Complete! ---"
