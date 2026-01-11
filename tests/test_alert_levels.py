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
    """
    Test the alert level classification logic with dynamic scoring.
    
    Scoring system (based on config values):
    - Nonce: 0-1 = +3, 2-5 = +2, 6-9 = +1
    - Odds: < max_odds/3 = +3, < max_odds*2/3 = +2, < max_odds = +1
    - Amount: >= 3x min_amount = +3, >= 2x min_amount = +2, >= min_amount = +1
    
    Level S: Score >= 7, Level A: Score >= 5, Level B: Score >= 1
    """
    print("Testing alert level classification (dynamic scoring)...\n")
    
    # Default config: min_amount=$10K, max_odds=30%
    min_amount = 10000
    max_odds = 0.30
    
    # Level S (GHOST) - Score 9: nonce=1(+3), odds=5%<10%(+3), amount=$35K>=3x$10K(+3)
    level, tag, emoji = get_alert_level(35000, 0.05, 1, min_amount, max_odds)
    assert level == AlertLevel.S, f"Expected S (score 9), got {level}"
    print(f"✅ Level S: {emoji} - Nonce 1 + 5% odds + $35K (3.5x) = Score 9")
    
    # Level A (HIGH SUSPICION) - Score 6: nonce=3(+2), odds=15%<20%(+2), amount=$25K>=2x$10K(+2)
    level, tag, emoji = get_alert_level(25000, 0.15, 3, min_amount, max_odds)
    assert level == AlertLevel.A, f"Expected A (score 6), got {level}"
    print(f"✅ Level A: {emoji} - Nonce 3 + 15% odds + $25K (2.5x) = Score 6")
    
    # Level B (SHARK) - Score 4: nonce=7(+1), odds=25%<30%(+1), amount=$20K>=2x(+2)
    level, tag, emoji = get_alert_level(20000, 0.25, 7, min_amount, max_odds)
    assert level == AlertLevel.B, f"Expected B (score 4), got {level}"
    print(f"✅ Level B: {emoji} - Nonce 7 + 25% odds + $20K (2x) = Score 4")
    
    # Test with different config: min_amount=$50K, max_odds=40%
    print("\n--- Testing with different config (min=$50K, max_odds=40%) ---")
    level, tag, emoji = get_alert_level(150000, 0.10, 1, 50000, 0.40)
    # nonce=1(+3), odds=10%<13.3%(+3), amount=$150K>=3x$50K(+3) = 9
    assert level == AlertLevel.S, f"Expected S with custom config, got {level}"
    print(f"✅ Level S: {emoji} - $150K with $50K threshold = 3x multiplier")
    
    print("\n✅ All alert level tests passed (dynamic scoring verified)!")


def test_send_alerts():
    """Send test alerts to Telegram (requires .env configuration)."""
    print("\nSending test alerts to Telegram...")
    
    config = load_config()
    alerter = TelegramAlerter(config.telegram_bot_token, config.telegram_chat_id)
    
    # Test Level S alert
    test_s = TradeAlert(
        market_name="Will Trump be the 2028 Republican Nominee?",
        market_url="https://polymarket.com/event/2028-republican-presidential-nominee",
        outcome="NO",
        odds=0.12,
        amount_usdc=25000.00,
        wallet_address="0xabc123def456789012345678901234567890abcd",
        wallet_nonce=1,
        wallet_age_description="👻 Ghost",
        trade_type="contrarian",
        timestamp="2026-01-09 00:00:00 UTC",
        trader_name="CryptoWhale99",
        trade_timestamp="2026-01-09 00:00:00",
        event_slug="2028-republican-presidential-nominee"
    )
    
    if alerter.send_trade_alert(test_s):
        print("✅ Level S (GHOST) alert sent!")
    else:
        print("❌ Failed to send Level S alert")
    
    # Test Level A alert
    test_a = TradeAlert(
        market_name="Will Biden win the 2024 Election?",
        market_url="https://polymarket.com/event/presidential-election-winner-2024",
        outcome="YES",
        odds=0.25,
        amount_usdc=75000.00,
        wallet_address="0x9876543210fedcba9876543210fedcba98765432",
        wallet_nonce=50,
        wallet_age_description="👤 Known",
        trade_type="contrarian",
        timestamp="2026-01-09 00:01:00 UTC",
        trader_name="PolyTrader_Elite",
        trade_timestamp="2026-01-09 00:01:00",
        event_slug="presidential-election-winner-2024"
    )
    
    if alerter.send_trade_alert(test_a):
        print("✅ Level A (WHALE) alert sent!")
    else:
        print("❌ Failed to send Level A alert")
    
    # Test Level B alert
    test_b = TradeAlert(
        market_name="Will DeSantis run in 2028?",
        market_url="https://polymarket.com/event/will-desantis-run-2028",
        outcome="NO",
        odds=0.20,
        amount_usdc=15000.00,
        wallet_address="0x1111222233334444555566667777888899990000",
        wallet_nonce=5,
        wallet_age_description="🐣 Young",
        trade_type="contrarian",
        timestamp="2026-01-09 00:02:00 UTC",
        trader_name="SharkInvestor",
        trade_timestamp="2026-01-09 00:02:00",
        event_slug="will-desantis-run-2028"
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
