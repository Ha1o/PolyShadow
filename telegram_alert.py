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
    timestamp: str


def get_alert_level(amount: float, odds: float, nonce: int) -> Tuple[AlertLevel, str, str]:
    """
    Calculate the threat level for a trade.
    
    Args:
        amount: Trade amount in USDC
        odds: Current odds (0-1)
        nonce: Wallet transaction count
        
    Returns:
        Tuple of (AlertLevel, tag_text, emoji)
    """
    # Level S (GHOST): Brand new wallet + large bet
    if nonce <= 1 and amount >= 20000:
        return (
            AlertLevel.S,
            "🚨 <b>SUSPECTED INSIDER</b> 🚨",
            "👻"
        )
    
    # Level A (WHALE): Huge bet from any wallet
    if amount >= 50000:
        return (
            AlertLevel.A,
            "⚠️ <b>WHALE ALERT</b> ⚠️",
            "🐳"
        )
    
    # Level B (SHARK): Default suspicious trade
    return (
        AlertLevel.B,
        "🦈 <b>SMART MONEY</b>",
        "🦈"
    )


def get_nonce_emoji(nonce: int) -> str:
    """Get emoji indicator for wallet age based on nonce."""
    if nonce <= 1:
        return "👻 Ghost"
    elif nonce <= 5:
        return "🆕 Fresh"
    elif nonce <= 10:
        return "🐣 Young"
    else:
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
    
    def __init__(self, bot_token: str, chat_id: str, thread_id: str = None):
        """
        Initialize Telegram alerter.
        
        Args:
            bot_token: Telegram Bot API token
            chat_id: Target chat/channel ID
            thread_id: Optional topic/thread ID for groups with Topics enabled
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.thread_id = thread_id
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
        # Calculate threat level
        level, tag, emoji = get_alert_level(
            alert.amount_usdc,
            alert.odds,
            alert.wallet_nonce
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
        
        # Build the beautiful message
        message = f"""{tag}
{'━' * 30}
{emoji} <b>Level {level.name}</b> | {level.value}

🎯 <b>Event</b>: {safe_market_name}{'...' if len(alert.market_name) > 60 else ''}

{bet_emoji} <b>Bet</b>: <code>{safe_outcome}</code>
📉 <b>Odds</b>: {odds_percent} <i>(Contrarian!)</i>
💰 <b>Size</b>: <code>{amount_str}</code> (${alert.amount_usdc:,.0f})

🕵️ <b>Wallet</b>: <code>{wallet_short}</code>
   ├─ Nonce: <b>{alert.wallet_nonce}</b> {nonce_emoji}
   └─ <a href="https://polygonscan.com/address/{alert.wallet_address}">View on PolygonScan</a>

🔗 <a href="{alert.market_url}">View on Polymarket</a>
{'━' * 30}
<i>⏰ {alert.timestamp} | Captured by PolyShadow</i>"""

        return self.send_message(message)
    
    def send_startup_notification(self) -> bool:
        """Send a notification that the monitor has started."""
        message = """🟢 <b>PolyShadow Monitor Started</b>

━━━━━━━━━━━━━━━━━━━━
📊 <b>Monitoring</b>: Polymarket Politics
💰 <b>Min Amount</b>: $10,000 USDC
📉 <b>Max Odds</b>: ≤30% (Contrarian only)
👛 <b>Wallet Filter</b>: Nonce &lt; 10

🦈 Alert Levels:
   👻 <b>S-GHOST</b>: New wallet + $20K+ bet
   🐳 <b>A-WHALE</b>: $50K+ bet
   🦈 <b>B-SHARK</b>: Smart money detected
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
