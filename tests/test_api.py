"""
PolyShadow Test Suite - Polymarket API
Tests the public Polymarket API connectivity (no auth required).
Run: python -m tests.test_api
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polymarket_api import PolymarketAPI


def test_fetch_markets():
    """Test fetching top politics markets from Polymarket."""
    print("🔍 Fetching top Polymarket Politics markets...\n")
    
    api = PolymarketAPI()
    markets = api.get_top_politics_markets(limit=5)
    
    assert len(markets) > 0, "Failed to fetch any markets"
    print(f"✅ Successfully fetched {len(markets)} markets\n")
    print("=" * 60)
    
    for i, m in enumerate(markets, 1):
        print(f"\n📊 #{i}: {m.question}")
        print(f"   💰 Volume: ${m.volume:,.0f}")
        print(f"   🔗 {m.url}")
        
        for j, outcome in enumerate(m.outcomes):
            if j < len(m.outcome_prices):
                print(f"   • {outcome}: {m.outcome_prices[j]:.1%}")
    
    print("\n" + "=" * 60)
    return markets


def test_fetch_trades(markets):
    """Test fetching trades for a market."""
    if not markets:
        print("⚠️  No markets to test trades with")
        return
    
    market = markets[0]
    print(f"\n📈 Fetching trades for: {market.question[:50]}...")
    
    api = PolymarketAPI()
    trades = api.get_recent_trades(market.condition_id, limit=10)
    
    print(f"✅ Fetched {len(trades)} trades")
    
    for i, t in enumerate(trades[:5], 1):
        print(f"   Trade #{i}: ${t.amount_usdc:.2f} {t.side} '{t.outcome}'")
        if t.taker_address:
            print(f"            Wallet: {t.taker_address[:16]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("  PolyShadow API Connectivity Test")
    print("  Testing public Polymarket APIs (no auth required)")
    print("=" * 60)
    
    markets = test_fetch_markets()
    test_fetch_trades(markets)
    
    print("\n✅ All API tests passed!")
