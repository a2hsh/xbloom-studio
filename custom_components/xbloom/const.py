"""Constants for the xBloom Studio integration.

BLE-only by default; an optional cloud layer (recipe sync + firmware check)
activates once the user logs in with an xBloom account.
"""

DOMAIN = "xbloom"

# Config entry data keys — machine (BLE)
CONF_PRODUCT_ID = "product_id"  # serial number tail (e.g. "ABC123")
CONF_BLE_NAME = "ble_name"      # advertised BLE name (e.g. "XBLOOM ABC123")

# Config entry data keys — optional cloud account. Stored under a single
# `cloud` sub-dict in entry.data so a logged-out entry has no cloud key at all.
CONF_CLOUD = "cloud"
CONF_CLOUD_EMAIL = "email"         # account email (also used for re-login)
CONF_CLOUD_PASSWORD = "password"   # stored ONLY if the user opts in (remember)
CONF_CLOUD_MEMBER_ID = "member_id"  # member.tableId from the login response
CONF_CLOUD_TOKEN = "token"          # session token for the recipe API
CONF_CLOUD_REMEMBER = "remember"    # whether the password is stored for auto-refresh

