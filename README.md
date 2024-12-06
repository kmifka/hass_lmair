# Light Manager Air Integration

A Home Assistant custom integration for the Light Manager Air by jb media.

## Key Features

- **Automatic device discovery** on your local network
- Full control of:
  - **Lights** (including dimming)
  - **Blinds/Covers**
  - **Markers**
  - **Scenes**
- **Reception of 433 MHz and 868 MHz radio signals**
- Real-time **marker status updates**, with the ability to **set marker states**
- Integration of **weather data** from connected weather stations
- Automatic mapping of zones to **Home Assistant areas**
- Marker mapping to use markers as state proxies for stateless devices.

This integration bridges jb media's Light Manager Air with Home Assistant, unlocking advanced home automation capabilities.

---

## Installation

### Option 1: Manual Installation

1. Copy the `light_manager_air` folder to the `custom_components` directory in your Home Assistant configuration folder.
2. Restart Home Assistant.
3. Add the integration via the UI:
   Go to **Settings** → **Devices & Services** → **Add Integration** and search for "Light Manager Air".

### Option 2: Installation via HACS (Home Assistant Community Store)

1. **Ensure HACS is Installed**
   If you don’t have HACS installed, follow the [HACS installation guide](https://hacs.xyz/docs/use/).

2. **Add the Custom Repository**
   - Open Home Assistant and navigate to **HACS** → **Integrations**.
   - Click the **three dots menu** in the top-right corner and select **Custom repositories**.
   - Add the following repository URL:
     ```
     https://github.com/kmifka/hass_lmair
     ```
   - Select **Integration** as the category.
   - Click **Add**.

3. **Install the Integration**
   - Search for "Light Manager Air" in the HACS integrations list.
   - Click **Install** to download and install the integration.

4. **Restart Home Assistant**
   Restart Home Assistant to apply changes.

5. **Add the Integration in Home Assistant**
   Go to **Settings** → **Devices & Services** → **Add Integration** and follow the setup instructions.

---

## Configuration

### Polling Settings

The Light Manager Air relies on polling for updates because it does not support event-based communication. This integration allows you to adjust the polling intervals for:

1. **Marker Updates**: Updates the status of markers (Default: `5000 ms`).
2. **Radio Signals**: Checks for 433 MHz and 868 MHz signals (Default: `2000 ms`).

You can customize these intervals to suit your needs or disable polling entirely if not required:

1. Navigate to **Settings** → **Devices & Services**.
2. Locate the Light Manager Air integration and click **Options**.
3. Set your desired intervals or disable polling by setting the interval to `0`.

⚠️ **Warning**: Short intervals improve response times but may impact performance. Use default settings as a starting point and adjust based on your system's capabilities.

---

### Marker Mapping (Optional Feature)

Markers can be used to reflect and **set the states** of stateless actuators (e.g., lights, blinds) via the Light Manager Air. This is especially useful for:

- Providing feedback for automations
- Status visualization within the Light Manager
- Triggering and managing scenes

To configure marker mappings, add the following to your `configuration.yaml` file:

```yaml
light_manager_air:
  marker_mappings:
    - marker_id: 12
      entity_id: "light.garden_lights"
    - marker_id: 15
      entity_id: "cover.bedroom_blinds"
    - marker_id: 22
      entity_id: "light.dining_room"
    - marker_id: 30
      entity_id: "light.fountain_pump"