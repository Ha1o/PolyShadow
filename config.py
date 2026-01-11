"""
PolyShadow Configuration Module
Loads and validates environment variables.
"""

import os
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration settings for PolyShadow."""
    
    # Polygon RPC
    polygon_rpc_url: str
    
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_thread_id: str  # Optional: for groups with Topics enabled
    
    # Polymarket API (optional)
    polymarket_api_key: str
    polymarket_api_secret: str
    polymarket_api_passphrase: str
    
    # Monitoring thresholds
    poll_interval_seconds: int
    min_trade_amount_usdc: float
    max_odds_for_contrarian: float
    suspicious_wallet_nonce_threshold: int


def load_config() -> Config:
    """
    Load configuration from .env file.
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        ValueError: If required configuration is missing
    """
    load_dotenv()
    
    # Required fields
    polygon_rpc_url = os.getenv("POLYGON_RPC_URL")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Validate required fields
    if not polygon_rpc_url:
        raise ValueError("POLYGON_RPC_URL is required in .env")
    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required in .env")
    if not telegram_chat_id:
        raise ValueError("TELEGRAM_CHAT_ID is required in .env")
    
    return Config(
        polygon_rpc_url=polygon_rpc_url,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        telegram_thread_id=os.getenv("TELEGRAM_THREAD_ID", ""),
        polymarket_api_key=os.getenv("POLYMARKET_API_KEY", ""),
        polymarket_api_secret=os.getenv("POLYMARKET_API_SECRET", ""),
        polymarket_api_passphrase=os.getenv("POLYMARKET_API_PASSPHRASE", ""),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "30")),
        # Core detection thresholds (must match business logic: $10K / 30% / nonce<10)
        min_trade_amount_usdc=float(os.getenv("MIN_TRADE_AMOUNT_USDC", "10000")),
        max_odds_for_contrarian=float(os.getenv("MAX_ODDS_FOR_CONTRARIAN", "0.30")),
        suspicious_wallet_nonce_threshold=int(os.getenv("SUSPICIOUS_WALLET_NONCE_THRESHOLD", "10")),  # nonce < this value = suspicious
    )


# Polymarket Constants
POLYMARKET_HOST = "https://clob.polymarket.com"
POLYMARKET_CHAIN_ID = 137  # Polygon Mainnet

# Politics category tag (used to filter markets)
POLITICS_CATEGORY = "politics"
