# BE-Alert Integration for Home Assistant

This custom integration provides **real-time BE-Alert notifications** for Belgium. Alerts include emergencies such as fire, weather, pollution, and public safety. The integration allows you to create sensors for all of Belgium or for specific zones and devices in Home Assistant.

![BE-Alert logo](https://raw.githubusercontent.com/Spiffo/be-alert/main/custom_components/be_alert/logo.png)

---

## Features
- Retrieves official BE-Alert warnings for all of Belgium.
- Creates a central "hub" device for the integration.
- Creates separate devices for each tracked `zone` or `device_tracker`, linked to the hub.
- Provides a sensor for all alerts nationwide (`sensor.be_alert_all`).
- For each tracked location, it creates:
  - A sensor showing the *count* of active alerts (e.g., `sensor.be_alert_home`).
  - A binary sensor that is `on` if there is an active alert (e.g., `binary_sensor.be_alert_home_alerting`), perfect for automations.
- Configurable polling interval.
- Manual update service (`be_alert.update`) to force a refresh.

---

## Installation

### HACS (recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. In HACS, go to **Integrations**.
3. Click the three dots in the top right and select **Custom repositories**.
4. In the dialog, enter the following:
   - **Repository:** `https://github.com/Spiffo/be-alert`
   - **Category:** `Integration`
5. Click **Add**, then find the "BE-Alert" card and click **Install**.
6. Restart Home Assistant.

### Manual
1. Copy the `be_alert` folder from `custom_components` into your own `custom_components` directory.
2. Restart Home Assistant.

---

## Entities

This integration uses a hub-and-spoke model to organize its devices and entities.

### Main Hub Device
A central "BE Alert" device is created to represent the integration itself.

#### "All Alerts" Sensor (`sensor.be_alert_all`)
This sensor is attached to the main hub device and shows the total number of active alerts across all of Belgium.
- **State**: Count of current active alerts.
- **Attributes**: A list of all active alerts with details like title, description, category, etc.

### Location-based Devices
For each `zone` or `device_tracker` you choose to monitor, a new device is created (e.g., a device for `zone.home`). This device is linked to the main hub and contains the following entities:

#### Location Alert Count Sensor (e.g., `sensor.be_alert_home`)
Shows the number of active alerts affecting this specific location.
- **State**: Count of alerts affecting the location.
- **Attributes**: A list of alerts specific to this location.

#### Location Alerting Binary Sensor (e.g., `binary_sensor.be_alert_home_alerting`)
A boolean sensor that indicates if there is an active alert for the location. This is the recommended entity to use for automations.
- **State**: `on` if one or more alerts are active for the location; `off` otherwise.

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

## Example Automations

### 1. Send a notification for any new alert in Belgium
This automation sends a notification to your phone whenever a new alert is published anywhere in the country.

```yaml
alias: "BE-Alert: Notify on any new alert"
trigger:
  - platform: numeric_state
    entity_id: sensor.be_alert_all
    above: 0
action:
  - service: notify.mobile_app_your_phone # Change to your notification service
    data:
      title: "🚨 BE-Alert"
      message: "{{ state_attr('sensor.be_alert_all', 'alerts')[0].title }}"
```

### 2. Announce an alert for your Home zone
This automation triggers when an alert becomes active for your `zone.home`. It flashes a light and makes an announcement on a Google Home speaker.

```yaml
alias: "BE-Alert: Announce alert for Home"
trigger:
  - platform: state
    entity_id: binary_sensor.be_alert_home_alerting # Assumes you have a sensor for zone.home
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
    data:
      flash: long
  - service: tts.google_translate_say
    target:
      entity_id: media_player.google_home_speaker
    data:
      message: "Attention, an important BE-Alert message is active for our area."
```
