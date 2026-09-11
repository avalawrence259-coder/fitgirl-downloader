# 🧩 FFDL Browser Extension

1-Click Accelerated Download Integration with **FFDL-CLI** for FitGirl Repacks.

## 🚀 Features
- **Automatic Post Detection**: Detects game repacks on both individual game pages and the homepage/search index.
- **1-Click Download Buttons**: Injects sleek buttons for **FuckingFast**, **DataNodes**, **FileKeeper**, and **Torrent Magnets**.
- **Selective Audio Filtering**: Toggle to automatically skip foreign voiceovers and download core main game archives only.
- **Native CLI Integration**: Connects via native `ffdl://` protocol deep link (instant CLI launch) or optional background daemon (`http://127.0.0.1:45732`).
- **Context Menu**: Right-click any FitGirl or direct link to download directly with FFDL.

---

## 🛠️ Installation Guide

### Step 1: Register Windows Deep-Link Protocol
Run this once in your terminal to enable browser 1-click launch:
```powershell
ffdl --register-protocol
```

### Step 2: Load Extension in Browser (Chrome, Brave, Edge, Opera)
1. Open your browser and go to the extensions page:
   - **Chrome / Brave**: `chrome://extensions`
   - **Edge**: `edge://extensions`
2. Toggle on **"Developer mode"** (top right corner).
3. Click **"Load unpacked"**.
4. Select the `extension` folder inside this repository.
5. Done! You will see the **⚡ FFDL** lightning icon in your browser toolbar.

---

## 🎮 How It Works
1. Navigate to any game on **FitGirl Repacks** (e.g. `https://fitgirl-repacks.site/`).
2. You will see the **⚡ FFDL Action Bar** right beneath the game title or on post cards.
3. Click **[⚡ FuckingFast]** (or DataNodes / FileKeeper):
   - Your browser triggers the deep link.
   - FFDL CLI terminal opens immediately with high-speed multi-threaded chunks downloading to your disk!
