import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
import aiohttp
import math

logger = logging.getLogger(__name__)

def format_price_smart(price: float) -> str:
    """
    Format price with appropriate decimal places based on magnitude.
    For very small prices (< 0.01), show more decimal places.
    For larger prices, show fewer decimal places.
    """
    if price == 0:
        return "0.0000"
    
    if price < 0.0001:
        return f"{price:.8f}"
    elif price < 0.01:
        return f"{price:.6f}"
    elif price < 1:
        return f"{price:.4f}"
    elif price < 10:
        return f"{price:.3f}"
    else:
        return f"{price:.2f}"

class TelegramNotificationService:
    def __init__(self):
        # Reload environment variables
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        logger.info(f"Telegram service initialized - Token: {self.bot_token[:10] if self.bot_token else 'None'}..., Chat ID: {self.chat_id}")
        
        if self.bot_token and self.chat_id:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
        else:
            logger.warning("Telegram bot not configured - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    
    async def send_message(self, message: str) -> bool:
        """Send a message to the configured Telegram chat."""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Telegram message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def fetch_asset_overview_data(self) -> Dict:
        """Fetch real asset overview data from the API using the same logic as Asset Overview page."""
        try:
            # Get API key from environment
            api_key = os.getenv("API_KEY")
            headers = {"X-API-Key": api_key}
            
            # Use local URL for testing
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            async with aiohttp.ClientSession() as session:
                # Fetch Bitunix data using the same endpoint as Asset Overview
                bitunix_url = f"{base_url}/api/v1/spot-trades/backward-analysis"
                async with session.get(bitunix_url, headers=headers) as response:
                    bitunix_data = await response.json() if response.status == 200 else None
                
                # Convert backward-analysis response to asset format for compatibility
                bitunix_assets = []
                if bitunix_data and "assets" in bitunix_data:
                    for asset in bitunix_data["assets"]:
                        # Convert to the format expected by the report generation
                        formatted_asset = {
                            "symbol": asset.get("symbol", ""),
                            "current_balance": asset.get("current_balance", 0),
                            "current_price": asset.get("current_price", 0),
                            "average_entry_price": asset.get("average_entry_price", 0),
                            "unrealized_pnl_percentage": asset.get("unrealized_pnl_percentage", 0),
                            "total_buy_value": asset.get("current_balance", 0) * asset.get("average_entry_price", 0)
                        }
                        bitunix_assets.append(formatted_asset)
                
                return {
                    "bitunix": {"assets": bitunix_assets}
                }
        except Exception as e:
            logger.error(f"Error fetching asset overview data: {e}")
            return {"bitunix": None}
    
    async def fetch_orders_info(self, symbol: str) -> tuple:
        """Fetch current orders count and recent order history for a specific symbol."""
        try:
            # Get API key from environment
            api_key = os.getenv("API_KEY")
            headers = {"X-API-Key": api_key}
            
            # Use local URL for testing
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            async with aiohttp.ClientSession() as session:
                # Fetch all orders and filter by base symbol (same logic as Asset Overview)
                orders_url = f"{base_url}/api/v1/spot-trades/orders"
                async with session.get(orders_url, headers=headers) as response:
                    if response.status == 200:
                        orders_data = await response.json()
                        if isinstance(orders_data, list):
                            # Filter orders by base symbol (same logic as Asset Overview)
                            symbol_orders = []
                            for order in orders_data:
                                order_symbol = order.get('symbol', '')
                                # Extract base symbol from order symbol (e.g., "SUI/USDT" -> "SUI")
                                base_symbol = order_symbol.split('/')[0] if '/' in order_symbol else order_symbol
                                if base_symbol == symbol:
                                    symbol_orders.append(order)
                            
                            # Count current orders (status 1 or 'open' = pending)
                            current_orders = [o for o in symbol_orders if o.get('status') == 1 or o.get('status') == 'open']
                            current_count = len(current_orders)
                            
                            return current_count, ""
                        else:
                            return 0, ""
                    else:
                        return 0, ""
        except Exception as e:
            logger.error(f"Error fetching orders info for {symbol}: {e}")
            return 0, ""
    
    async def fetch_current_orders_count(self, symbol: str) -> int:
        """
        Fetch current orders count for a specific symbol.
        Returns the count of current orders.
        """
        count, _ = await self.fetch_orders_info(symbol)
        return count
    
    async def generate_market_report(self) -> str:
        """Generate a comprehensive market report using real data."""
        try:
            # Fetch real asset overview data
            asset_data = await self.fetch_asset_overview_data()
            
            # Format the report
            report = f"📊 <b>AR Trading Portfolio Report</b>\n\n"
            
            # Initialize overall portfolio variables
            total_invested = 0
            total_current_value = 0
            usdt_balance = 0
            
            # Process Bitunix data
            if asset_data["bitunix"] and "assets" in asset_data["bitunix"]:
                bitunix_assets = asset_data["bitunix"]["assets"]
                
                # Use all assets from backward-analysis (same as Asset Overview)
                filtered_bitunix_assets = bitunix_assets
                
                # Calculate Bitunix portfolio summary (same logic as Asset Overview)
                # Separate USDT from other assets
                usdt_asset = next((asset for asset in filtered_bitunix_assets if asset.get("symbol") == "USDT"), None)
                crypto_assets = [asset for asset in filtered_bitunix_assets if asset.get("symbol") != "USDT" and "(BGet)" not in asset.get("symbol", "")]
                
                # Calculate crypto-only values (excluding USDT and Bitget) - same as Asset Overview
                bitunix_crypto_cost = sum(float(asset.get("total_buy_value", 0)) for asset in crypto_assets if asset.get("total_buy_value") is not None)
                bitunix_crypto_current = sum(float(asset.get("current_balance", 0)) * float(asset.get("current_price", 0)) for asset in crypto_assets if asset.get("current_balance") is not None and asset.get("current_price") is not None)
                bitunix_usdt_balance = float(usdt_asset.get("current_balance", 0)) if usdt_asset else 0
                
                # Total values (crypto + USDT) - same as Asset Overview
                bitunix_total_cost = bitunix_crypto_cost + bitunix_usdt_balance
                bitunix_current_value = bitunix_crypto_current + bitunix_usdt_balance
                bitunix_pnl = bitunix_current_value - bitunix_total_cost
                bitunix_pnl_percentage = (bitunix_pnl / bitunix_total_cost * 100) if bitunix_total_cost > 0 else 0
                
                total_invested += bitunix_total_cost
                total_current_value += bitunix_current_value
                usdt_balance = bitunix_usdt_balance
                
                # Sort assets by current value
                sorted_bitunix_assets = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("current_balance", 0)) * float(x.get("current_price", 0)), reverse=True)
                
                report += f"📋 <b>Top Assets by Value</b>\n"
                for i, asset in enumerate(sorted_bitunix_assets[:5], 1):
                    symbol = asset.get("symbol", "Unknown")
                    current_value = float(asset.get("current_balance", 0)) * float(asset.get("current_price", 0))
                    cost_value = float(asset.get("total_buy_value", 0))
                    pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                    
                    # Remove /USDT from symbols to match the desired format
                    display_symbol = symbol.replace("/USDT", "") if symbol != "USDT" else "USDT"
                    
                    # Skip USDT for orders info
                    if symbol != "USDT":
                        orders_count, _ = await self.fetch_orders_info(display_symbol)
                        report += f"{i}. {display_symbol}: ${cost_value:,.0f} | ${current_value:,.0f} ({pnl_percentage:+.1f}%) | {orders_count} O\n"
                    else:
                        report += f"{i}. {display_symbol}: ${cost_value:,.0f} | ${current_value:,.0f} ({pnl_percentage:+.1f}%)\n"
                
                report += "\n"
                
                # Best and worst performers (fix the logic)
                # best_performers = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("unrealized_pnl_percentage", 0)), reverse=True)[:2]
                # worst_performers = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("unrealized_pnl_percentage", 0)))[:2]
                
                # report += f"🏆 <b>Best Performers</b>\n"
                # for asset in best_performers:
                #     symbol = asset.get("symbol", "Unknown")
                #     pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                #     report += f"• {symbol}: {pnl_percentage:+.2f}%\n"
                
                # report += "\n"
                
                # report += f"⚠️ <b>Worst Performers</b>\n"
                # for asset in worst_performers:
                #     symbol = asset.get("symbol", "Unknown")
                #     pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                #     report += f"• {symbol}: {pnl_percentage:+.2f}%\n"
                
                # report += "\n"
                
                # Asset details
                report += f"📊 <b>Asset Details</b>\n"
                for asset in sorted_bitunix_assets:
                    symbol = asset.get("symbol", "Unknown")
                    balance = float(asset.get("current_balance", 0))
                    avg_entry = float(asset.get("average_entry_price", 0))
                    current_price = float(asset.get("current_price", 0))
                    
                    # Remove /USDT from symbols to match the desired format
                    display_symbol = symbol.replace("/USDT", "") if symbol != "USDT" else "USDT"
                    
                    # Format balance - no decimals for values over 1M
                    balance_formatted = f"{balance:,.0f}" if balance >= 1000000 else f"{balance:,.2f}"
                    report += f"• {display_symbol}: {balance_formatted} @ ${format_price_smart(avg_entry)} → ${format_price_smart(current_price)}\n"
            else:
                report += f"📈 <b>Bitunix Portfolio</b>\n"
                report += f"No data available.\n\n"
            
            
            # Overall portfolio summary
            if total_invested > 0:
                
                # Calculate P&L without USDT (crypto only)
                total_crypto_cost = total_invested - usdt_balance
                total_crypto_current = total_current_value - usdt_balance
                total_pnl_without_usdt = total_crypto_current - total_crypto_cost
                total_pnl_percentage_without_usdt = (total_pnl_without_usdt / total_crypto_cost * 100) if total_crypto_cost > 0 else 0
                
                # Calculate total P&L (including USDT)
                total_pnl = total_current_value - total_invested
                total_pnl_percentage = (total_pnl / total_invested * 100)
                
                report += "\n"
                report += f"💰 <b>Overall Portfolio Summary</b>\n"
                report += f"• Total + USDT: ${total_invested:,.2f}\n"
                report += f"• Current + USDT: ${total_current_value:,.2f} | ${total_pnl:,.2f} ({total_pnl_percentage:+.2f}%)\n"
                report += f"\nTotal Cost: ${total_crypto_cost:,.2f}\n"
                report += f"Cost + P&L: ${total_crypto_current:,.2f} | ${total_pnl_without_usdt:,.2f} ({total_pnl_percentage_without_usdt:+.2f}%)"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating market report: {e}")
            return f"❌ <b>Error generating report</b>\n{str(e)}"
    
    async def send_scheduled_report(self):
        """Send the scheduled market report."""
        report = await self.generate_market_report()
        await self.send_message(report)
    
    def start_scheduler(self, interval_hours: int = 3):
        """Start the scheduler to send periodic reports."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Add job to send reports every interval_hours
            self.scheduler.add_job(
                func=self.send_scheduled_report,
                trigger=IntervalTrigger(hours=interval_hours),
                id='market_report',
                name='Market Report Scheduler',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Telegram scheduler started with {interval_hours} hour intervals")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Telegram scheduler stopped")
        else:
            logger.warning("Scheduler is not running")
    
    async def send_test_message(self) -> bool:
        """Send a test message to verify bot configuration."""
        test_message = f"🤖 <b>AR Trading Bot Test</b>\n"
        test_message += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        test_message += f"✅ Bot is working correctly!"
        
        return await self.send_message(test_message)
    
    async def send_test_report_with_orders(self) -> bool:
        """Send a test report to verify the orders count functionality."""
        try:
            # Test orders count for a specific symbol
            test_symbol = "SUI/USDT"
            orders_count = await self.fetch_current_orders_count(test_symbol)
            
            test_message = f"🧪 <b>Orders Count Test</b>\n"
            test_message += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            test_message += f"📊 Testing orders count for {test_symbol}\n"
            test_message += f"📋 Current Orders: {orders_count}\n"
            test_message += f"✅ Orders count functionality working!"
            
            return await self.send_message(test_message)
        except Exception as e:
            logger.error(f"Error in test report: {e}")
            return False

# Global instance
telegram_service = TelegramNotificationService() 