# 🗳️ VoteScript

**Automated bot for voting on FeatureUpvote.com.
Sends votes to multiple configurable URLs, simulates realistic user behavior, and supports Tor-based anonymity.**

**The project is continuously being developed and improved, with new features, performance upgrades, and optimizations added regularly to ensure greater stability and flexibility.
Any suggestions, ideas, or feature requests are welcome and appreciated.**

---

## ⚠️ Disclaimer

-This project is intended for **educational and testing purposes only**.
-And i am NOT responsible for any misuse or violation of third-party terms of service.

---

## 🚀 Features

* ✅ Multi-URL voting system
* 🔁 Configurable votes per target
* 🌐 Tor integration (via GUI)
* 🧠 Human-like behavior simulation
* 🧩 Modular architecture (strategies, browser, core)
* 🖥️ GUI with advanced controls
* 📊 Real-time vote monitoring & control

---

## 📁 Project Structure

```bash
VoteScript/
│   gui.py
│   main.py
│   start_tor.bat
│   requirements.txt
│   LICENSE
│   README.md
│
├── browser/           # Fingerprinting & human behavior simulation
├── config/            # Configuration files
├── core/              # Main logic (voting + Tor management)
├── driver/            # WebDriver (GeckoDriver)
├── strategies/        # Anti-block & timing strategies
├── Tor/               # Embedded Tor client
├── utils/             # Helpers & logging
```

---

## ⚙️ Configuration

All settings are managed in:

```bash
/config/config.json
```

### Example:

```json
{
    "target_urls": [
        "https://www.example.com/vote",
        "https://www.example.com/vote?option=1",
        "https://www.example.com/vote?option=2",
        "https://www.example.com/vote?option=3"
    ],

    "total_votes": 0,
}
```

---

### 🔹 Parameters

* **target_urls** → List of voting endpoints
* **total_votes** → Number of votes sent **per URL**

---

## ▶️ Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Configure targets

Edit:

```bash
config/config.json
```

---

### 3. Browser

```bash
FIREFOX MUST BE INSTALLED ON YOUR PC
```

---

### 4. Start Tor (IMPORTANT)

⚠️ Tor is **NOT started via `start_tor.bat`**

👉 You must start Tor directly from the GUI:

* Open the GUI:

```bash
pythonw gui.py
```

* Click:
  👉 **"Start Tor"**

---

### 5. Run the bot

You can:

* Start from GUI (recommended)

  * Click:
    👉 **"Start Bot"**

* Or run (**NOT recommended**):

```bash
python main.py
```

---

## 🧠 Pre-Navigation Mode (Anti-Detection)

The GUI includes a **Pre-Navigation** option:

### 🔹 Enabled (RECOMMENDED)

* Bot navigates randomly through URLs in `config.json` before voting
* Simulates real user browsing behavior
* ✅ Lower chance of detection / vote blocking

### 🔹 Disabled

* Bot sends votes immediately
* ⚡ Faster execution
* ❌ Higher risk of being flagged and votes blocked

---

## 📊 Real-Time Votes Panel

The GUI includes a **REAL-TIME VOTES** section:

* Displays the **title of each target link**
* Shows the **number of votes sent per link**
* Allows enabling/disabling voting **individually for each URL**

👉 This gives full control over the voting process while the bot is running.

---

## 🧠 How It Works

* Uses browser automation (GeckoDriver)
* Simulates human-like interactions
* Routes traffic through Tor
* Applies anti-detection strategies
* Handles blocking dynamically

---

## 🧾 Versions

### v1.0

* Basic voting script
* Single URL support

### v2.0

* Multi-URL support
* Improved request system

### v3.0

* Introduced config system (`config.json`)
* Modular architecture

### v4.0

* Tor integration
* Anonymity improvements
* Raw UI

### v5.0

* Advanced anti-detection strategies
* Pre-navigation system
* Human behavior simulation
* GUI controls (Start Tor, settings)
* Real-time vote monitoring system
* Performance & stability improvements

---

## 📜 License

MIT License © 2026
