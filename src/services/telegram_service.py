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

logger = logging.getLogger(__name__)

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
        """Fetch real asset overview data from the API."""
        try:
            # Get API key from environment
            api_key = os.getenv("API_KEY", "vZgz1jBWa_FmmEazZp722avXKjNIkjUufKXadoKACrk")
            headers = {"X-API-Key": api_key}
            
            async with aiohttp.ClientSession() as session:
                # Fetch Bitunix data
                bitunix_url = "http://localhost:8000/api/v1/spot-trades/backward-analysis"
                async with session.get(bitunix_url, headers=headers) as response:
                    bitunix_data = await response.json() if response.status == 200 else None
                
                # Fetch Bitget data
                bitget_url = "http://localhost:8000/api/v1/bitget/backward-analysis?symbol=HYPE/USDT"
                async with session.get(bitget_url, headers=headers) as response:
                    bitget_data = await response.json() if response.status == 200 else None
                
                return {
                    "bitunix": bitunix_data,
                    "bitget": bitget_data
                }
        except Exception as e:
            logger.error(f"Error fetching asset overview data: {e}")
            return {"bitunix": None, "bitget": None}
    
    async def generate_market_report(self) -> str:
        """Generate a comprehensive market report using real data."""
        try:
            # Fetch real asset overview data
            asset_data = await self.fetch_asset_overview_data()
            
            # Format the report
            report = f"📊 <b>AR Trading Portfolio Report</b>\n"
            report += f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            # Initialize overall portfolio variables
            total_invested = 0
            total_current_value = 0
            
            # Process Bitunix data
            if asset_data["bitunix"] and "assets" in asset_data["bitunix"]:
                bitunix_assets = asset_data["bitunix"]["assets"]
                
                # Filter out USDT if value is below $10
                filtered_bitunix_assets = []
                for asset in bitunix_assets:
                    current_value = float(asset.get("current_balance", 0)) * float(asset.get("current_price", 0))
                    if asset.get("symbol") == "USDT" and current_value < 10:
                        continue
                    filtered_bitunix_assets.append(asset)
                
                # Calculate Bitunix portfolio summary
                bitunix_total_cost = sum(float(asset.get("total_buy_value", 0)) for asset in filtered_bitunix_assets)
                bitunix_current_value = sum(float(asset.get("current_balance", 0)) * float(asset.get("current_price", 0)) for asset in filtered_bitunix_assets)
                bitunix_pnl = bitunix_current_value - bitunix_total_cost
                bitunix_pnl_percentage = (bitunix_pnl / bitunix_total_cost * 100) if bitunix_total_cost > 0 else 0
                
                total_invested += bitunix_total_cost
                total_current_value += bitunix_current_value
                
                report += f"🔵 <b>Bitunix Portfolio</b>\n"
                report += f"• Total Cost: ${bitunix_total_cost:,.2f}\n"
                report += f"• Current Value: ${bitunix_current_value:,.2f}\n"
                report += f"• P&L: ${bitunix_pnl:,.2f} ({bitunix_pnl_percentage:+.2f}%)\n\n"
                
                # Sort assets by current value
                sorted_bitunix_assets = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("current_balance", 0)) * float(x.get("current_price", 0)), reverse=True)
                
                report += f"📋 <b>Top Assets by Value</b>\n"
                for i, asset in enumerate(sorted_bitunix_assets[:5], 1):
                    symbol = asset.get("symbol", "Unknown")
                    current_value = float(asset.get("current_balance", 0)) * float(asset.get("current_price", 0))
                    pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                    report += f"{i}. {symbol}: ${current_value:,.2f} ({pnl_percentage:+.2f}%)\n"
                
                report += "\n"
                
                # Best and worst performers (fix the logic)
                best_performers = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("unrealized_pnl_percentage", 0)), reverse=True)[:2]
                worst_performers = sorted(filtered_bitunix_assets, key=lambda x: float(x.get("unrealized_pnl_percentage", 0)))[:2]
                
                report += f"🏆 <b>Best Performers</b>\n"
                for asset in best_performers:
                    symbol = asset.get("symbol", "Unknown")
                    pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                    report += f"• {symbol}: {pnl_percentage:+.2f}%\n"
                
                report += "\n"
                
                report += f"⚠️ <b>Worst Performers</b>\n"
                for asset in worst_performers:
                    symbol = asset.get("symbol", "Unknown")
                    pnl_percentage = float(asset.get("unrealized_pnl_percentage", 0))
                    report += f"• {symbol}: {pnl_percentage:+.2f}%\n"
                
                report += "\n"
                
                # Asset details
                report += f"📊 <b>Asset Details</b>\n"
                for asset in sorted_bitunix_assets:
                    symbol = asset.get("symbol", "Unknown")
                    balance = float(asset.get("current_balance", 0))
                    avg_entry = float(asset.get("average_entry_price", 0))
                    current_price = float(asset.get("current_price", 0))
                    report += f"• {symbol}: {balance:,.2f} @ ${avg_entry:.4f} → ${current_price:.4f}\n"
            else:
                report += f"📈 <b>Bitunix Portfolio</b>\n"
                report += f"No data available.\n\n"
            
            # Process Bitget data if available
            if asset_data["bitget"] and asset_data["bitget"].get("symbol"):
                # Bitget returns a single asset object, not an array
                bitget_asset = asset_data["bitget"]
                
                # Calculate Bitget portfolio summary
                bitget_total_cost = float(bitget_asset.get("total_buy_cost", 0))
                bitget_current_value = float(bitget_asset.get("current_value", 0))
                bitget_pnl = bitget_current_value - bitget_total_cost
                bitget_pnl_percentage = (bitget_pnl / bitget_total_cost * 100) if bitget_total_cost > 0 else 0
                
                total_invested += bitget_total_cost
                total_current_value += bitget_current_value
                
                report += f"\n🔴 <b>Bitget Portfolio</b>\n"
                report += f"• Total Cost: ${bitget_total_cost:,.2f}\n"
                report += f"• Current Value: ${bitget_current_value:,.2f}\n"
                report += f"• P&L: ${bitget_pnl:,.2f} ({bitget_pnl_percentage:+.2f}%)\n\n"
                
                # Add Bitget asset to the asset details
                symbol = bitget_asset.get("symbol", "Unknown")
                balance = float(bitget_asset.get("current_balance", 0))
                avg_entry = float(bitget_asset.get("average_entry_price", 0))
                current_price = float(bitget_asset.get("current_price", 0))
                report += f"• {symbol}: {balance:,.2f} @ ${avg_entry:.4f} → ${current_price:.4f}\n"
            
            # Overall portfolio summary
            if total_invested > 0:
                total_pnl = total_current_value - total_invested
                total_pnl_percentage = (total_pnl / total_invested * 100)
                
                report += "\n"
                report += f"💰 <b>Overall Portfolio Summary</b>\n"
                report += f"• Total Invested: ${total_invested:,.2f}\n"
                report += f"• Current Value: ${total_current_value:,.2f}\n"
                report += f"• Total P&L: ${total_pnl:,.2f} ({total_pnl_percentage:+.2f}%)\n"
            
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

# Global instance
telegram_service = TelegramNotificationService() 