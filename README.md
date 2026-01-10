# PolyShadow 🕵️‍♂️

**Insider Trading Monitor for Polymarket Politics**

PolyShadow monitors Polymarket's political prediction markets for suspicious trading activity. It identifies large contrarian bets placed by fresh wallets—a pattern often associated with insider trading.

---

## 🔍 Detection Logic

PolyShadow flags trades that meet ALL of the following criteria:

| Filter | Threshold | Rationale |
|--------|-----------|-----------|
| **Category** | Politics | Focus on politically-sensitive markets |
| **Trade Size** | >$10,000 USDC | Filters out noise from small trades |
| **Odds** | <30% | Contrarian bets against market consensus |
| **Wallet Nonce** | <10 transactions | Fresh wallet detection |

### 🧪 Fresh Wallet / Nonce Check

The **nonce check** is key to identifying potential insiders. When someone knows the outcome of a political event, they typically:
1. Create a new wallet (to avoid linking to their identity)
2. Fund it with USDC
3. Place a single large bet

PolyShadow detects this by querying the wallet's transaction count (nonce) on Polygon. A wallet with <10 transactions placing a $10K+ contrarian bet is highly suspicious.

---

## 🚨 Alert Levels

| Level | Name | Emoji | Criteria |
|-------|------|-------|----------|
| **S** | Ghost | 👻 | Nonce ≤1 + $20K+ bet |
| **A** | Whale | 🐳 | $50K+ bet from any wallet |
| **B** | Shark | 🦈 | Meets base suspicious criteria |

Alerts are sent via Telegram with rich formatting including:
- Market name and link
- Bet direction and odds
- Trade size
- Wallet address with PolygonScan link
- Wallet age classification

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Polygon RPC endpoint (Alchemy, Infura, or QuickNode)
- Telegram Bot Token (create via [@BotFather](https://t.me/BotFather))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/PolyShadow.git
cd PolyShadow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Edit `.env` with your credentials:

```ini
# Required
POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/YOUR_KEY
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Thresholds (optional - defaults shown)
POLL_INTERVAL_SECONDS=30
MIN_TRADE_AMOUNT_USDC=10000
MAX_ODDS_FOR_CONTRARIAN=0.30
SUSPICIOUS_WALLET_NONCE_THRESHOLD=10
```

### Run

```bash
python main.py
```

---

## 📁 Project Structure

```
PolyShadow/
├── main.py              # Main monitoring loop
├── config.py            # Configuration management
├── polymarket_api.py    # Polymarket API wrapper
├── wallet_checker.py    # Polygon nonce checker
├── telegram_alert.py    # Telegram bot integration
├── tests/               # Test suite
│   ├── test_api.py      # API connectivity tests
│   └── test_alert_levels.py  # Alert formatting tests
├── .env.example         # Configuration template
├── requirements.txt     # Python dependencies
└── LICENSE              # MIT License
```

---

## 🧪 Testing

Run tests from the project root:

```bash
# Test Polymarket API connectivity (no auth required)
python -m tests.test_api

# Test alert level classification
python -m tests.test_alert_levels

# Send test alerts to Telegram (requires .env)
python -m tests.test_alert_levels --send
```

---

## 🛡️ Security

- **Never commit `.env`** — it contains your API keys
- `.gitignore` is configured to exclude sensitive files
- All Polymarket data is fetched from public APIs (no auth required)
- RPC calls are made with retry logic and exponential backoff

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This tool is for **educational and research purposes only**. It does not provide financial advice. Trading on prediction markets involves significant risk. Always do your own research before making any trading decisions.

---

<p align="center">
  <i>Built with 🐍 Python | Powered by Polymarket & Polygon</i>
</p>
