"""
Funding Rate Service for the AR trading application.

This module provides centralized functionality for fetching funding rates
from multiple exchanges using direct API calls for better reliability.
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status

from src.schemas.funding_rate_schema import FundingRateItem, FundingRateResponse, FundingRatesSummaryResponse

logger = logging.getLogger(__name__)

# Supported exchanges for funding rates with their API endpoints
SUPPORTED_EXCHANGES = ['bitunix', 'kucoin', 'coinex']  # 'mexc' commented out due to reliability issues

# Exchange API configurations
EXCHANGE_APIS = {
    'bitunix': {
        'base_url': 'https://fapi.bitunix.com/api/v1/futures/market',
        'funding_rate_endpoint': '/funding_rate',
        'funding_rate_batch_endpoint': '/funding_rate/batch',
        'rate_limit': 10,  # requests per second
        'requires_auth': False
    },
    'kucoin': {
        'base_url': 'https://api-futures.kucoin.com/api/v1',
        'funding_rate_endpoint': '/contracts/active',
        'rate_limit': 5,  # requests per second
        'requires_auth': False
    },
    # 'mexc': {  # Commented out due to reliability issues
    #     'base_url': 'https://contract.mexc.com/api/v1/contract',
    #     'funding_rate_endpoint': '/funding_rate',
    #     'rate_limit': 3,  # 3 requests per second
    #     'requires_auth': False
    # },
    'coinex': {
        'base_url': 'https://api.coinex.com/v2',
        'funding_rate_endpoint': '/futures/funding-rate',
        'rate_limit': 5,  # requests per second
        'requires_auth': False
    }
}

# Supported symbols (base currencies) - only those available on Bitunix
SUPPORTED_SYMBOLS = ['BTC', 'ETH', 'XRP', 'ADA', 'SOL', 'SUI', 'XLM', 'TRX', 'PEPE', 'BNB', 'ATOM', 'DOT', 'BCH']

# Exchange-specific symbol mappings for each exchange
EXCHANGE_SYMBOL_MAPPING = {
    'bitunix': {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT', 
        'XRP': 'XRPUSDT',
        'ADA': 'ADAUSDT',
        'SOL': 'SOLUSDT',
        'SUI': 'SUIUSDT',
        'XLM': 'XLMUSDT',
        'PEPE': '1000PEPEUSDT',  # Bitunix uses 1000PEPEUSDT for PEPE
        'TRX': 'TRXUSDT',
        'BNB': 'BNBUSDT',
        'ATOM': 'ATOMUSDT',
        'DOT': 'DOTUSDT',
        'BCH': 'BCHUSDT'
    },
    'kucoin': {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT', 
        'XRP': 'XRPUSDT',
        'ADA': 'ADAUSDT',
        'SOL': 'SOLUSDT',
        'SUI': 'SUIUSDT',
        'XLM': 'XLMUSDT',
        # 'PEPE': '1000PEPEUSDT',  # Kucoin doesn't support PEPE
        'TRX': 'TRXUSDT',
        'BNB': 'BNBUSDT',
        'ATOM': 'ATOMUSDT',
        'DOT': 'DOTUSDT',
        'BCH': 'BCHUSDT'
    },
    # 'mexc': {  # Commented out due to reliability issues
    #     'BTC': 'BTC_USDT',
    #     'ETH': 'ETH_USDT',
    #     'XRP': 'XRP_USDT',
    #     'ADA': 'ADA_USDT',
    #     'SOL': 'SOL_USDT',
    #     'SUI': 'SUI_USDT',
    #     'XLM': 'XLM_USDT',
    #     'PEPE': 'PEPE_USDT',
    #     'TRX': 'TRX_USDT',
    #     'BNB': 'BNB_USDT',
    #     'ATOM': 'ATOM_USDT',
    #     'DOT': 'DOT_USDT',
    #     'BCH': 'BCH_USDT'
    # },
    'coinex': {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT', 
        'XRP': 'XRPUSDT',
        'ADA': 'ADAUSDT',
        'SOL': 'SOLUSDT',
        'SUI': 'SUIUSDT',
        'XLM': 'XLMUSDT',
        # 'PEPE': '1000PEPEUSDT',  # Coinex doesn't support PEPE
        'TRX': 'TRXUSDT',
        'BNB': 'BNBUSDT',
        'ATOM': 'ATOMUSDT',
        'DOT': 'DOTUSDT',
        'BCH': 'BCHUSDT'
    }
}

class FundingRateService:
    """Service for fetching funding rates from multiple exchanges using direct APIs."""
    
    def __init__(self):
        """Initialize the funding rate service."""
        self.session = None
        self.rate_limiters = {}
        logger.info("Funding Rate Service initialized")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _rate_limit(self, exchange_id: str):
        """Simple rate limiting for exchange API calls."""
        if exchange_id not in self.rate_limiters:
            self.rate_limiters[exchange_id] = 0
        
        rate_limit = EXCHANGE_APIS[exchange_id]['rate_limit']
        current_time = datetime.now().timestamp()
        
        # Only apply rate limiting if we're making too many requests too quickly
        # For parallel requests, this should rarely trigger
        if self.rate_limiters[exchange_id] > 0:
            time_since_last = current_time - self.rate_limiters[exchange_id]
            min_interval = 1.0 / rate_limit
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                await asyncio.sleep(wait_time)
        
        self.rate_limiters[exchange_id] = current_time
    
    async def _fetch_bitunix_funding_rate(self, symbol: str) -> Optional[FundingRateItem]:
        """Fetch funding rate from Bitunix API (individual symbol)."""
        try:
            await self._rate_limit('bitunix')
            session = await self._get_session()
            
            url = f"{EXCHANGE_APIS['bitunix']['base_url']}{EXCHANGE_APIS['bitunix']['funding_rate_endpoint']}?symbol={symbol}"
            logger.info(f"Fetching Bitunix funding rate for symbol: {symbol} from URL: {url}")
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Bitunix API response for {symbol}: {data}")
                    
                    if data.get('code') == 0 and 'data' in data:
                        funding_data = data['data']
                        
                        # Parse funding rate (Bitunix returns percentage, not decimal)
                        funding_rate = float(funding_data.get('fundingRate', 0))
                        mark_price_raw = funding_data.get('markPrice')
                        last_price_raw = funding_data.get('lastPrice')
                        
                        # Handle price parsing with better precision handling
                        mark_price = None
                        last_price = None
                        
                        if mark_price_raw and mark_price_raw != '0' and mark_price_raw != 0:
                            try:
                                mark_price = float(mark_price_raw)
                                logger.debug(f"Parsed mark price for {symbol}: {mark_price}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Could not parse mark price '{mark_price_raw}' for {symbol}: {e}")
                        
                        if last_price_raw and last_price_raw != '0' and last_price_raw != 0:
                            try:
                                last_price = float(last_price_raw)
                                logger.debug(f"Parsed last price for {symbol}: {last_price}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Could not parse last price '{last_price_raw}' for {symbol}: {e}")
                        
                        return FundingRateItem(
                            exchange='BITUNIX',
                            symbol=symbol,
                            funding_rate=funding_rate,
                            mark_price=mark_price,
                            last_price=last_price,
                            next_funding_time=None,  # Bitunix doesn't provide this
                            previous_funding_rate=None,  # Bitunix doesn't provide this
                            estimated_rate=None,  # Bitunix doesn't provide this
                            last_updated=datetime.utcnow()
                        )
                    else:
                        logger.warning(f"Bitunix API error for {symbol}: {data}")
                        return None
                else:
                    logger.warning(f"Bitunix API HTTP error for {symbol}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Bitunix funding rate for {symbol}: {e}")
            return None
    
    async def _fetch_bitunix_funding_rates_batch(self) -> List[FundingRateItem]:
        """Fetch all funding rates from Bitunix API in one batch call."""
        try:
            await self._rate_limit('bitunix')
            session = await self._get_session()
            
            url = f"{EXCHANGE_APIS['bitunix']['base_url']}{EXCHANGE_APIS['bitunix']['funding_rate_batch_endpoint']}"
            logger.info(f"Fetching Bitunix batch funding rates from URL: {url}")
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('code') == 0 and 'data' in data:
                        funding_rates = []
                        funding_data_list = data['data']
                        
                        for funding_data in funding_data_list:
                            symbol = funding_data.get('symbol', '')
                            logger.debug(f"Found Bitunix symbol: {symbol}")
                            
                            # Only include symbols we support
                            base_symbol = symbol.replace('USDT', '')
                            if base_symbol in SUPPORTED_SYMBOLS:
                                try:
                                    # Parse funding rate (Bitunix returns percentage, not decimal)
                                    funding_rate = float(funding_data.get('fundingRate', 0))
                                    mark_price_raw = funding_data.get('markPrice')
                                    last_price_raw = funding_data.get('lastPrice')
                                    
                                    # Handle price parsing with better precision handling
                                    mark_price = None
                                    last_price = None
                                    
                                    if mark_price_raw and mark_price_raw != '0' and mark_price_raw != 0:
                                        try:
                                            mark_price = float(mark_price_raw)
                                        except (ValueError, TypeError) as e:
                                            logger.warning(f"Could not parse mark price '{mark_price_raw}' for {symbol}: {e}")
                                    
                                    if last_price_raw and last_price_raw != '0' and last_price_raw != 0:
                                        try:
                                            last_price = float(last_price_raw)
                                        except (ValueError, TypeError) as e:
                                            logger.warning(f"Could not parse last price '{last_price_raw}' for {symbol}: {e}")
                                    
                                    funding_rates.append(FundingRateItem(
                                        exchange='BITUNIX',
                                        symbol=symbol,
                                        funding_rate=funding_rate,
                                        mark_price=mark_price,
                                        last_price=last_price,
                                        next_funding_time=None,  # Bitunix doesn't provide this
                                        previous_funding_rate=None,  # Bitunix doesn't provide this
                                        estimated_rate=None,  # Bitunix doesn't provide this
                                        last_updated=datetime.utcnow()
                                    ))
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Error parsing funding data for {symbol}: {e}")
                                    continue
                        
                        logger.info(f"Fetched {len(funding_rates)} funding rates from Bitunix batch API")
                        return funding_rates
                    else:
                        logger.warning(f"Bitunix batch API error: {data}")
                        return []
                else:
                    logger.warning(f"Bitunix batch API HTTP error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Bitunix batch funding rates: {e}")
            return []
    
    async def _fetch_kucoin_funding_rate(self, symbol: str) -> Optional[FundingRateItem]:
        """Fetch funding rate from Kucoin Futures API."""
        try:
            await self._rate_limit('kucoin')
            session = await self._get_session()
            
            # Kucoin Futures API returns all contracts, we need to filter by symbol
            url = f"{EXCHANGE_APIS['kucoin']['base_url']}{EXCHANGE_APIS['kucoin']['funding_rate_endpoint']}"
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('code') == '200000' and 'data' in data:
                        contracts = data['data']
                        
                        # Find the contract that matches our symbol
                        # Kucoin uses symbols like XBTUSDTM, ETHUSDTM, etc.
                        # Special case: BTC -> XBT for Kucoin
                        kucoin_symbol = symbol.replace('USDT', 'USDTM')
                        if kucoin_symbol.startswith('BTC'):
                            kucoin_symbol = kucoin_symbol.replace('BTC', 'XBT')
                        
                        matching_contract = None
                        
                        for contract in contracts:
                            if contract.get('symbol') == kucoin_symbol:
                                matching_contract = contract
                                break
                        
                        if matching_contract:
                            # Kucoin returns funding rate as decimal, convert to percentage
                            funding_rate = float(matching_contract.get('fundingFeeRate', 0)) * 100
                            mark_price = float(matching_contract.get('markPrice', 0)) if matching_contract.get('markPrice') else None
                            next_funding_time = matching_contract.get('nextFundingRateDateTime')
                            
                            # Convert next funding time to datetime if available
                            next_funding_time_dt = None
                            if next_funding_time:
                                try:
                                    next_funding_time_dt = datetime.fromtimestamp(int(next_funding_time) / 1000, tz=timezone.utc)
                                except (ValueError, TypeError):
                                    logger.warning(f"Could not parse Kucoin next funding time: {next_funding_time}")
                            
                            return FundingRateItem(
                                exchange='KUCOIN',
                                symbol=symbol,
                                funding_rate=funding_rate,
                                mark_price=mark_price,  # Now we have mark price!
                                last_price=None,  # Kucoin doesn't provide last price in this endpoint
                                next_funding_time=next_funding_time_dt,
                                previous_funding_rate=None,  # Kucoin doesn't provide this
                                estimated_rate=None,  # Kucoin doesn't provide this
                                last_updated=datetime.utcnow()
                            )
                        else:
                            logger.warning(f"Symbol {kucoin_symbol} not found in Kucoin contracts")
                            return None
                    else:
                        logger.warning(f"Kucoin API error: {data}")
                        return None
                else:
                    logger.warning(f"Kucoin API HTTP error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Kucoin funding rate for {symbol}: {e}")
            return None
    


    # async def _fetch_mexc_funding_rate(self, symbol: str) -> Optional[FundingRateItem]:
    #     """Fetch funding rate from MEXC Contract API."""
    #     try:
    #         await self._rate_limit('mexc')
    #         session = await self._get_session()
    #         
    #         # MEXC contract API uses the symbol directly in the URL path
    #         url = f"{EXCHANGE_APIS['mexc']['base_url']}{EXCHANGE_APIS['mexc']['funding_rate_endpoint']}/{symbol}"
    #         
    #         # Increased timeout for MEXC to prevent hanging
    #         timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for MEXC
    #         
    #         async with session.get(url, timeout=timeout) as response:
    #             if response.status == 200:
    #                 data = await response.json()
    #                 
    #                 if data.get('success') and data.get('code') == 0 and 'data' in data:
    #                     funding_data = data['data']
    #                     
    #                     # MEXC contract API returns funding rate as decimal, convert to percentage
    #                     funding_rate = float(funding_data.get('fundingRate', 0)) * 100
    #                     next_settle_time = funding_data.get('nextSettleTime')
    #                     
    #                     # Convert next settle time to datetime if available
    #                     next_funding_time = None
    #                     if next_settle_time:
    #                         try:
    #                             next_funding_time = datetime.fromtimestamp(int(next_settle_time) / 1000, tz=timezone.utc)
    #                         except (ValueError, TypeError):
    #                             logger.warning(f"Could not parse MEXC next settle time: {next_settle_time}")
    #                     
    #                     # No mark price fetching - MEXC price endpoints are unreliable
    #                     # Return funding rate data without mark price to avoid errors
    #                     
    #                     return FundingRateItem(
    #                         exchange='MEXC',
    #                         symbol=symbol.replace('_', ''),  # Convert back to BTCUSDT format for consistency
    #                         funding_rate=funding_rate,
    #                         mark_price=None,  # MEXC price endpoints removed due to reliability issues
    #                         last_price=None,  # MEXC doesn't provide last price in funding rate endpoint
    #                         next_funding_time=next_funding_time,
    #                         previous_funding_rate=None,  # MEXC doesn't provide this
    #                         estimated_rate=None,  # MEXC doesn't provide this
    #                         last_updated=datetime.utcnow()
    #                     )
    #                 else:
    #                     logger.warning(f"MEXC Contract API error: {data}")
    #                     return None
    #             elif response.status == 429:  # Rate limit exceeded
    #                 logger.warning(f"MEXC rate limit exceeded for {symbol}, returning N/A")
    #                 return None
    #             else:
    #                 logger.warning(f"MEXC Contract API HTTP error: {response.status}")
    #                 return None
    #                 
    #     except asyncio.TimeoutError:
    #         logger.warning(f"MEXC API timeout for {symbol}, returning N/A")
    #         return None
    #     except Exception as e:
    #         logger.error(f"Error fetching MEXC funding rate for {symbol}: {e}")
    #         return None
    
    async def _fetch_coinex_funding_rate(self, symbol: str) -> Optional[FundingRateItem]:
        """Fetch funding rate from Coinex Futures API."""
        try:
            await self._rate_limit('coinex')
            session = await self._get_session()
            
            url = f"{EXCHANGE_APIS['coinex']['base_url']}{EXCHANGE_APIS['coinex']['funding_rate_endpoint']}?market={symbol}"
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('code') == 0 and 'data' in data:
                        funding_data_list = data['data']
                        
                        # Find the data for our specific symbol
                        matching_data = None
                        for item in funding_data_list:
                            if item.get('market') == symbol:
                                matching_data = item
                                break
                        
                        if matching_data:
                            # Coinex returns funding rate as decimal, convert to percentage
                            funding_rate = float(matching_data.get('latest_funding_rate', 0)) * 100
                            mark_price = float(matching_data.get('mark_price', 0)) if matching_data.get('mark_price') and matching_data.get('mark_price') != '0' else None
                            next_funding_time = matching_data.get('next_funding_time')
                            
                            # Convert next funding time to datetime if available
                            next_funding_time_dt = None
                            if next_funding_time:
                                try:
                                    next_funding_time_dt = datetime.fromtimestamp(int(next_funding_time) / 1000, tz=timezone.utc)
                                except (ValueError, TypeError):
                                    logger.warning(f"Could not parse Coinex next funding time: {next_funding_time}")
                            
                            return FundingRateItem(
                                exchange='COINEX',
                                symbol=symbol,
                                funding_rate=funding_rate,
                                mark_price=mark_price,  # Now we have mark price!
                                last_price=None,  # Coinex doesn't provide last price in this endpoint
                                next_funding_time=next_funding_time_dt,
                                previous_funding_rate=None,  # Coinex doesn't provide this
                                estimated_rate=None,  # Coinex doesn't provide this
                                last_updated=datetime.utcnow()
                            )
                        else:
                            logger.warning(f"Symbol {symbol} not found in Coinex funding rate data")
                            return None
                    else:
                        logger.warning(f"Coinex API error: {data}")
                        return None
                else:
                    logger.warning(f"Coinex API HTTP error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Coinex funding rate for {symbol}: {e}")
            return None
    
    async def _fetch_exchange_funding_rate(
        self, 
        exchange_id: str, 
        symbol: str
    ) -> Optional[FundingRateItem]:
        """
        Fetch funding rate for a specific symbol from a specific exchange.
        
        Args:
            exchange_id: Exchange identifier
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            FundingRateItem if successful, None if not supported or error
        """
        try:
            if exchange_id == 'bitunix':
                return await self._fetch_bitunix_funding_rate(symbol)
            elif exchange_id == 'kucoin':
                return await self._fetch_kucoin_funding_rate(symbol)
            # elif exchange_id == 'mexc':  # Commented out due to reliability issues
            #     return await self._fetch_mexc_funding_rate(symbol)
            elif exchange_id == 'coinex':
                return await self._fetch_coinex_funding_rate(symbol)
            else:
                logger.warning(f"Exchange {exchange_id} not supported for funding rates")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol} on {exchange_id}: {e}")
            return None
    
    async def get_symbol_funding_rates(
        self, 
        symbol: str,
        exchanges: Optional[List[str]] = None
    ) -> FundingRateResponse:
        """
        Get funding rates for a specific symbol across multiple exchanges.
        
        Args:
            symbol: Base symbol (e.g., 'BTC')
            exchanges: List of exchanges to fetch from (default: all supported)
            
        Returns:
            FundingRateResponse with rates from all exchanges
        """
        if symbol not in SUPPORTED_SYMBOLS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Symbol {symbol} not supported. Supported symbols: {SUPPORTED_SYMBOLS}"
            )
        
        # Use all supported exchanges if none specified
        target_exchanges = exchanges or SUPPORTED_EXCHANGES
        
        logger.info(f"Fetching funding rates for {symbol} from exchanges: {target_exchanges}")
        
        # Fetch rates from all exchanges concurrently
        tasks = []
        for exchange_id in target_exchanges:
            # Use exchange-specific symbol format
            if exchange_id in EXCHANGE_SYMBOL_MAPPING and symbol in EXCHANGE_SYMBOL_MAPPING[exchange_id]:
                exchange_symbol = EXCHANGE_SYMBOL_MAPPING[exchange_id][symbol]
            else:
                # Fallback to default format if not specified
                exchange_symbol = f"{symbol}USDT"
            
            tasks.append(self._fetch_exchange_funding_rate(exchange_id, exchange_symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        rates = []
        for result in results:
            if isinstance(result, FundingRateItem):
                rates.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in funding rate fetch: {result}")
        
        return FundingRateResponse(
            symbol=symbol,
            rates=rates,
            last_updated=datetime.utcnow()
        )
    
    async def get_all_funding_rates(
        self,
        symbols: Optional[List[str]] = None,
        exchanges: Optional[List[str]] = None
    ) -> FundingRatesSummaryResponse:
        """
        Get funding rates for all symbols across all exchanges.
        
        Args:
            symbols: List of symbols to fetch (default: all supported)
            exchanges: List of exchanges to fetch from (default: all supported)
            
        Returns:
            FundingRatesSummaryResponse with all rates
        """
        target_symbols = symbols or SUPPORTED_SYMBOLS
        target_exchanges = exchanges or SUPPORTED_EXCHANGES
        
        logger.info(f"Fetching funding rates for symbols: {target_symbols} from exchanges: {target_exchanges}")
        
        # Use batch fetching for Bitunix when available
        if 'bitunix' in target_exchanges:
            logger.info("Using Bitunix batch API for efficient funding rate fetching")
            bitunix_rates = await self._fetch_bitunix_funding_rates_batch()
            
            # Create tasks for other exchanges
            other_exchanges = [ex for ex in target_exchanges if ex != 'bitunix']
            if other_exchanges:
                logger.info(f"Fetching from other exchanges: {other_exchanges}")
                other_tasks = []
                for symbol in target_symbols:
                    for exchange_id in other_exchanges:
                        if exchange_id in EXCHANGE_SYMBOL_MAPPING and symbol in EXCHANGE_SYMBOL_MAPPING[exchange_id]:
                            exchange_symbol = EXCHANGE_SYMBOL_MAPPING[exchange_id][symbol]
                        else:
                            exchange_symbol = f"{symbol}USDT"
                        other_tasks.append(self._fetch_exchange_funding_rate(exchange_id, exchange_symbol))
                
                other_results = await asyncio.gather(*other_tasks, return_exceptions=True)
                
                # Combine Bitunix batch results with other exchange results
                all_results = bitunix_rates + [r for r in other_results if isinstance(r, FundingRateItem)]
            else:
                all_results = bitunix_rates
        else:
            # No Bitunix, use parallel fetching for all exchanges
            logger.info("Using parallel fetching for maximum speed")
            all_tasks = []
            
            for symbol in target_symbols:
                for exchange_id in target_exchanges:
                    if exchange_id in EXCHANGE_SYMBOL_MAPPING and symbol in EXCHANGE_SYMBOL_MAPPING[exchange_id]:
                        exchange_symbol = EXCHANGE_SYMBOL_MAPPING[exchange_id][symbol]
                    else:
                        exchange_symbol = f"{symbol}USDT"
                    all_tasks.append(self._fetch_exchange_funding_rate(exchange_id, exchange_symbol))
            
            logger.info(f"Executing {len(all_tasks)} API calls in parallel")
            all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Group results by symbol
        symbol_rates = {}
        for result in all_results:
            if isinstance(result, FundingRateItem):
                symbol = result.symbol
                if symbol not in symbol_rates:
                    symbol_rates[symbol] = []
                symbol_rates[symbol].append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in funding rate fetch: {result}")
        
        # Convert to expected format
        rates = []
        for symbol in target_symbols:
            # Use standard USDT format for the response
            standard_symbol = f"{symbol}USDT"
            if standard_symbol in symbol_rates:
                rates.append(FundingRateResponse(
                    symbol=standard_symbol,
                    rates=symbol_rates[standard_symbol],
                    last_updated=datetime.utcnow()
                ))
        
        return FundingRatesSummaryResponse(
            symbols=target_symbols,
            exchanges=target_exchanges,
            rates=rates,
            last_updated=datetime.utcnow()
        )
    
    async def get_exchange_funding_rates(
        self,
        exchange_id: str,
        symbols: Optional[List[str]] = None
    ) -> List[FundingRateItem]:
        """
        Get funding rates for all symbols from a specific exchange.
        
        Args:
            exchange_id: Exchange identifier
            symbols: List of symbols to fetch (default: all supported)
            
        Returns:
            List of FundingRateItem for the exchange
        """
        if exchange_id not in SUPPORTED_EXCHANGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exchange {exchange_id} not supported. Supported exchanges: {SUPPORTED_EXCHANGES}"
            )
        
        target_symbols = symbols or SUPPORTED_SYMBOLS
        
        logger.info(f"Fetching funding rates from {exchange_id} for symbols: {target_symbols}")
        
        # Use batch fetching for Bitunix to improve efficiency
        if exchange_id == 'bitunix':
            logger.info("Using Bitunix batch API for efficient funding rate fetching")
            return await self._fetch_bitunix_funding_rates_batch()
        
        # For other exchanges, fetch rates for all symbols individually
        tasks = []
        for symbol in target_symbols:
            # Use exchange-specific symbol format
            if exchange_id in EXCHANGE_SYMBOL_MAPPING and symbol in EXCHANGE_SYMBOL_MAPPING[exchange_id]:
                exchange_symbol = EXCHANGE_SYMBOL_MAPPING[exchange_id][symbol]
            else:
                # Fallback to default format if not specified
                exchange_symbol = f"{symbol}USDT"
            tasks.append(self._fetch_exchange_funding_rate(exchange_id, exchange_symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None results and exceptions
        rates = []
        for result in results:
            if isinstance(result, FundingRateItem):
                rates.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception in exchange funding rate fetch: {result}")
        
        return rates
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Funding Rate Service cleaned up")
