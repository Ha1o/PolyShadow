"""
PolyShadow Test Suite - Alert Levels
Tests the Telegram alert formatting and threat level classification.
Run: python -m tests.test_alert_levels
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram_alert import TelegramAlerter, TradeAlert, get_alert_level, AlertLevel
from config import load_config


def test_alert_levels():
    """Test the alert level classification logic."""
    print("Testing alert level classification...\n")
    
    # Level S (GHOST) - New wallet + big bet
    level, tag, emoji = get_alert_level(25000, 0.15, 1)
    assert level == AlertLevel.S, f"Expected S, got {level}"
    print(f"✅ Level S (GHOST): {emoji} - Nonce 1 + $25K")
    
    # Level A (WHALE) - Huge bet
    level, tag, emoji = get_alert_level(75000, 0.25, 50)
    assert level == AlertLevel.A, f"Expected A, got {level}"
    print(f"✅ Level A (WHALE): {emoji} - $75K bet")
    
    # Level B (SHARK) - Base criteria
    level, tag, emoji = get_alert_level(15000, 0.20, 5)
    assert level == AlertLevel.B, f"Expected B, got {level}"
    print(f"✅ Level B (SHARK): {emoji} - $15K, nonce 5")
    
    print("\n✅ All alert level tests passed!")


def test_send_alerts():
    """Send test alerts to Telegram (requires .env configuration)."""
    print("\nSending test alerts to Telegram...")
    
    config = load_config()
    alerter = TelegramAlerter(config.telegram_bot_token, config.telegram_chat_id)
    
    # Test Level S alert
    test_s = TradeAlert(
        market_name="Will Trump be the 2028 Republican Nominee?",
        market_url="https://polymarket.com/event/trump-2028",
        outcome="NO",
        odds=0.12,
        amount_usdc=25000.00,
        wallet_address="0xabc123def456789012345678901234567890abcd",
        wallet_nonce=1,
        wallet_age_description="👻 Ghost",
        trade_type="contrarian",
        timestamp="2026-01-09 00:00:00 UTC"
    )
    
    if alerter.send_trade_alert(test_s):
        print("✅ Level S (GHOST) alert sent!")
    else:
        print("❌ Failed to send Level S alert")
    
    # Test Level A alert
    test_a = TradeAlert(
        market_name="Will Biden win the 2024 Election?",
        market_url="https://polymarket.com/event/biden-2024",
        outcome="YES",
        odds=0.25,
        amount_usdc=75000.00,
        wallet_address="0x9876543210fedcba9876543210fedcba98765432",
        wallet_nonce=50,
        wallet_age_description="👤 Known",
        trade_type="contrarian",
        timestamp="2026-01-09 00:01:00 UTC"
    )
    
    if alerter.send_trade_alert(test_a):
        print("✅ Level A (WHALE) alert sent!")
    else:
        print("❌ Failed to send Level A alert")
    
    # Test Level B alert
    test_b = TradeAlert(
        market_name="Will DeSantis run in 2028?",
        market_url="https://polymarket.com/event/desantis-2028",
        outcome="NO",
        odds=0.20,
        amount_usdc=15000.00,
        wallet_address="0x1111222233334444555566667777888899990000",
        wallet_nonce=5,
        wallet_age_description="🐣 Young",
        trade_type="contrarian",
        timestamp="2026-01-09 00:02:00 UTC"
    )
    
    if alerter.send_trade_alert(test_b):
        print("✅ Level B (SHARK) alert sent!")
    else:
        print("❌ Failed to send Level B alert")
    
    print("\n🎉 Check your Telegram for test alerts!")


if __name__ == "__main__":
    test_alert_levels()
    
    # Only send real alerts if --send flag is passed
    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        test_send_alerts()
    else:
        print("\nTip: Run with --send flag to send test alerts to Telegram")
