<div align="center">

```text
███████╗███████╗██████╗ ██╗     
██╔════╝██╔════╝██╔══██╗██║     
█████╗  █████╗  ██║  ██║██║     
██╔══╝  ██╔══╝  ██║  ██║██║     
██║     ██║     ██████╔╝███████╗
╚═╝     ╚═╝     ╚═════╝ ╚══════╝
```

# ⚡ FitGirl Downloader & Accelerator (`fitgirl-downloader`)
### Ultra-High-Speed Multi-Threaded Download Accelerator & Browser Companion for FitGirl Repacks

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

</div>

---

## 🌟 Why FitGirl Downloader?

- 🆓 **Zero API Keys & Zero Credentials Required:** Runs 100% locally on your machine with zero configuration. No accounts, no subscriptions.
- ⚡ **16–32 Parallel TCP Worker Streams:** Squeezes maximum ISP bandwidth with chunk pre-allocation and active anti-stall watchdogs.
- 🌐 **1-Click Browser Companion Extension:** Injects dedicated download buttons (`DataNodes`, `FuckingFast`, `FileKeeper`, `Torrent Magnet`) directly into `fitgirl-repacks.site`.
- 🤖 **System Downloader Auto-Detection:** Automatically detects installed download managers (**IDM**, **FDM**, **Aria2**, or built-in engine).
- 🤫 **Silent IDM Background Queueing:** Sends parted archives into Internet Download Manager's scheduler silently with zero focus-stealing or popup dialogs.
- 📦 **Automated Multi-Part Downloading:** Sequentially queues and downloads `part01.rar` through `partXX.rar` automatically with zero manual clicking.
- 🎯 **Release Isolation:** Accurately isolates primary cracked editions from older/hypervisor versions without mixing archive sets.
- 🗂️ **Selective Component Filtering:** Easily skip multi-gigabyte optional voiceovers and bonus files or download core game + English audio with a single keypress.
- 🛡️ **Stealth Interstitial Solvers:** Local headless solver bypasses Cloudflare Turnstile, DataNodes ad loops, and FileKeeper countdowns.
- 🧠 **Instant Smart Memory Skip:** Verifies file size and segment integrity on disk in **0.01 seconds** to avoid redownloading completed files.

---

## 📋 Prerequisites

1. **Python 3.9 or newer:**
   - Download from [python.org](https://www.python.org/downloads/).
   - ⚠️ **Windows Users:** Check the box **"Add python.exe to PATH"** during installation.
2. **Google Chrome, Brave, Edge, or Chromium:**
   - Used by the local headless solver to bypass Turnstile verification in ~3 seconds.

---

## 📦 Installation

### Option 1: Quick Install (from Source)

```bash
# 1. Clone the repository
git clone https://github.com/avalawrence259-coder/fitgirl-downloader.git
cd fitgirl-downloader

# 2. Install dependencies & CLI in editable mode
pip install -r requirements.txt
pip install -e .

# 3. Install headless browser binaries for Turnstile / Host solvers
playwright install chromium
```

### Option 2: 1-Click Windows Batch Installer
Double-click `install.bat` inside the repository folder. It automatically verifies Python, installs dependencies, and prepares the CLI.

---

## 🌐 Browser Extension Companion (1-Click Downloads)

Turn any FitGirl page into an instant 1-click download hub:

### Step 1: Register the Protocol Handler
Open terminal and run this once (no administrator rights needed):
```powershell
ffdl --register-protocol
```
*This connects your browser's `ffdl://` clicks directly to the CLI.*

### Step 2: Load the Extension into Your Browser
1. Open your browser extension management page:
   - **Chrome / Brave**: `chrome://extensions`
   - **Edge**: `edge://extensions`
2. Toggle on **"Developer mode"** (top right corner).
3. Click **"Load unpacked"**.
4. Select the `extension` folder inside this repository.
5. Done! The **⚡ FFDL** icon will appear in your toolbar.

### Step 3: Download with 1 Click
Visit any game on `fitgirl-repacks.site`. You will see dedicated buttons right on the page:
- `[⚡ DOWNLOAD DATANODES]`
- `[⚡ DOWNLOAD FUCKINGFAST]`
- `[⚡ DOWNLOAD FILEKEEPER]`
- `[🧲 DOWNLOAD MAGNET]`

Click any button to open the CLI and begin downloading immediately!

---

## 🤖 Downloader Auto-Detection (IDM, FDM, Aria2, FFDL)

When you launch a download, the CLI automatically scans your Windows Registry and Program Files for external download managers and displays an interactive engine picker:

```text
╭─────────────────────── DETECTED DOWNLOAD ENGINES ────────────────────────╮
│ [1] FFDL Built-in Accelerator (Recommended) [Default]                   │
│ [2] Internet Download Manager (IDM) [Silent Background Queue]            │
│ [3] Free Download Manager (FDM)                                          │
╰──────────────────────────────────────────────────────────────────────────╯
Choose engine [1/2/3] (1):
```

- **Option 1 (FFDL Built-in):** Ultra-fast multi-threaded chunk accelerator with active socket watchdog and dynamic token refreshing.
- **Option 2 (IDM):** Resolves all parted archives and silently injects each file into IDM's queue (`IDMan.exe /d ... /p ... /f ... /n /a`) and starts the queue (`IDMan.exe /s`) in the background with zero popup dialogs.

You can also bypass the menu by passing `--idm`, `--fdm`, `--aria2`, or `--downloader ffdl` via command line.

---

## 🗂️ Selective Component Filtering

FitGirl repacks often include dozens of gigabytes of optional language voiceovers (`fg-selective-french.bin`, `fg-selective-brazilian.bin`) and bonus media. The CLI automatically separates essential archives from optional addons:

```text
╭──────────────────────── CHOOSE DOWNLOAD PACKAGE ─────────────────────────╮
│ [1] ⚡ Auto-Download All Main Game Parts (Automated sequential download) │
│ [E] 🌟 Auto-Download Main Parts + English Voiceover                      │
│ [2] 📦 Auto-Download Complete Package (All main parts + all optionals)   │
│ [3] 🎯 Custom Selection (Pick specific optionals by number or keyword)   │
│ [4] 📋 Manual Part-by-Part Range Picker (e.g. 1-9 or 1-5, 8)             │
╰──────────────────────────────────────────────────────────────────────────╯
Choose an option [1/2/3/4/E] (1):
```

- Pass `--main-only` to automatically download core game parts and skip all optionals.
- Pass `--all` to download everything.
- Pass `--select "french,ost"` to script custom component downloads.

---

## ☁️ Optional Cloud Scraper APIs (For Headless VPS or Strict ISPs)

> [!NOTE]
> **No API keys are required for standard desktop use!**
> Cloud scraper failover is strictly optional, designed for headless cloud servers without GUI/Chromium or networks with strict ISP geoblocking.

A template file [`.env.example`](./.env.example) is included in the root directory:

```bash
# Copy template to active environment file
cp .env.example .env
```

Supported cloud providers (all offer free tiers):
| Provider | Free Monthly Tier | Environment Variable | Registration |
| :--- | :---: | :--- | :--- |
| **Firecrawl** | 500 scrapes / mo | `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) |
| **Scrapfly** | 1,000 requests / mo | `SCRAPFLY_API_KEY` | [scrapfly.io](https://scrapfly.io) |
| **ZenRows** | 1,000 requests / mo | `ZENROWS_API_KEY` | [zenrows.com](https://zenrows.com) |
| **ScraperAPI** | 5,000 requests / mo | `SCRAPERAPI_KEY` | [scraperapi.com](https://scraperapi.com) |

---

## 📁 Download Locations & Configuration

By default, files are saved to your standard user Downloads directory:
```text
C:\Users\<Username>\Downloads
```

### Changing the Destination:
- **One-time download flag:**
  ```powershell
  ffdl <url> -o "D:\Games"
  ```
- **Permanent default setting:**
  Edit your configuration file at `~/.ffdl_config.json`:
  ```json
  {
    "output_dir": "D:\\Games",
    "concurrency": 16,
    "chunk_kb": 256
  }
  ```

---

## 🛠️ CLI Options Reference

```text
Usage: ffdl [OPTIONS] [URLS]...

Options:
  -i, --interactive            Launch interactive CLI wizard dashboard
  -f, --file PATH              File containing URLs or raw HTML snippet
  -p, --paste TEXT             Raw HTML snippet or pasted text containing links
  -o, --output TEXT            Destination directory for downloads (default: ~/Downloads)
  -c, --concurrency INTEGER    Number of parallel worker streams (default: 16)
  --chunk-kb INTEGER           Buffer chunk size in KB (default: 256)
  -w, --overwrite              Force re-download and overwrite existing files
  --main-only                  Download core game parts only, skipping optional files
  --all, --all-parts           Download all parts including all optional addons
  --select TEXT                Comma-separated indices or names of optionals to include
  --hoster TEXT                Force hoster preference (fuckingfast, datanodes, filekeeper)
  --idm                        Dispatch directly to Internet Download Manager
  --fdm                        Dispatch directly to Free Download Manager
  --aria2                      Dispatch directly to Aria2
  --downloader TEXT            Select download engine (ffdl, idm, fdm, aria2)
  --register-protocol          Register ffdl:// deep link in Windows Registry
  --unregister-protocol        Unregister ffdl:// deep link from Windows Registry
  --speedtest                  Run internet speed test and calibrate concurrency
  --info                       Probe file size and metadata without downloading
  --links-only                 Resolve and print direct CDN download URLs only
  -h, --help                   Show help message and exit
```

---

## 🧪 Testing & Verification

The project includes a full unit, integration, and simulation test suite:
```bash
pytest tests/ -v
```
- **51 / 51 tests passing (100% coverage)**
- Native messaging IPC framing, bearer authentication, multi-release isolation, downloader detection, and segment resumption verification.

---

## 🔧 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **`playwright` browser missing** | Run `playwright install chromium` in your terminal. |
| **Browser button doesn't open CLI** | Run `ffdl --register-protocol` in your terminal once. |
| **Console window closes immediately** | The protocol handler uses space-free 8.3 paths and exception barriers to keep the window open for review. |
| **File already exists on disk** | FFDL Smart Memory verifies file integrity and skips it in 0.01s. Use `-w` to force redownload. |

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.
