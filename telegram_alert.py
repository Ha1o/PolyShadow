"""
PolyShadow Telegram Alert Module
Sends beautifully formatted alerts with threat level classification.
"""

import html
import requests
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Threat level classification for trades."""
    S = "GHOST"   # Brand new wallet + huge bet = likely insider
    A = "WHALE"   # Massive bet from any wallet
    B = "SHARK"   # Meets base suspicious criteria


@dataclass
class TradeAlert:
    """Data structure for a suspicious trade alert."""
    market_name: str
    market_url: str
    outcome: str
    odds: float
    amount_usdc: float
    wallet_address: str
    wallet_nonce: int
    wallet_age_description: str
    trade_type: str  # "contrarian" or "momentum"
    timestamp: str  # Alert timestamp (when captured)
    # New fields for enhanced display
    trader_name: str = ""       # User's Polymarket username
    trade_timestamp: str = ""   # When trade was executed
    event_slug: str = ""        # For correct Polymarket URL


def get_alert_level(
    amount: float,
    odds: float,
    nonce: int,
    min_amount: float = 10000,
    max_contrarian_odds: float = 0.30
) -> Tuple[AlertLevel, str, str]:
    """
    Calculate the threat level for a trade based on 3 factors.
    
    Scoring system (lower nonce + lower odds + higher amount = higher threat):
    - Nonce: 0-1 = +3, 2-5 = +2, 6-9 = +1
    - Odds: < max_odds/3 = +3, < max_odds*2/3 = +2, < max_odds = +1
    - Amount: > 3x min_amount = +3, > 2x min_amount = +2, >= min_amount = +1
    
    Level S (GHOST): Score >= 7 - Likely insider
    Level A (HIGH SUSPICION): Score >= 5 - High suspicion
    Level B (SHARK): Score >= 1 - Worth watching
    
    Args:
        amount: Trade amount in USDC
        odds: Current odds (0-1)
        nonce: Wallet transaction count
        min_amount: MIN_TRADE_AMOUNT_USDC from config (default $10K)
        max_contrarian_odds: MAX_ODDS_FOR_CONTRARIAN from config (default 30%)
        
    Returns:
        Tuple of (AlertLevel, tag_text, emoji)
    """
    score = 0
    
    # Nonce scoring (lower = more suspicious)
    if nonce <= 1:
        score += 3
    elif nonce <= 5:
        score += 2
    elif nonce <= 9:
        score += 1
    
    # Odds scoring - dynamic based on max_contrarian_odds
    # < 1/3 threshold = +3, < 2/3 threshold = +2, < threshold = +1
    if odds < max_contrarian_odds / 3:
        score += 3
    elif odds < max_contrarian_odds * 2 / 3:
        score += 2
    elif odds < max_contrarian_odds:
        score += 1
    
    # Amount scoring - dynamic based on min_amount
    # > 3x = +3, > 2x = +2, >= 1x = +1
    if amount >= min_amount * 3:
        score += 3
    elif amount >= min_amount * 2:
        score += 2
    elif amount >= min_amount:
        score += 1
    
    # Level classification based on total score
    if score >= 7:
        return (
            AlertLevel.S,
            "🚨 <b>SUSPECTED INSIDER</b> 🚨",
            "👻"
        )
    elif score >= 5:
        return (
            AlertLevel.A,
            "⚠️ <b>HIGH SUSPICION</b> ⚠️",
            "🐳"
        )
    else:
        return (
            AlertLevel.B,
            "🦈 <b>SMART MONEY</b>",
            "🦈"
        )


def get_nonce_emoji(nonce: int) -> str:
    """
    Get emoji indicator for wallet age based on nonce.
    
    Must align with detection logic: nonce < 10 = suspicious (new wallet)
    """
    if nonce <= 1:
        return "👻 Ghost"
    elif nonce <= 5:
        return "🆕 Fresh"
    elif nonce < 10:  # Match detection threshold: nonce < 10 = suspicious
        return "🐣 Young"
    else:  # nonce >= 10 = not suspicious
        return "👤 Known"


def format_amount(amount: float) -> str:
    """Format amount with K/M suffix for readability."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.1f}K"
    else:
        return f"${amount:.2f}"


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent Telegram parse errors."""
    return html.escape(str(text))


class TelegramAlerter:
    """Sends beautifully formatted alerts to Telegram."""
    
    TELEGRAM_API_BASE = "https://api.telegram.org/bot"
    
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        thread_id: str = None,
        min_amount: float = 10000,
        max_contrarian_odds: float = 0.30,
        nonce_threshold: int = 10
    ):
        """
        Initialize Telegram alerter.
        
        Args:
            bot_token: Telegram Bot API token
            chat_id: Target chat/channel ID
            thread_id: Optional topic/thread ID for groups with Topics enabled
            min_amount: MIN_TRADE_AMOUNT_USDC for dynamic scoring
            max_contrarian_odds: MAX_ODDS_FOR_CONTRARIAN for dynamic scoring
            nonce_threshold: SUSPICIOUS_WALLET_NONCE_THRESHOLD for startup notification
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.min_amount = min_amount
        self.max_contrarian_odds = max_contrarian_odds
        self.nonce_threshold = nonce_threshold
        self.api_url = f"{self.TELEGRAM_API_BASE}{bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message to the configured chat.
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or Markdown)
            
        Returns:
            bool: True if sent successfully
        """
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False,
            }
            
            # Add thread_id for Telegram Topics support
            if self.thread_id:
                payload["message_thread_id"] = int(self.thread_id)
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_trade_alert(self, alert: TradeAlert) -> bool:
        """
        Send a beautifully formatted trade alert with threat level.
        
        Args:
            alert: TradeAlert data structure
            
        Returns:
            bool: True if sent successfully
        """
        # Calculate threat level (using dynamic config values)
        level, tag, emoji = get_alert_level(
            alert.amount_usdc,
            alert.odds,
            alert.wallet_nonce,
            self.min_amount,
            self.max_contrarian_odds
        )
        
        # Format values
        amount_str = format_amount(alert.amount_usdc)
        odds_percent = f"{alert.odds:.1%}"
        wallet_short = f"{alert.wallet_address[:8]}...{alert.wallet_address[-6:]}"
        nonce_emoji = get_nonce_emoji(alert.wallet_nonce)
        
        # Determine bet direction emoji
        bet_emoji = "🔴" if alert.outcome.upper() == "NO" else "🟢"
        
        # Escape user-provided data to prevent HTML parse errors
        safe_market_name = escape_html(alert.market_name[:60])
        safe_outcome = escape_html(alert.outcome.upper())
        safe_trader_name = escape_html(alert.trader_name) if alert.trader_name else "Unknown"
        
        # Escape URLs for HTML href attributes
        safe_market_url = html.escape(alert.market_url, quote=True)
        safe_wallet_url = html.escape(f"https://polygonscan.com/address/{alert.wallet_address}", quote=True)
        
        # Handle empty trade_timestamp
        trade_time_line = ""
        if alert.trade_timestamp:
            trade_time_line = f"\n🕐 <b>Trade Time</b>: {alert.trade_timestamp} (UTC+8)"
        
        # Build the beautiful message
        message = f"""{tag}
{'━' * 30}
{emoji} <b>Level {level.name}</b> | {level.value}

🎯 <b>Event</b>: {safe_market_name}{'...' if len(alert.market_name) > 60 else ''}

{bet_emoji} <b>Bet</b>: <code>{safe_outcome}</code>
📉 <b>Odds</b>: {odds_percent} <i>({alert.trade_type.capitalize()})</i>
💰 <b>Size</b>: <code>{amount_str}</code> (${alert.amount_usdc:,.0f})

👤 <b>Trader</b>: <code>{safe_trader_name}</code>{trade_time_line}

🕵️ <b>Wallet</b>: <code>{wallet_short}</code>
   ├─ Nonce: <b>{alert.wallet_nonce}</b> {nonce_emoji}
   └─ <a href="{safe_wallet_url}">View on PolygonScan</a>

🔗 <a href="{safe_market_url}">View on Polymarket</a>
{'━' * 30}
<i>⏰ {alert.timestamp} | Captured by PolyShadow</i>"""

        return self.send_message(message)
    
    def send_startup_notification(self) -> bool:
        """Send a notification that the monitor has started with dynamic config values."""
        min_amount_str = f"${self.min_amount:,.0f}"
        max_odds_str = f"{self.max_contrarian_odds:.0%}"
        
        message = f"""🟢 <b>PolyShadow Monitor Started</b>

━━━━━━━━━━━━━━━━━━━━
📊 <b>Monitoring</b>: Polymarket Politics
💰 <b>Min Amount</b>: {min_amount_str} USDC
📉 <b>Max Odds</b>: ≤{max_odds_str} (Contrarian only)
👛 <b>Wallet Filter</b>: Nonce &lt; {self.nonce_threshold} (new wallets)

🦈 Alert Levels (Score-based):
   👻 <b>S-GHOST</b>: Score ≥7 (Suspected insider)
   🐳 <b>A-HIGH</b>: Score ≥5 (High suspicion)
   🦈 <b>B-SHARK</b>: Score &lt;5 (Smart money)
━━━━━━━━━━━━━━━━━━━━
<i>Scanning for insider activity...</i>"""
        return self.send_message(message)
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send an error notification."""
        message = f"""🔴 <b>PolyShadow Error</b>

{error_message}

<i>The monitor will attempt to recover automatically.</i>"""
        return self.send_message(message)


if __name__ == "__main__":
    # Test the alerter
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python telegram_alert.py <BOT_TOKEN> <CHAT_ID>")
        sys.exit(1)
    
    alerter = TelegramAlerter(sys.argv[1], sys.argv[2])
    
    # Send test alert
    test_alert = TradeAlert(
        market_name="Will Trump win the 2024 Presidential Election?",
        market_url="https://polymarket.com/event/test",
        outcome="NO",
        odds=0.15,
        amount_usdc=25000.00,
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        wallet_nonce=1,
        wallet_age_description="🆕 Brand New (1 txs)",
        trade_type="contrarian",
        timestamp="2024-01-08 12:00:00 UTC"
    )
    
    if alerter.send_trade_alert(test_alert):
        print("✅ Test alert sent successfully!")
    else:
        print("❌ Failed to send test alert")
