# BE Alert Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

The **BE Alert** integration for Home Assistant allows you to monitor the official Belgian public alert system, [be-alert.be](https://be-alert.be). It fetches active alerts and creates sensors in Home Assistant so you can stay informed and create automations based on emergency situations.

## Features

- **All Alerts Sensor**: A global sensor (`sensor.be_alert_all_alerts`) that shows the total count of active alerts across Belgium. Its attributes contain a list of all current alerts.
- **Location-Based Monitoring**: Create sensors to monitor alerts for specific locations.
- **Multiple Location Sources**: Track alerts for:
  - **Persons**: `person` entities.
  - **Device Trackers**: `device_tracker` entities (with GPS).
  - **Zones**: `zone` entities (e.g., `zone.home`, `zone.work`).
- **Dual Sensors for Locations**: For each tracked location, the integration creates two entities:
  - A `sensor` (e.g., `sensor.be_alert_peter`) that counts how many active alerts affect that specific location.
  - A `binary_sensor` (e.g., `binary_sensor.be_alert_peter_alerting`) that turns `on` if there is one or more active alerts for the location.
- **Configurable Update Interval**: Set how often the integration should check for new alerts.
- **Manual Refresh**: Trigger an immediate update for all sensors using the `be_alert.update` service.

## Installation

### HACS (Recommended)

1.  Ensure you have HACS (Home Assistant Community Store) installed.
2.  In HACS, go to "Integrations".
3.  Click the three dots in the top right and select "Custom repositories".
4.  Add the URL to this repository (`https://github.com/spiffo/be_alert`) and select the "Integration" category.
5.  Find the "BE Alert" integration in the list and click "Install".
6.  Restart Home Assistant.

### Manual Installation

1.  Copy the `custom_components/be_alert` directory from this repository into your Home Assistant `config/custom_components/` directory.
2.  Restart Home Assistant.

## Configuration

Configuration is done entirely through the Home Assistant user interface.

1.  Go to **Settings > Devices & Services**.
2.  Click **Add Integration** and search for **BE Alert**.
3.  Follow the on-screen prompt to add the integration. This will set up the central hub but won't create any sensors yet.

### Managing Sensors and Settings

After the initial setup, all further management is done by clicking **Configure** on the BE Alert integration card.

This will open a menu with three options:

#### 1. Add a new sensor

This option starts a wizard to add a new alert sensor.

- **All Alerts Sensor**: You can add a single sensor that tracks all alerts in Belgium.
- **Location-Based Sensor**: Select a `person`, `device_tracker`, or `zone` entity to monitor. The integration will create a device in Home Assistant for this tracked location, containing a count sensor and a binary "alerting" sensor.

#### 2. Remove a sensor

This option shows a list of all your currently configured BE Alert sensors. Select one to remove it.

#### 3. Global Settings

Here you can configure the **Update interval** (in minutes) for how often the integration checks the BE Alert feed. The default is 5 minutes.

## Entities

### Global Sensor

- `sensor.be_alert_all_alerts`:
  - **State**: The total number of active alerts.
  - **Attributes**: `alerts` (a list of all alert details), `last_checked`.

### Location-Based Sensors

For a tracked entity named "Peter's Phone", the following are created:

- `sensor.be_alert_peters_phone`:
  - **State**: The number of alerts affecting the location of Peter's Phone.
  - **Attributes**: `source` (the entity ID being tracked), `alerts` (a list of relevant alert details).

- `binary_sensor.be_alert_peters_phone_alerting`:
  - **State**: `on` if the alert count is > 0, otherwise `off`.
  - **Attributes**: `source`.

## Service

You can manually trigger a refresh of the alert data by calling the `be_alert.update` service.

```yaml
# Example automation to refresh alerts every hour
trigger:
  - platform: time_pattern
    hours: "/1"
action:
  - service: be_alert.update
```

## Alert Categories

The integration monitors the BE Alert feed for alerts in the following categories:

- **Geo**: Geophysical (e.g., earthquake)
- **Met**: Meteorological (e.g., severe weather)
- **Safety**, **Security**, **Rescue**, **Fire**, **Health**
- **Env**: Environmental
- **Transport**, **Infra**: Infrastructure
- **CBRNE**: Chemical, Biological, Radiological, Nuclear, and Explosives
- **Other**