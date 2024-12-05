from decimal import Decimal
from typing import Dict, Any, AsyncGenerator
import requests
from wallet.adapters.base_adapter import BaseAdapter
from wallet.wallet_types import WalletType
from wallet.exceptions import QuoteError
from .types import TokenInfo


class LiFiAdapter(BaseAdapter):
    """Adapter for LiFi endpoints"""

    LIFI_API_URL = "https://li.quest/v1"

    def __init__(self, wallet: WalletType):
        super().__init__(wallet)

    def get_token_info(self, chain_id: int, token_address: str) -> TokenInfo:
        """
        Get token information from LiFi API

        Args:
            token_address: Address of the token

        Returns:
            TokenInfo containing token information including decimals

        Raises:
            QuoteError: If token info request fails
        """
        params = {
            "chain": chain_id,
            "token": token_address,
        }

        try:
            response = requests.get(f"{self.LIFI_API_URL}/token", params=params)
            response.raise_for_status()
            token_data = response.json()

            if "decimals" not in token_data:
                raise QuoteError(f"Invalid token info response for {token_address}")

            return TokenInfo(**token_data)

        except requests.exceptions.RequestException as e:
            raise QuoteError(f"Failed to get token info: {str(e)}")

    def get_quote(
        self,
        chain_id: int,
        token_in: TokenInfo,
        token_out: TokenInfo,
        amount_in: Decimal,
    ) -> Dict[str, Any]:
        """
        Get a quote for a token swap using LiFi API

        Args:
            chain_id: Chain ID for the transaction
            token_in: Input token information
            token_out: Output token information
            amount_in: Amount of input token (in decimal)

        Returns:
            Dict containing the quote response

        Raises:
            QuoteError: If quote request fails
        """
        # Get token information and convert amount to proper decimals
        amount_base_units = str(int(amount_in * Decimal(10 ** token_in["decimals"])))

        params = {
            "fromChain": str(chain_id),
            "toChain": str(chain_id),
            "fromToken": token_in["address"],
            "toToken": token_out["address"],
            "fromAmount": amount_base_units,
            "fromAddress": self._wallet._account.address,
            "slippage": 0.5,  # 0.5% slippage default
        }

        try:
            response = requests.get(
                f"{self.LIFI_API_URL}/quote",
                params=params,
                headers={"accept": "application/json"},
            )
            response.raise_for_status()
            quote_data = response.json()

            # Validate quote response
            if "estimate" not in quote_data:
                raise QuoteError("Invalid quote response from LiFi")

            return quote_data

        except requests.exceptions.RequestException as e:
            raise QuoteError(f"Failed to get quote from LiFi: {str(e)}")

    async def swap(self, quote: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Swap tokens using a quote

        Args:
            quote: Quote data from get_quote()

        Yields:
            Dict containing status updates about the swap progress

        Returns:
            Final swap result with transaction details
        """
        transaction_request = {
            "data": quote["transactionRequest"]["data"],
            "to": quote["transactionRequest"]["to"],
            "value": quote["transactionRequest"]["value"],
            "chainId": quote["transactionRequest"]["chainId"],
            "maxFeePerGas": hex(int(quote["estimate"]["gasCosts"][0]["price"])),
            "maxPriorityFeePerGas": hex(
                int(float(quote["estimate"]["gasCosts"][0]["price"]) * 0.1)
            ),
            "gas": hex(int(quote["estimate"]["gasCosts"][0]["estimate"])),
            "type": "0x2",
            "nonce": await self._wallet._web3.eth.get_transaction_count(
                self._wallet._account.address
            ),
        }

        signed_tx = self._wallet._web3.eth.account.sign_transaction(
            transaction_request, self._wallet._account.key
        )

        yield {
            "status": "pending",
            "message": "Transaction submitted, waiting for confirmation...",
            "transaction_hash": tx_hash.hex(),
        }

        tx_hash = await self._wallet._web3.eth.send_raw_transaction(
            signed_tx.raw_transaction
        )

        receipt = await self._wallet._web3.eth.wait_for_transaction_receipt(tx_hash)

        # Return final result
        yield {
            "status": "success" if receipt["status"] == 1 else "failed",
            "message": (
                "Transaction confirmed"
                if receipt["status"] == 1
                else "Transaction failed"
            ),
            "transaction_hash": receipt["transactionHash"].hex(),
        }