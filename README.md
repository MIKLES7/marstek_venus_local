<p align="center">
  <img src="assets/marstek_logo.png" alt="Marstek" width="240">
</p>

<h1 align="center">Marstek Venus Local (UDP)</h1>

<p align="center">
  Local Home Assistant integration for <strong>Marstek Venus</strong> devices using the local UDP API.<br>
  No cloud, no polling limits, fast local control.
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=MIKLES7&repository=marstek_venus_local&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open this repository in HACS">
  </a>
</p>

---

## ✨ Features

- 🔌 **Local-only** communication via UDP
- 🚀 Fast updates without cloud dependency
- 🏠 Native Home Assistant integration
- 🔧 Config Flow (UI-based setup)
- 📡 Sensor entities for device data

---

## 📦 Installation (via HACS – recommended)

1. Make sure **HACS** is installed
2. Go to **HACS → Integrations**
3. Open the menu (⋮) → **Custom repositories**
4. Add this repository:
https://github.com/MIKLES7/marstek_venus_local
Category: **Integration**
5. Install **Marstek Venus Local (UDP)**
6. Restart Home Assistant
7. Go to **Settings → Devices & Services → Add Integration**
8. Select **Marstek Venus Local (UDP)**

---

## ⚙️ Configuration

The integration is configured via the Home Assistant UI.

During setup you will be asked for:
- Device IP address
- (Optional) additional connection parameters depending on device firmware

---

## 🧩 Entities

The integration creates sensor entities based on the data provided by the Marstek Venus local API, for example:
- Power
- Energy
- Device status
- Additional telemetry (depending on firmware)

---

## 📚 Documentation / API Reference

Marstek official API documentation:  
https://static-eu.marstekenergy.com/ems/resource/agreement/MarstekDeviceOpenApi.pdf

---

## 🛠️ Development & Updates

- Domain: `marstek_venus_local`
- Updates are delivered via **HACS**
- Versioning is handled via GitHub releases

---

## 🐞 Issues & Feature Requests

If you find a bug or have an idea for an improvement, please open an issue on GitHub:

👉 https://github.com/MIKLES7/marstek_venus_local/issues

---

## 📄 License

MIT License
