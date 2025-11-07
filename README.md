# BE-Alert Integration for Home Assistant

This custom integration provides **real-time BE-Alert notifications** for Belgium. Alerts include emergencies such as fire, weather, pollution, and public safety. The integration allows you to create sensors for all of Belgium or for specific zones and devices in Home Assistant.

![BE-Alert logo](https://raw.githubusercontent.com/be-alert/be-alert/main/logo_be-alert.webp)

---

## Features
- Retrieves official BE-Alert warnings for all of Belgium.
- Create sensors to monitor all alerts, or only alerts affecting a specific zone or device tracker.
- Configurable polling interval.
- Manual update service (`be_alert.update`) to force a refresh.
- Works with automations (notify, flash lights, TTS, etc.).

---

## Installation

### HACS (recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. In HACS, go to **Integrations** → **Custom repositories**  
3. Add this repository URL: `https://github.com/Spiffo/be-alert` with category `Integration`.
4. Install, then restart Home Assistant  

### Manual
1. Copy the `be_alert` folder from `custom_components` into your own `custom_components` directory.
2. Restart Home Assistant.

---

## Entities

This integration can create two types of sensors.

### "All Alerts" Sensor (`sensor.be_alert_all`)
Shows the total number of active alerts across all of Belgium.
- **State**: Count of current active alerts.
- **Attributes**:
- `alerts`: A list of all active alerts, each with details like title, description, category, etc.
- `last_checked`: The timestamp of the last successful data fetch.

### Location-based Sensor (e.g., `sensor.be_alert_home`)
Shows the number of active alerts affecting a specific location (from a `zone` or `device_tracker`).
- **State**: Count of alerts affecting the location.
- **Attributes**:
- `alerts`: A list of alerts affecting this specific location.
- `source`: The entity ID of the zone or device being tracked.

---

## Configuration
1. Go to **Settings → Devices & Services → Add Integration** and search for **BE-Alert**.
2. Follow the on-screen instructions to add the central integration hub.
3. Once added, click **Configure** on the BE-Alert integration card.
4. From the menu, you can:
    - **Add a new sensor**: Choose between "All Alerts", "Zone-based", or "Device-based".
    - **Remove a sensor**: Select a previously created sensor to remove it.
    - **Global Settings**: Adjust the polling interval (in minutes).

---

## Services

### `be_alert.update`
Forces an immediate update of the BE-Alert feed data for all sensors.

---

## Example Automation
```yaml
alias: BE-Alert notification
trigger:
  - platform: numeric_state
    entity_id: sensor.be_alert_all
    above: 0
action:
  - service: notify.your_notification_service # e.g., notify.mobile_app_your_phone
    data:
      message: "🚨 BE-Alert active: {{ state_attr('sensor.be_alert_all','alerts')[0].title }}"
