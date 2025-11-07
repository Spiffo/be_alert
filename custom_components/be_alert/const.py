# const.py
DOMAIN = "be_alert"
CONF_LOCATION_TEXT = "Track Alert at this location:"

# Internal keys for config flow
LOCATION_SOURCE_DEVICE = "device"
LOCATION_SOURCE_ZONE = "zone"

DEFAULT_SCAN_INTERVAL = 5 # Default polling interval in minutes

FEED_URL = (
    "https://publicalerts.be/CapGateway/feed?"
    "capCategory=Geo,Met,Safety,Security,Rescue,Fire,Health,Env,Transport,Infra,CBRNE,Other&outdated=false"
)