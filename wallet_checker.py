"""
PolyShadow Wallet Checker Module
Analyzes wallet addresses on Polygon for suspicious activity patterns.
"""

from web3 import Web3
from web3.exceptions import Web3Exception
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from cachetools import TTLCache
import requests.exceptions
import logging
import time

logger = logging.getLogger(__name__)

# Default RPC timeout in seconds
DEFAULT_RPC_TIMEOUT = 10

# Nonce cache settings
NONCE_CACHE_TTL = 600  # 10 minutes
NONCE_CACHE_MAXSIZE = 1000  # Max cached addresses


class WalletChecker:
    """
    Checks wallet addresses for signs of potential insider trading.
    
    A wallet is considered suspicious if it has a very low transaction count (nonce),
    indicating it was created recently specifically for trading.
    
    Features TTL cache for nonce lookups to reduce RPC pressure.
    """
    
    def __init__(self, rpc_url: str, nonce_threshold: int = 10, rpc_timeout: int = DEFAULT_RPC_TIMEOUT):
        """
        Initialize the WalletChecker.
        
        Args:
            rpc_url: Polygon RPC endpoint URL
            nonce_threshold: Maximum nonce to consider a wallet "new/suspicious"
            rpc_timeout: Timeout for RPC requests in seconds (default 10s)
        """
        # Initialize Web3 with request timeout to prevent hanging
        self.web3 = Web3(Web3.HTTPProvider(
            rpc_url,
            request_kwargs={"timeout": rpc_timeout}
        ))
        self.nonce_threshold = nonce_threshold
        self.rpc_timeout = rpc_timeout
        
        # TTL cache for nonce lookups (reduces RPC calls for repeated addresses)
        self._nonce_cache: TTLCache = TTLCache(maxsize=NONCE_CACHE_MAXSIZE, ttl=NONCE_CACHE_TTL)
        
        # Verify connection (with timeout protection)
        try:
            if not self.web3.is_connected():
                raise ConnectionError(f"Cannot connect to Polygon RPC: {rpc_url}")
            logger.info(f"Connected to Polygon. Chain ID: {self.web3.eth.chain_id}")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Polygon RPC: {rpc_url} - {e}")
    
    def _fetch_nonce_from_rpc(self, address: str) -> int:
        """Internal method to fetch nonce from RPC with retries."""
        checksum_address = Web3.to_checksum_address(address)
        return self.web3.eth.get_transaction_count(checksum_address)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            Web3Exception,
            ConnectionError,
            TimeoutError,
            ValueError,  # web3 JSON-RPC errors often raise ValueError
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            OSError,
        )),
        before_sleep=lambda retry_state: logger.warning(
            f"RPC request failed ({type(retry_state.outcome.exception()).__name__}), "
            f"retrying in {retry_state.next_action.sleep:.1f}s... "
            f"(attempt {retry_state.attempt_number}/3)"
        ),
        reraise=True
    )
    def get_wallet_nonce(self, address: str) -> int:
        """
        Get the transaction count (nonce) for a wallet address.
        
        Uses TTL cache to reduce RPC calls for repeated addresses.
        
        Args:
            address: Ethereum/Polygon wallet address
            
        Returns:
            int: Number of transactions sent from this wallet
            
        Raises:
            Various exceptions if all retries fail
        """
        # Normalize address for cache key
        cache_key = address.lower()
        
        # Check cache first
        if cache_key in self._nonce_cache:
            nonce = self._nonce_cache[cache_key]
            logger.debug(f"Wallet {address[:10]}... nonce from cache: {nonce}")
            return nonce
        
        # Fetch from RPC
        nonce = self._fetch_nonce_from_rpc(address)
        
        # Store in cache
        self._nonce_cache[cache_key] = nonce
        logger.debug(f"Wallet {address[:10]}... nonce from RPC: {nonce} (cached)")
        return nonce
    
    def is_suspicious_wallet(self, address: str) -> tuple[bool, int]:
        """
        Check if a wallet is suspicious (likely new/insider wallet).
        
        Args:
            address: Wallet address to check
            
        Returns:
            tuple: (is_suspicious: bool, nonce: int)
                   Returns (False, -1) on RPC failure or invalid address
        """
        # Validate address format before making RPC calls
        if not address or not isinstance(address, str):
            logger.warning(f"⚠️ Invalid wallet address (empty or wrong type): {address}")
            return False, -1
        
        # Check basic address format (0x prefix + 40 hex chars)
        address_clean = address.strip()
        if not address_clean.startswith("0x") or len(address_clean) != 42:
            logger.warning(f"⚠️ Invalid wallet address format: {address}")
            return False, -1
        
        try:
            # Validate checksum address (will raise if invalid hex)
            Web3.to_checksum_address(address_clean)
        except ValueError as e:
            logger.warning(f"⚠️ Invalid wallet address (checksum failed): {address} - {e}")
            return False, -1
        
        try:
            nonce = self.get_wallet_nonce(address)
            is_suspicious = nonce < self.nonce_threshold
            
            if is_suspicious:
                logger.info(f"🚨 Suspicious wallet detected: {address} (nonce: {nonce}, threshold: {self.nonce_threshold})")
            else:
                logger.debug(f"Wallet {address} passed check (nonce: {nonce} >= threshold: {self.nonce_threshold})")
            
            return is_suspicious, nonce
            
        except RetryError as e:
            # All retries exhausted
            original_error = e.last_attempt.exception() if e.last_attempt else e
            logger.warning(
                f"⚠️ Skipping alert for wallet {address}: "
                f"RPC nonce fetch failed after 3 retries ({type(original_error).__name__}: {original_error})"
            )
            return False, -1
            
        except Exception as e:
            # Unexpected error - log as error level
            logger.error(
                f"❌ Unexpected error checking wallet {address}: {type(e).__name__}: {e}"
            )
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
        retry=retry_if_exception_type((
            Web3Exception,
            ConnectionError,
            TimeoutError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            OSError,
        )),
        reraise=True
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
