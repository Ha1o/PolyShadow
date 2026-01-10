"""
PolyShadow Wallet Checker Module
Analyzes wallet addresses on Polygon for suspicious activity patterns.
"""

from web3 import Web3
from web3.exceptions import Web3Exception
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)


class WalletChecker:
    """
    Checks wallet addresses for signs of potential insider trading.
    
    A wallet is considered suspicious if it has a very low transaction count (nonce),
    indicating it was created recently specifically for trading.
    """
    
    def __init__(self, rpc_url: str, nonce_threshold: int = 10):
        """
        Initialize the WalletChecker.
        
        Args:
            rpc_url: Polygon RPC endpoint URL
            nonce_threshold: Maximum nonce to consider a wallet "new/suspicious"
        """
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self.nonce_threshold = nonce_threshold
        
        # Verify connection
        if not self.web3.is_connected():
            raise ConnectionError(f"Cannot connect to Polygon RPC: {rpc_url}")
        
        logger.info(f"Connected to Polygon. Chain ID: {self.web3.eth.chain_id}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Web3Exception, ConnectionError, TimeoutError)),
        before_sleep=lambda retry_state: logger.warning(
            f"RPC request failed, retrying in {retry_state.next_action.sleep} seconds..."
        )
    )
    def get_wallet_nonce(self, address: str) -> int:
        """
        Get the transaction count (nonce) for a wallet address.
        
        Args:
            address: Ethereum/Polygon wallet address
            
        Returns:
            int: Number of transactions sent from this wallet
        """
        # Ensure address is checksummed
        checksum_address = Web3.to_checksum_address(address)
        nonce = self.web3.eth.get_transaction_count(checksum_address)
        logger.debug(f"Wallet {address[:10]}... has nonce: {nonce}")
        return nonce
    
    def is_suspicious_wallet(self, address: str) -> tuple[bool, int]:
        """
        Check if a wallet is suspicious (likely new/insider wallet).
        
        Args:
            address: Wallet address to check
            
        Returns:
            tuple: (is_suspicious: bool, nonce: int)
        """
        try:
            nonce = self.get_wallet_nonce(address)
            is_suspicious = nonce < self.nonce_threshold
            
            if is_suspicious:
                logger.info(f"🚨 Suspicious wallet detected: {address} (nonce: {nonce})")
            
            return is_suspicious, nonce
        except Exception as e:
            logger.error(f"Error checking wallet {address}: {e}")
            # Return False to avoid false positives on errors
            return False, -1
    
    def get_wallet_age_description(self, nonce: int) -> str:
        """
        Get a human-readable description of wallet age based on nonce.
        
        Args:
            nonce: Transaction count of the wallet
            
        Returns:
            str: Description like "🆕 Brand New (2 txs)" or "📊 Established (150 txs)"
        """
        if nonce < 0:
            return "❓ Unknown"
        elif nonce < 5:
            return f"🆕 Brand New ({nonce} txs)"
        elif nonce < 10:
            return f"⚠️ Very New ({nonce} txs)"
        elif nonce < 50:
            return f"📊 Lightly Used ({nonce} txs)"
        elif nonce < 200:
            return f"✅ Established ({nonce} txs)"
        else:
            return f"🏛️ Veteran ({nonce} txs)"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Web3Exception, ConnectionError, TimeoutError))
    )
    def get_wallet_balance(self, address: str) -> float:
        """
        Get the MATIC balance of a wallet.
        
        Args:
            address: Wallet address
            
        Returns:
            float: Balance in MATIC
        """
        checksum_address = Web3.to_checksum_address(address)
        balance_wei = self.web3.eth.get_balance(checksum_address)
        balance_matic = self.web3.from_wei(balance_wei, 'ether')
        return float(balance_matic)


if __name__ == "__main__":
    # Quick test
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 2:
        print("Usage: python wallet_checker.py <RPC_URL> [address]")
        sys.exit(1)
    
    rpc_url = sys.argv[1]
    test_address = sys.argv[2] if len(sys.argv) > 2 else "0x0000000000000000000000000000000000000000"
    
    checker = WalletChecker(rpc_url)
    is_sus, nonce = checker.is_suspicious_wallet(test_address)
    print(f"Address: {test_address}")
    print(f"Nonce: {nonce}")
    print(f"Suspicious: {is_sus}")
    print(f"Description: {checker.get_wallet_age_description(nonce)}")
