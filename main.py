"""
PolyShadow Main Module
Main monitoring loop for detecting suspicious trades on Polymarket.
"""

import time
import signal
import logging
from datetime import datetime
from typing import Set

from config import load_config, Config
from wallet_checker import WalletChecker
from telegram_alert import TelegramAlerter, TradeAlert
from polymarket_api import PolymarketAPI, Market, Trade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PolyShadow")


class PolyShadowMonitor:
    """
    Main monitoring class for detecting suspicious Polymarket trades.
    
    Implements the full detection pipeline:
    1. Fetch top politics markets
    2. Get recent trades for each market
    3. Filter by amount and direction
    4. Check wallet suspiciousness
    5. Send alerts
    """
    
    def __init__(self, config: Config):
        """
        Initialize the monitor with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.running = False
        
        # Track seen trades to avoid duplicate alerts
        self.seen_trades: Set[str] = set()
        
        # Initialize components
        logger.info("Initializing PolyShadow components...")
        
        self.polymarket = PolymarketAPI(config.polymarket_api_key or None)
        self.wallet_checker = WalletChecker(
            config.polygon_rpc_url,
            config.suspicious_wallet_nonce_threshold
        )
        self.alerter = TelegramAlerter(
            config.telegram_bot_token,
            config.telegram_chat_id,
            config.telegram_thread_id or None
        )
        
        logger.info("✅ All components initialized successfully")
    
    def analyze_trade(
        self,
        trade: Trade,
        trade_type: str,
        market: Market
    ) -> bool:
        """
        Perform full analysis on a suspicious trade.
        
        Args:
            trade: The trade to analyze
            trade_type: "contrarian" or "momentum"
            market: The market the trade belongs to
            
        Returns:
            bool: True if alert was sent
        """
        # Skip if we've already seen this trade
        if trade.trade_id in self.seen_trades:
            return False
        
        self.seen_trades.add(trade.trade_id)
        
        # Determine which wallet to check (taker initiated the trade)
        wallet_address = trade.taker_address
        if not wallet_address:
            wallet_address = trade.maker_address
        
        if not wallet_address:
            logger.warning(f"Trade {trade.trade_id} has no wallet address")
            return False
        
        # Check wallet suspiciousness
        is_suspicious, nonce = self.wallet_checker.is_suspicious_wallet(wallet_address)
        
        if not is_suspicious:
            logger.debug(
                f"Wallet {wallet_address[:10]}... is not suspicious (nonce: {nonce})"
            )
            return False
        
        # All filters passed - send alert!
        logger.warning(
            f"🚨 HIGH SUSPICION TRADE DETECTED!\n"
            f"   Market: {market.question}\n"
            f"   Outcome: {trade.outcome}\n"
            f"   Amount: ${trade.amount_usdc:,.2f}\n"
            f"   Wallet: {wallet_address}\n"
            f"   Wallet Age: {nonce} txs"
        )
        
        # Get current price for the outcome
        outcome_idx = 0
        for i, o in enumerate(market.outcomes):
            if o == trade.outcome:
                outcome_idx = i
                break
        
        current_odds = market.outcome_prices[outcome_idx] if outcome_idx < len(market.outcome_prices) else trade.price
        
        # Build and send alert
        alert = TradeAlert(
            market_name=market.question,
            market_url=market.url,
            outcome=trade.outcome,
            odds=current_odds,
            amount_usdc=trade.amount_usdc,
            wallet_address=wallet_address,
            wallet_nonce=nonce,
            wallet_age_description=self.wallet_checker.get_wallet_age_description(nonce),
            trade_type=trade_type,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        return self.alerter.send_trade_alert(alert)
    
    def monitor_cycle(self) -> int:
        """
        Run one monitoring cycle.
        
        Returns:
            int: Number of alerts sent
        """
        alerts_sent = 0
        
        # Step 1: Get top politics markets
        logger.info("📊 Fetching top politics markets...")
        markets = self.polymarket.get_top_politics_markets(limit=20)
        
        if not markets:
            logger.warning("No markets fetched, skipping cycle")
            return 0
        
        logger.info(f"Monitoring {len(markets)} markets")
        
        # Step 2-4: Process each market
        for market in markets:
            try:
                # Get recent trades
                trades = self.polymarket.get_recent_trades(market.condition_id)
                
                if not trades:
                    continue
                
                # Build outcome price map
                outcome_prices = {}
                for i, outcome in enumerate(market.outcomes):
                    if i < len(market.outcome_prices):
                        outcome_prices[outcome] = market.outcome_prices[i]
                
                # Filter for suspicious trades
                suspicious = self.polymarket.filter_significant_trades(
                    trades,
                    self.config.min_trade_amount_usdc,
                    self.config.max_odds_for_contrarian,
                    outcome_prices
                )
                
                # Analyze each suspicious trade
                for trade, trade_type in suspicious:
                    if self.analyze_trade(trade, trade_type, market):
                        alerts_sent += 1
                
            except Exception as e:
                logger.error(f"Error processing market {market.question[:30]}...: {e}")
                continue
        
        return alerts_sent
    
    def run(self):
        """Start the monitoring loop."""
        self.running = True
        
        # Send startup notification
        self.alerter.send_startup_notification()
        
        logger.info(
            f"🚀 PolyShadow Monitor started\n"
            f"   Poll interval: {self.config.poll_interval_seconds}s\n"
            f"   Min trade amount: ${self.config.min_trade_amount_usdc:,.0f}\n"
            f"   Contrarian odds threshold: {self.config.max_odds_for_contrarian:.0%}\n"
            f"   Suspicious wallet threshold: {self.config.suspicious_wallet_nonce_threshold} txs"
        )
        
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"Starting monitoring cycle #{cycle_count}")
                
                alerts = self.monitor_cycle()
                
                logger.info(f"Cycle #{cycle_count} complete. Alerts sent: {alerts}")
                logger.info(f"Next cycle in {self.config.poll_interval_seconds} seconds...")
                
                # Wait for next cycle
                time.sleep(self.config.poll_interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                self.alerter.send_error_notification(str(e))
                # Wait before retrying
                time.sleep(self.config.poll_interval_seconds)
        
        logger.info("PolyShadow Monitor stopped")
    
    def stop(self):
        """Stop the monitoring loop."""
        self.running = False


def main():
    """Main entry point."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗  ██████╗ ██╗  ██╗   ██╗███████╗██╗  ██╗ █████╗ ██████╗  ██████╗ ██╗    ██╗   ║
    ║   ██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝██╔════╝██║  ██║██╔══██╗██╔══██╗██╔═══██╗██║    ██║   ║
    ║   ██████╔╝██║   ██║██║   ╚████╔╝ ███████╗███████║███████║██║  ██║██║   ██║██║ █╗ ██║   ║
    ║   ██╔═══╝ ██║   ██║██║    ╚██╔╝  ╚════██║██╔══██║██╔══██║██║  ██║██║   ██║██║███╗██║   ║
    ║   ██║     ╚██████╔╝███████╗██║   ███████║██║  ██║██║  ██║██████╔╝╚██████╔╝╚███╔███╔╝   ║
    ║   ╚═╝      ╚═════╝ ╚══════╝╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚══╝╚══╝    ║
    ║                                                               ║
    ║          Polymarket Insider Trading Detector v1.0             ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create and run monitor
        monitor = PolyShadowMonitor(config)
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received")
            monitor.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start monitoring
        monitor.run()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Configuration error: {e}")
        print("Please copy .env.example to .env and fill in your credentials.")
        return 1
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        print(f"\n❌ Connection error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
