# VPS Specifications & Headful Browser Access Guide

## 1. System Specifications
This system is an **ARM64 Virtual Private Server (VPS)**, likely an Oracle Cloud Ampere A1 instance.

*   **Operating System:** Debian GNU/Linux 13 (trixie)
*   **Architecture:** `aarch64` (ARM64)
*   **CPU:** ARM Neoverse-N1 (2 Cores)
*   **Memory:** 4GB RAM
*   **Virtualization:** KVM
*   **GPU:** No physical GPU (uses virtualized graphics)

---

## 2. Running Headful Browsers (Chrome/Selenium)
Standard "Headful" mode requires a display. Since this is a server, you have two main options:

### Option A: Using the existing Remote Desktop (XRDP)
The system already has an XRDP server running on **Display :10**. If you connect via RDP, you can run browsers directly. To target this display from a terminal or script:

```bash
# Set the display environment variable
export DISPLAY=:10

# Launch Chromium (once installed)
chromium
```

### Option B: Using a Virtual Framebuffer (Xvfb)
If you aren't using RDP but your script *requires* a "headful" browser (for extensions, screenshots, or avoiding bot detection), use `xvfb-run`. It creates a virtual display in memory.

```bash
# Run your script through xvfb
xvfb-run python your_script.py
```

---

## 3. Installation Guide (ARM64)
Because this is an ARM system, you must use `chromium` instead of the standard "Google Chrome" `.deb` package.

### Prerequisites
```bash
sudo apt update
sudo apt install chromium chromium-driver xvfb python3-selenium
```

### Selenium Configuration (Python Example)
When writing your Selenium script, do **not** add the `--headless` argument.

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

options = Options()
# options.add_argument("--headless")  <-- DO NOT ADD THIS
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# On this server, specify the driver path if needed
service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://google.com")
print(driver.title)
driver.quit()
```

---

## 4. Key Performance Tip
With **4GB of RAM**, a headful browser can be demanding. If you encounter crashes (Out of Memory), consider creating a swap file:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
