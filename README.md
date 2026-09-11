<div align="center">

```text
███████╗███████╗██████╗ ██╗     
██╔════╝██╔════╝██╔══██╗██║     
█████╗  █████╗  ██║  ██║██║     
██╔══╝  ██╔══╝  ██║  ██║██║     
██║     ██║     ██████╔╝███████╗
╚═╝     ╚═╝     ╚═════╝ ╚══════╝
```

# ⚡ FF-Downloader (`ffdl`)
### The Ultra-High-Speed Parallel Multi-Part Downloader with Smart Memory & Anti-Stall Engine

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

</div>

---

## 🚀 Overview

**`ffdl`** is a high-performance CLI download accelerator built specifically for downloading multi-part archives, game repacks, and direct filehost streams (`fuckingfast.co`, `paste.fitgirl-repacks.site`, and direct CDNs).

It combines **16–32 parallel TCP worker streams**, **automated Cloudflare Turnstile resolution**, **Smart Memory file deduplication**, **in-memory persistent disk buffering**, and an **Active Anti-Stall Watchdog** to give you uninterrupted, unthrottled maximum ISP download speeds without manual browser clicking or annoying ads.

---

## 📋 Prerequisites (What You Need Before Installing)

Before installing `ffdl`, ensure your computer has:

1. **Python 3.9 or newer installed:**
   - Download from [python.org](https://www.python.org/downloads/).
   - ⚠️ **Important on Windows:** Check the box that says **"Add python.exe to PATH"** during installation.
2. **Google Chrome or Chromium:**
   - `ffdl` uses a lightweight headless browser engine to solve Cloudflare Turnstile challenges in ~3 seconds.

---

## 📦 Installation & Setup

### Option 1: Quick Install via PyPI (Recommended)
```bash
pip install ffdl-cli
playwright install chromium
```

---

### Option 2: Clone & Install from GitHub (Source Code)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ffdl-cli.git
cd ffdl-cli

# 2. Install requirements & CLI in editable mode
pip install -r requirements.txt
pip install -e .

# 3. Install browser engine for Turnstile auto-solving
playwright install chromium
```

---

## 🎮 How to Use `ffdl`

### 1. Interactive Visual Menu (Recommended)
Just type `ffdl` in your terminal:
```bash
ffdl
```
```text
╭───────────────────────────────── MAIN MENU ─────────────────────────────────╮
│ [1] 🌐 Enter Pastebin or Download URL (Auto-extracts & decrypts all parts) │
│ [2] 📁 Load from File (.txt, .html, .md)                                    │
│ [3] 🔥 Scrape Web Page with Firecrawl AI                                    │
│ [4] ⚡ Run Internet Speed Test & Calibrate Concurrency                      │
│ [5] ⚙️  Configure Settings (Concurrency, Output Path)                       │
│ [0] 🚪 Exit                                                                 │
╰─────────────────────────────────────────────────────────────────────────────╯
```
Choose **`[1]`**, paste your pastebin or file URL, and press Enter!

---

### 2. Direct Command-Line Examples

#### Download an entire multi-part FitGirl / PrivateBin link:
```bash
ffdl "https://paste.fitgirl-repacks.site/?707252024fa0ea4f#wWGjJYT7jiRCtTrTb5YoLgj3fF6XRmwXwMnH4LbsWLJ" -o "C:\Downloads"
```

#### Download a single file:
```bash
ffdl "https://fuckingfast.co/dcnsbbuenlbx#Game.part01.rar" -o "C:\Downloads"
```

#### Download from a text or HTML file list:
```bash
ffdl -f links.txt -o "C:\Downloads" -c 24
```

#### Run the built-in Speed Test & Auto-Calibrator:
```bash
ffdl --speedtest
```

#### Probe file sizes without downloading:
```bash
ffdl "https://fuckingfast.co/dcnsbbuenlbx#Game.part01.rar" --info
```

---

## ✨ Features Breakdown

- **⚡ 16–32 Parallel Worker Streams:** Squeezes every megabit out of your connection using chunk range acceleration.
- **🧠 Smart Memory File Skip:** Automatically verifies existing files on disk and skips complete parts in **0.01 seconds**.
- **🔄 Zero-Loss Resumption (`.ffmeta`):** Safely resume interrupted downloads right from the exact byte where it paused.
- **🛡️ 100% Ad & Popup Protection:** Direct streaming bypasses all redirect loops, popups, malware ads, and fake download buttons.
- **🤖 Automated Cloudflare Turnstile Solver:** Solves Turnstile verification tokens and iframe checkboxes automatically in ~3s.
- **🔓 Client-Side Pastebin Auto-Decryption:** Decrypts PrivateBin and FitGirl pastebin links directly into organized queues.
- **⏱️ Active Anti-Stall Watchdog:** Automatically breaks frozen sockets in <4s and recovers full bandwidth instantly.
- **🔄 Dynamic Token Auto-Refresher:** Silently refreshes expired CDN tokens (401/403/410) mid-stream without resetting file progress.
- **💤 Windows Sleep Prevention:** Engages OS keep-awake hooks so your PC never sleeps or suspends network cards during downloads.
- **⚙️ Permanent Settings Persistence:** Remembers your download folders and stream settings in `~/.ffdl_config.json`.

---

## 🛠️ CLI Options Reference

```text
Usage: ffdl [OPTIONS] [URLS]...

Options:
  -i, --interactive          Launch interactive CLI menu dashboard
  -f, --file PATH            File containing URLs or raw HTML snippet
  -p, --paste TEXT           Raw HTML snippet or pasted text containing links
  -o, --output TEXT          Destination directory for downloads (default: ~/Downloads)
  -c, --concurrency INTEGER  Number of parallel worker streams (default: 16)
  --chunk-kb INTEGER         Buffer chunk size in KB (default: 256)
  -w, --overwrite            Force re-download and overwrite existing files
  -s, --scrape               Use Firecrawl to scrape links from web pages
  --speedtest                Run built-in internet speed test and auto-calibrate
  --info                     Probe file size and metadata without downloading
  --links-only               Resolve and print direct CDN download URLs only
  -h, --help                 Show help message and exit
```

---

## 🔧 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **`playwright` browser missing** | Run `playwright install chromium` in your terminal. |
| **`ffdl: command not found`** | Ensure Python Scripts folder is in your PATH, or run `python -m ffdl.cli`. |
| **File already exists on disk** | `ffdl` Smart Memory skips it. Use `-w` or `--overwrite` if you want to force re-download. |

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.
