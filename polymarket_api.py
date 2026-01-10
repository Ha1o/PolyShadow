"""
PolyShadow Polymarket API Module
Wrapper for Polymarket public APIs to fetch markets and trades.
Uses Gamma API for market discovery and Data API for trade history.
No authentication required - all endpoints are public.
"""

import requests
import logging
import json
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Polymarket Public API endpoints (no auth required)
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"


@dataclass
class Market:
    """Represents a Polymarket event market."""
    condition_id: str
    question: str
    slug: str
    volume: float
    outcomes: list[str]
    outcome_prices: list[float]
    url: str


@dataclass
class Trade:
    """Represents a single trade on Polymarket."""
    trade_id: str
    market_id: str
    maker_address: str
    taker_address: str
    outcome: str
    side: str  # "BUY" or "SELL"
    price: float
    size: float  # Amount in shares
    amount_usdc: float  # Dollar amount
    timestamp: datetime


class PolymarketAPI:
    """
    Wrapper for Polymarket public APIs.
    
    Uses Gamma API for market discovery and Data API for trade history.
    All endpoints are public and require no authentication.
    """
    
    @staticmethod
    def _parse_list_field(value):
        """Parse a field that could be JSON array string, comma-separated, or list."""
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return value.split(",")
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Polymarket API client.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def get_top_politics_markets(self, limit: int = 20) -> list[Market]:
        """
        Get the top Politics markets by volume.
        
        Args:
            limit: Maximum number of markets to return
            
        Returns:
            List of Market objects sorted by volume
        """
        try:
            # Use Gamma API for market discovery (more complete data)
            response = self.session.get(
                f"{GAMMA_API_BASE}/markets",
                params={
                    "tag": "politics",
                    "closed": "false",
                    "order": "volume",
                    "ascending": "false",
                    "limit": limit,
                },
                timeout=15
            )
            response.raise_for_status()
            
            markets_data = response.json()
            markets = []
            
            for m in markets_data:
                try:
                    # Parse outcome prices
                    outcome_prices = [float(p) for p in self._parse_list_field(m.get("outcomePrices"))]
                    outcomes = self._parse_list_field(m.get("outcomes"))
                    
                    markets.append(Market(
                        condition_id=m.get("conditionId", ""),
                        question=m.get("question", "Unknown"),
                        slug=m.get("slug", ""),
                        volume=float(m.get("volume", 0)),
                        outcomes=outcomes,
                        outcome_prices=outcome_prices,
                        url=f"https://polymarket.com/event/{m.get('slug', '')}",
                    ))
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing market: {e}")
                    continue
            
            logger.info(f"Fetched {len(markets)} politics markets")
            return markets
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    def get_recent_trades(self, condition_id: str, limit: int = 50) -> list[Trade]:
        """
        Get recent trades for a specific market using the public Data API.
        
        Args:
            condition_id: The market condition ID (hex format with 0x prefix)
            limit: Maximum number of trades to return
            
        Returns:
            List of Trade objects
        """
        try:
            # Use public Data API for trade history (no auth required)
            response = self.session.get(
                f"{DATA_API_BASE}/trades",
                params={
                    "market": condition_id,  # Filter by market condition ID
                    "limit": limit,
                },
                timeout=30
            )
            response.raise_for_status()
            
            trades_data = response.json()
            trades = []
            
            # Data API returns a list directly
            if not isinstance(trades_data, list):
                trades_data = []
            
            for t in trades_data:
                try:
                    price = float(t.get("price", 0))
                    size = float(t.get("size", 0))
                    
                    # Data API uses 'proxyWallet' for the trader address
                    wallet_address = t.get("proxyWallet", "")
                    
                    # Parse Unix timestamp
                    timestamp_val = t.get("timestamp", 0)
                    if isinstance(timestamp_val, (int, float)):
                        trade_time = datetime.fromtimestamp(timestamp_val)
                    else:
                        trade_time = datetime.now()
                    
                    # Use transaction hash as trade ID
                    trade_id = t.get("transactionHash", "")
                    
                    trades.append(Trade(
                        trade_id=trade_id,
                        market_id=t.get("conditionId", condition_id),
                        maker_address="",  # Data API doesn't separate maker/taker
                        taker_address=wallet_address,
                        outcome=t.get("outcome", ""),
                        side=t.get("side", "BUY").upper(),
                        price=price,
                        size=size,
                        amount_usdc=price * size,
                        timestamp=trade_time,
                    ))
                except (ValueError, KeyError, TypeError) as e:
                    logger.debug(f"Error parsing trade: {e}")
                    continue
            
            logger.debug(f"Fetched {len(trades)} trades for market {condition_id[:16]}...")
            return trades
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch trades for {condition_id[:16]}...: {e}")
            return []
    
    def filter_significant_trades(
        self,
        trades: list[Trade],
        min_amount: float,
        max_contrarian_odds: float,
        market_outcome_prices: dict[str, float]
    ) -> list[tuple[Trade, str]]:
        """
        Filter trades for suspicious activity.
        
        Args:
            trades: List of trades to filter
            min_amount: Minimum trade amount in USDC
            max_contrarian_odds: Maximum odds for contrarian classification
            market_outcome_prices: Dict mapping outcome name to current price
            
        Returns:
            List of (Trade, trade_type) tuples where trade_type is "contrarian" or "momentum"
        """
        suspicious_trades = []
        
        for trade in trades:
            # Filter 1: Amount threshold
            if trade.amount_usdc < min_amount:
                continue
            
            # Only analyze BUY trades
            if trade.side != "BUY":
                continue
            
            # Get the current price for this outcome
            current_price = market_outcome_prices.get(trade.outcome, 0.5)
            
            # Filter 2: Trade direction analysis
            trade_type = None
            
            # Contrarian: Buying low-probability outcomes
            if current_price < max_contrarian_odds:
                trade_type = "contrarian"
                logger.info(
                    f"Contrarian trade: ${trade.amount_usdc:.2f} on {trade.outcome} "
                    f"@ {current_price:.1%} odds"
                )
            
            # Momentum: Large trades (could be momentum buying)
            elif trade.amount_usdc >= min_amount * 5:  # 5x threshold = momentum
                trade_type = "momentum"
                logger.info(
                    f"Momentum trade: ${trade.amount_usdc:.2f} on {trade.outcome}"
                )
            
            if trade_type:
                suspicious_trades.append((trade, trade_type))
        
        return suspicious_trades


if __name__ == "__main__":
    # Test API connection
    logging.basicConfig(level=logging.INFO)
    
    api = PolymarketAPI()
    
    print("Fetching top politics markets...")
    markets = api.get_top_politics_markets(5)
    
    for m in markets:
        print(f"\n📊 {m.question}")
        print(f"   Volume: ${m.volume:,.0f}")
        print(f"   URL: {m.url}")
        for i, outcome in enumerate(m.outcomes):
            price = m.outcome_prices[i] if i < len(m.outcome_prices) else 0
            print(f"   - {outcome}: {price:.1%}")
