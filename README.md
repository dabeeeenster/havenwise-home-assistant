# Havenwise Home Assistant Integration

A custom Home Assistant integration for [Havenwise](https://havenwise.co.uk/) heat pump control.

## Features

- **Climate entity** — heating control with current/target temperature, boost, and holiday mode presets
- **Water heater entity** — hot water temperature, boost, and away mode
- **Sensors** — COP (total, heating, DHW), energy consumed/produced, cost, effective tariff, room and DHW temperatures
- **Holiday mode switch** — toggle all heating and hot water off/on
- **Connection status** — binary sensor showing heat pump connectivity

## Installation via HACS

### Prerequisites

- [HACS](https://hacs.xyz/) installed in your Home Assistant instance

### Steps

1. In Home Assistant, go to **HACS** in the sidebar
2. Click the **three dots menu** (top right) and select **Custom repositories**
3. In the **Repository** field, paste the GitHub URL for this repo:
   ```
   https://github.com/dabeeeenster/havenwise-home-assistant
   ```
4. In the **Category** dropdown, select **Integration**
5. Click **Add**
6. The Havenwise integration will now appear in HACS — click on it and then click **Download**
7. **Restart Home Assistant** (Settings > System > Restart)
8. After restart, go to **Settings > Devices & Services**
9. Click **+ Add Integration** (bottom right)
10. Search for **Havenwise** and select it
11. Enter your Havenwise account email and password
12. All entities will appear under a single **Havenwise Heat Pump** device

### Updating

When a new version is available, HACS will show an update notification. Click **Update** and restart Home Assistant.

## Manual Installation

Copy the `custom_components/havenwise` directory into your Home Assistant `config/custom_components/` directory and restart.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Heating | Climate | Room temp, target temp, HEAT/OFF modes, boost/away presets |
| Hot Water | Water Heater | DHW temp, boost, away mode |
| Holiday Mode | Switch | Toggle all heating and DHW off |
| Connection | Binary Sensor | Heat pump connection status |
| Total COP | Sensor | Coefficient of performance (total) |
| Heating COP | Sensor | COP for space heating |
| Hot Water COP | Sensor | COP for domestic hot water |
| Energy Consumed Today | Sensor | Electricity consumed (kWh) |
| Heat Energy Produced Today | Sensor | Heat energy delivered (kWh) |
| Energy Cost Today | Sensor | Cost in GBP |
| Effective Tariff | Sensor | Effective rate in p/kWh |
| Room Temperature | Sensor | Current room temperature |
| Hot Water Temperature | Sensor | Current DHW cylinder temperature |
