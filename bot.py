#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚗 Professional Vehicle RC Information Bot
A comprehensive Telegram bot for vehicle registration lookup with advanced features

Author: RC Info Bot Team
Version: 3.0.0
License: MIT
"""

import logging
import requests
import json
import time
import sqlite3
import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "8229904939:AAEUG82rLWg2dPq0LCZFzx-gmuPIjJAE38w)
API_BASE = "https://vvvin-ng.vercel.app/lookup?rc="
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else [8284333794]
DATABASE_FILE = "vehicle_intel.db"
MAX_QUERIES_PER_DAY = int(os.getenv("MAX_QUERIES_PER_DAY", "10"))
CACHE_EXPIRY_HOURS = 24

# Enable comprehensive logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_RC, BATCH_MODE, WAITING_FEEDBACK = range(3)

# RC Number validation pattern
RC_PATTERN = re.compile(r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$')

class VehicleIntelBot:
    """Professional Vehicle Intelligence Bot with advanced features"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.init_database()
        logger.info("✅ Vehicle Intelligence Bot initialized successfully")

    def init_database(self):
        """Initialize comprehensive SQLite database schema"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Users table with detailed tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                queries_count INTEGER DEFAULT 0,
                queries_today INTEGER DEFAULT 0,
                last_query_date DATE,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_premium BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0
            )
        ''')
        
        # Queries history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rc_number TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Cache table for API responses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                rc_number TEXT PRIMARY KEY,
                response_data TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hits INTEGER DEFAULT 0
            )
        ''')
        
        # Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("📊 Database initialized successfully")

    def log_user_activity(self, user_id: int, username: str, first_name: str, last_name: str) -> None:
        """Log user activity with daily quota management"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check if it's a new day for this user
        cursor.execute('SELECT last_query_date FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        today = datetime.now().date()
        reset_daily = False
        
        if result:
            last_date = datetime.strptime(result[0], '%Y-%m-%d').date() if result[0] else None
            if last_date != today:
                reset_daily = True
        
        # Update or insert user
        cursor.execute('''
            INSERT INTO users 
            (user_id, username, first_name, last_name, queries_count, queries_today, last_query_date, last_seen)
            VALUES (?, ?, ?, ?, 1, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                queries_count = queries_count + 1,
                queries_today = CASE WHEN ? THEN 1 ELSE queries_today + 1 END,
                last_query_date = excluded.last_query_date,
                last_seen = CURRENT_TIMESTAMP
        ''', (user_id, username, first_name, last_name, today, reset_daily))
        
        conn.commit()
        conn.close()

    def check_user_quota(self, user_id: int) -> tuple[bool, int]:
        """Check if user has remaining quota for today"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT queries_today, is_premium, is_banned 
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True, MAX_QUERIES_PER_DAY
        
        queries_today, is_premium, is_banned = result
        
        if is_banned:
            return False, 0
        
        # Premium users have unlimited queries
        if is_premium:
            return True, -1
        
        remaining = MAX_QUERIES_PER_DAY - queries_today
        return remaining > 0, remaining

    def log_query(self, user_id: int, rc_number: str, success: bool, error_message: str = None) -> None:
        """Log individual query with error tracking"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO queries (user_id, rc_number, success, error_message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, rc_number.upper(), success, error_message))
        
        conn.commit()
        conn.close()

    def cache_response(self, rc_number: str, response_data: Dict[str, Any]) -> None:
        """Cache API response for faster subsequent queries"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache (rc_number, response_data, cached_at, hits)
            VALUES (?, ?, CURRENT_TIMESTAMP, 
                COALESCE((SELECT hits FROM cache WHERE rc_number = ?), 0) + 1)
        ''', (rc_number.upper(), json.dumps(response_data), rc_number.upper()))
        
        conn.commit()
        conn.close()

    def get_cached_response(self, rc_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available and not expired"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT response_data, cached_at FROM cache 
            WHERE rc_number = ?
        ''', (rc_number.upper(),))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        cached_data, cached_at = result
        cached_time = datetime.strptime(cached_at, '%Y-%m-%d %H:%M:%S')
        
        # Check if cache is still valid
        if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRY_HOURS):
            return None
        
        return json.loads(cached_data)

    def validate_rc_number(self, rc_number: str) -> bool:
        """Validate RC number format"""
        rc_clean = rc_number.strip().upper().replace(" ", "").replace("-", "")
        return bool(RC_PATTERN.match(rc_clean))

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a user"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT queries_count, queries_today, first_seen, last_seen, is_premium
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return None
        
        queries_count, queries_today, first_seen, last_seen, is_premium = result
        
        # Get recent queries
        cursor.execute('''
            SELECT rc_number, timestamp, success 
            FROM queries 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''', (user_id,))
        
        recent_queries = cursor.fetchall()
        conn.close()
        
        return {
            "total_queries": queries_count,
            "queries_today": queries_today,
            "remaining_today": -1 if is_premium else max(0, MAX_QUERIES_PER_DAY - queries_today),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "is_premium": is_premium,
            "recent_queries": recent_queries
        }

    def get_admin_stats(self) -> Dict[str, Any]:
        """Get comprehensive admin statistics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Total queries
        cursor.execute('SELECT COUNT(*) FROM queries')
        total_queries = cursor.fetchone()[0]
        
        # Successful queries
        cursor.execute('SELECT COUNT(*) FROM queries WHERE success = 1')
        successful_queries = cursor.fetchone()[0]
        
        # Queries today
        cursor.execute('''
            SELECT COUNT(*) FROM queries 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        queries_today = cursor.fetchone()[0]
        
        # Active users today
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM queries 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        active_today = cursor.fetchone()[0]
        
        # Top 5 users
        cursor.execute('''
            SELECT user_id, username, queries_count 
            FROM users 
            ORDER BY queries_count DESC 
            LIMIT 5
        ''')
        top_users = cursor.fetchall()
        
        # Most queried RCs
        cursor.execute('''
            SELECT rc_number, COUNT(*) as count 
            FROM queries 
            GROUP BY rc_number 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_rcs = cursor.fetchall()
        
        # Cache stats
        cursor.execute('SELECT COUNT(*) FROM cache')
        cache_size = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "queries_today": queries_today,
            "active_today": active_today,
            "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
            "top_users": top_users,
            "top_rcs": top_rcs,
            "cache_size": cache_size
        }

    def save_feedback(self, user_id: int, message: str) -> None:
        """Save user feedback"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (user_id, message)
            VALUES (?, ?)
        ''', (user_id, message))
        
        conn.commit()
        conn.close()

    def get_feedback_list(self) -> List[tuple]:
        """Get recent feedback for admins"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.id, f.user_id, u.username, f.message, f.timestamp
            FROM feedback f
            LEFT JOIN users u ON f.user_id = u.user_id
            ORDER BY f.timestamp DESC
            LIMIT 10
        ''')
        
        feedback = cursor.fetchall()
        conn.close()
        
        return feedback

    async def query_rc_api(self, rc_number: str, use_cache: bool = True) -> Dict[str, Any]:
        """Enhanced API query with caching, retry logic and comprehensive error handling"""
        rc_clean = rc_number.strip().upper().replace(" ", "").replace("-", "")
        
        # Validate RC format
        if not self.validate_rc_number(rc_clean):
            return {"error": "Invalid RC number format. Example: MH12DE1433"}
        
        # Check cache first
        if use_cache:
            cached = self.get_cached_response(rc_clean)
            if cached:
                logger.info(f"✅ Cache hit for {rc_clean}")
                cached['from_cache'] = True
                return cached
        
        # Query API with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{API_BASE}{rc_clean}"
                logger.info(f"🔍 Querying API: {url} (Attempt {attempt + 1}/{max_retries})")
                
                response = self.session.get(url, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if API returned error
                    if isinstance(data, dict) and data.get('error'):
                        return {"error": data.get('error')}
                    
                    # Parse and cache the response
                    parsed_data = self.parse_intel_data(data, rc_clean)
                    if 'error' not in parsed_data:
                        self.cache_response(rc_clean, parsed_data)
                    
                    return parsed_data
                    
                elif response.status_code == 404:
                    return {"error": "❌ Vehicle not found in database"}
                elif response.status_code == 429:
                    return {"error": "⚠️ Rate limit exceeded. Please try again later"}
                else:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return {"error": f"API Error: HTTP {response.status_code}"}
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"⏱️ Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                return {"error": "⏱️ Request timeout - API is unresponsive"}
                
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": "🌐 Connection error - Please check your internet"}
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {str(e)}")
                return {"error": f"System error: {str(e)}"}
        
        return {"error": "Failed to fetch data after multiple attempts"}

    def parse_intel_data(self, data: Any, rc_number: str) -> Dict[str, Any]:
        """Parse and structure comprehensive intelligence data from API"""
        if not isinstance(data, dict):
            return {"error": "Invalid API response format"}
        
        # Create comprehensive intelligence report with all API fields
        intel_report = {
            "metadata": {
                "target": rc_number,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_confidence": "HIGH",
                "from_cache": False
            },
            
            # 🚗 Ownership Details
            "ownership": {
                "😀 Owner Name": data.get("Owner Name", "N/A"),
                "👨‍👨‍👦‍👦 Father's Name": data.get("Father's Name", "N/A"),
                "🔢 Owner Serial No": data.get("Owner Serial No", "N/A"),
                "🪪 Registration Number": data.get("Registration Number", rc_number)
            },
            
            # 🏢 Registered RTO
            "rto": {
                "🏢 Registered RTO": data.get("Registered RTO", "N/A")
            },
            
            # 🧰 Vehicle Details
            "vehicle": {
                "🚘 Model Name": data.get("Model Name", "N/A"),
                "🏭 Maker Model": data.get("Maker Model", "N/A"),
                "💎 Vehicle Class": data.get("Vehicle Class", "N/A"),
                "🧤 Fuel Type": data.get("Fuel Type", "N/A"),
                "☃️ Fuel Norms": data.get("Fuel Norms", "N/A"),
                "🔩 Chassis Number": data.get("Chassis Number", "N/A"),
                "🧠 Engine Number": data.get("Engine Number", "N/A"),
                "⚙️ Cubic Capacity": data.get("Cubic Capacity", "N/A"),
                "👥 Seating Capacity": data.get("Seating Capacity", "N/A")
            },
            
            # 📄 Insurance Information
            "insurance": {
                "🧝 Insurance Expiry": data.get("Insurance Expiry", "N/A"),
                "🔖 Insurance No": data.get("Insurance No", "N/A"),
                "🏢 Insurance Company": data.get("Insurance Company", "N/A"),
                "🎶 Insurance Upto": data.get("Insurance Upto", "N/A"),
                "🚫 Insurance Expiry In": data.get("Insurance Expiry In", "N/A"),
                "⏱ Insurance Alert": data.get("Insurance Alert", "N/A"),
                "🗓️ Expired Days": data.get("Expired Days", "N/A")
            },
            
            # 🗓 Important Dates & Validity
            "dates": {
                "👑 Registration Date": data.get("Registration Date", "N/A"),
                "⏳ Vehicle Age": data.get("Vehicle Age", "N/A"),
                "🧾 Fitness Upto": data.get("Fitness Upto", "N/A"),
                "😀 Tax Upto": data.get("Tax Upto", "N/A"),
                "🧧 PUC No": data.get("PUC No", "N/A"),
                "🗓️ PUC Upto": data.get("PUC Upto", "N/A"),
                "⚡️ PUC Expiry In": data.get("PUC Expiry In", "N/A")
            },
            
            # 🛍 Other Information
            "other": {
                "😀 Financer Name": data.get("Financer Name", "N/A"),
                "🪪 Permit Type": data.get("Permit Type", "N/A"),
                "🚫 Blacklist Status": data.get("Blacklist Status", "N/A")
            },
            
            # 📁 NOC Details
            "noc": {
                "NOC Details": data.get("NOC Details", "N/A")
            },
            
            # 🪪 Basic Card Info
            "card_info": {
                "🚗 Modal Name": data.get("Modal Name", "N/A"),
                "😀 Owner Name": data.get("Owner Name", "N/A"),
                "🛡 Code": data.get("Code", "N/A"),
                "📍 City Name": data.get("City Name", "N/A"),
                "🛩 Phone": data.get("Phone", "N/A"),
                "🌐 Website": data.get("Website", "N/A"),
                "😀 Address": data.get("Address", "N/A")
            },
            
            # Raw data for reference
            "raw_data": data
        }
        
        return intel_report

    def format_intel_message(self, report: Dict[str, Any]) -> str:
        """Format comprehensive intelligence report for Telegram with all fields"""
        if "error" in report:
            return f"❌ *QUERY FAILED*\n\n{report['error']}\n\n💡 _Tip: Make sure the RC number is correct_"
        
        meta = report["metadata"]
        from_cache = " (Cached)" if meta.get("from_cache") else ""
        
        message = "╔══════════════════════════════╗\n"
        message += "║  🚗 *RC INFORMATION REPORT*  ║\n"
        message += "╚══════════════════════════════╝\n\n"
        
        # Metadata
        message += f"🎯 *Target:* `{meta['target']}`{from_cache}\n"
        message += f"🕐 *Generated:* {meta['timestamp']}\n"
        message += f"📊 *Confidence:* {meta['data_confidence']}\n"
        message += "═" * 35 + "\n\n"
        
        # 🚗 Ownership Details
        message += "🚗 *OWNERSHIP DETAILS*\n"
        message += "─" * 35 + "\n"
        for key, value in report["ownership"].items():
            if value and value != "N/A":
                message += f"{key}: `{value}`\n"
        
        # 🏢 RTO Information
        if report["rto"].get("🏢 Registered RTO", "N/A") != "N/A":
            message += "\n🏢 *RTO INFORMATION*\n"
            message += "─" * 35 + "\n"
            for key, value in report["rto"].items():
                if value and value != "N/A":
                    message += f"{key}: `{value}`\n"
        
        # 🧰 Vehicle Details
        message += "\n🧰 *VEHICLE DETAILS*\n"
        message += "─" * 35 + "\n"
        for key, value in report["vehicle"].items():
            if value and value != "N/A":
                message += f"{key}: `{value}`\n"
        
        # 📄 Insurance Information
        message += "\n📄 *INSURANCE INFORMATION*\n"
        message += "─" * 35 + "\n"
        has_insurance_data = False
        for key, value in report["insurance"].items():
            if value and value != "N/A":
                has_insurance_data = True
                message += f"{key}: `{value}`\n"
        
        if not has_insurance_data:
            message += "⚠️ _No insurance information available_\n"
        
        # Check for expired insurance warning
        insurance_expiry = report["insurance"].get("🚫 Insurance Expiry In", "N/A")
        if "expired" in str(insurance_expiry).lower() or "overdue" in str(insurance_expiry).lower():
            message += "\n⚠️ *WARNING:* Insurance has expired! Renew immediately.\n"
        
        # 🗓 Important Dates & Validity
        message += "\n🗓 *IMPORTANT DATES & VALIDITY*\n"
        message += "─" * 35 + "\n"
        for key, value in report["dates"].items():
            if value and value != "N/A":
                message += f"{key}: `{value}`\n"
        
        # 🛍 Other Information
        message += "\n🛍 *OTHER INFORMATION*\n"
        message += "─" * 35 + "\n"
        has_other_data = False
        for key, value in report["other"].items():
            if value and value != "N/A":
                has_other_data = True
                message += f"{key}: `{value}`\n"
        
        if not has_other_data:
            message += "_No additional information_\n"
        
        # 📁 NOC Details
        noc_details = report["noc"].get("NOC Details", "N/A")
        if noc_details and noc_details != "N/A":
            message += "\n📁 *NOC DETAILS*\n"
            message += "─" * 35 + "\n"
            message += f"NOC Details: `{noc_details}`\n"
        
        # 🪪 Basic Card Info (if different from main data)
        message += "\n🪪 *BASIC CARD INFO*\n"
        message += "─" * 35 + "\n"
        has_card_data = False
        for key, value in report["card_info"].items():
            if value and value != "N/A" and key not in ["😀 Owner Name"]:
                has_card_data = True
                message += f"{key}: `{value}`\n"
        
        if not has_card_data:
            message += "_No additional card information_\n"
        
        # 🚨 Security Alerts (Blacklist status)
        blacklist = report["other"].get("🚫 Blacklist Status", "N/A")
        if blacklist and blacklist != "N/A" and blacklist.lower() != "no":
            message += "\n🚨 *SECURITY ALERT*\n"
            message += "─" * 35 + "\n"
            message += f"⚠️ *Blacklist Status:* `{blacklist}`\n"
        
        message += "\n" + "═" * 35 + "\n"
        message += "🚀 *Made by RC Info Bot*\n"
        message += "📱 _Powered by VVVin API_\n"
        
        return message

# ===== TELEGRAM BOT HANDLERS =====
bot_instance = VehicleIntelBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command with enhanced welcome message"""
    user = update.effective_user
    
    welcome_text = f"""
╔═══════════════════════════════════╗
║   🚗 *RC INFO BOT v3.0* 🚗   ║
╚═══════════════════════════════════╝

Welcome *{user.first_name}*! 👋

🔥 *FEATURES:*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 *Comprehensive RC Lookup*
   • Complete vehicle details
   • Owner information
   • Insurance & PUC status
   • Tax & fitness validity
   • Blacklist checking

📊 *Advanced Features*
   • Batch processing support
   • Smart caching system
   • Usage statistics
   • Export reports (coming soon)

💎 *Premium Features*
   • Unlimited queries
   • Priority support
   • Advanced analytics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *QUICK START:*
1️⃣ Click "🔍 Lookup Vehicle" below
2️⃣ Send RC number (e.g., MH12DE1433)
3️⃣ Get instant detailed report!

⚡ Daily Limit: {MAX_QUERIES_PER_DAY} free queries

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ *DISCLAIMER*
This bot is for educational and informational purposes only. Users are responsible for their actions. We do not promote illegal activities.

🚀 *Made with ❤️ by RC Info Bot Team*
📱 Powered by VVVin API
"""
    
    keyboard = [
        [InlineKeyboardButton("🔍 Lookup Vehicle", callback_data="single_lookup")],
        [InlineKeyboardButton("📊 Batch Process", callback_data="batch_mode")],
        [InlineKeyboardButton("📈 My Stats", callback_data="user_stats"),
         InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("💬 Feedback", callback_data="feedback")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    help_text = """
📚 *HOW TO USE RC INFO BOT*

🔍 *SINGLE LOOKUP*
━━━━━━━━━━━━━━━━━━━━━━━━━
1. Send /lookup or click "🔍 Lookup Vehicle"
2. Enter RC number (e.g., MH12DE1433)
3. Receive detailed report instantly

Valid RC formats:
• MH12DE1433
• DL9CAB1234
• KA01AB1234

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 *BATCH PROCESSING*
━━━━━━━━━━━━━━━━━━━━━━━━━
1. Send /batch or click "📊 Batch Process"
2. Enter multiple RC numbers separated by:
   - Commas: MH12DE1433, DL9CAB1234
   - New lines
3. Get all reports together

━━━━━━━━━━━━━━━━━━━━━━━━━

📈 *VIEW STATISTICS*
Send /stats to see:
• Total queries made
• Queries today
• Remaining daily quota
• Recent search history

━━━━━━━━━━━━━━━━━━━━━━━━━

💬 *SEND FEEDBACK*
Send /feedback to share:
• Bug reports
• Feature requests
• General feedback

━━━━━━━━━━━━━━━━━━━━━━━━━

👑 *ADMIN COMMANDS* (Admins only)
/admin - Admin dashboard
/broadcast - Send message to all users

━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ Need help? Contact support!
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /lookup command with quota checking"""
    user = update.effective_user
    user_id = user.id
    
    # Check user quota
    has_quota, remaining = bot_instance.check_user_quota(user_id)
    
    if not has_quota:
        await update.message.reply_text(
            "⚠️ *DAILY LIMIT REACHED*\n\n"
            f"You've used all {MAX_QUERIES_PER_DAY} free queries for today.\n\n"
            "💎 Upgrade to Premium for unlimited queries!\n"
            "Contact admin for more information.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    quota_text = f"Remaining today: {remaining}" if remaining >= 0 else "Unlimited"
    
    await update.message.reply_text(
        f"🎯 *SINGLE VEHICLE LOOKUP*\n\n"
        f"Enter the RC number to search:\n"
        f"📋 Examples:\n"
        f"  • MH12DE1433\n"
        f"  • DL9CAB1234\n"
        f"  • KA01AB1234\n\n"
        f"⚡ {quota_text}",
        parse_mode='Markdown'
    )
    return WAITING_RC

async def handle_rc_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle RC number input with comprehensive validation and processing"""
    rc_number = update.message.text.strip().upper().replace(" ", "").replace("-", "")
    user = update.effective_user
    user_id = user.id
    
    # Log user activity
    bot_instance.log_user_activity(user_id, user.username, user.first_name, user.last_name)
    
    # Check quota again
    has_quota, remaining = bot_instance.check_user_quota(user_id)
    if not has_quota:
        await update.message.reply_text(
            "⚠️ Daily limit reached! Please try again tomorrow or upgrade to Premium.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Validate RC number format
    if not bot_instance.validate_rc_number(rc_number):
        await update.message.reply_text(
            "❌ *Invalid RC Number Format*\n\n"
            "Please enter a valid Indian vehicle RC number.\n\n"
            "📋 Valid formats:\n"
            "  • MH12DE1433\n"
            "  • DL9CAB1234\n"
            "  • KA01AB1234\n\n"
            "Try again or send /cancel to exit.",
            parse_mode='Markdown'
        )
        return WAITING_RC
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔍 *PROCESSING REQUEST*\n\n"
        f"📍 Target: `{rc_number}`\n"
        f"⏳ Fetching data from database...\n"
        f"⚡ This may take 10-20 seconds",
        parse_mode='Markdown'
    )
    
    try:
        # Query API
        intel_report = await bot_instance.query_rc_api(rc_number)
        
        # Log the query
        success = "error" not in intel_report
        error_msg = intel_report.get('error') if not success else None
        bot_instance.log_query(user_id, rc_number, success, error_msg)
        
        # Format and send response
        response_text = bot_instance.format_intel_message(intel_report)
        
        # Split message if too long (Telegram limit is 4096 characters)
        if len(response_text) > 4000:
            # Send in parts
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            await processing_msg.delete()
            for i, part in enumerate(parts):
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            # Edit original message with results
            await processing_msg.edit_text(
                response_text,
                parse_mode='Markdown'
            )
        
        # Send action buttons
        keyboard = [
            [InlineKeyboardButton("🔍 Lookup Another", callback_data="single_lookup")],
            [InlineKeyboardButton("◀️ Main Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error processing RC {rc_number}: {str(e)}")
        await processing_msg.edit_text(
            f"❌ *ERROR*\n\nFailed to process request: {str(e)}\n\n"
            f"Please try again or contact support.",
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END

async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /batch command"""
    user = update.effective_user
    user_id = user.id
    
    # Check quota
    has_quota, remaining = bot_instance.check_user_quota(user_id)
    
    if not has_quota:
        await update.message.reply_text(
            "⚠️ Daily limit reached! Cannot process batch requests.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📊 *BATCH PROCESSING MODE*\n\n"
        "Send multiple RC numbers in one of these formats:\n\n"
        "1️⃣ Comma-separated:\n"
        "`MH12DE1433, DL9CAB1234, KA01AB1234`\n\n"
        "2️⃣ Line-separated:\n"
        "`MH12DE1433`\n"
        "`DL9CAB1234`\n"
        "`KA01AB1234`\n\n"
        f"⚡ Remaining quota: {remaining if remaining >= 0 else 'Unlimited'}\n"
        f"📝 Max {min(10, remaining if remaining >= 0 else 10)} vehicles per batch",
        parse_mode='Markdown'
    )
    return BATCH_MODE

async def handle_batch_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle batch RC number input"""
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    
    # Parse RC numbers
    rc_numbers = []
    
    # Try comma-separated
    if ',' in text:
        rc_numbers = [rc.strip().upper().replace(" ", "").replace("-", "") for rc in text.split(',')]
    # Try line-separated
    elif '\n' in text:
        rc_numbers = [rc.strip().upper().replace(" ", "").replace("-", "") for rc in text.split('\n')]
    else:
        rc_numbers = [text.upper().replace(" ", "").replace("-", "")]
    
    # Remove empty entries
    rc_numbers = [rc for rc in rc_numbers if rc]
    
    if not rc_numbers:
        await update.message.reply_text("❌ No valid RC numbers found. Please try again.")
        return BATCH_MODE
    
    # Check quota
    has_quota, remaining = bot_instance.check_user_quota(user_id)
    max_batch = min(10, remaining if remaining >= 0 else 10)
    
    if len(rc_numbers) > max_batch:
        await update.message.reply_text(
            f"⚠️ Too many RC numbers! You can process maximum {max_batch} at once.\n"
            f"Remaining quota: {remaining if remaining >= 0 else 'Unlimited'}",
            parse_mode='Markdown'
        )
        return BATCH_MODE
    
    # Process batch
    processing_msg = await update.message.reply_text(
        f"📊 *BATCH PROCESSING*\n\n"
        f"Processing {len(rc_numbers)} vehicle(s)...\n"
        f"⏳ This may take a while...",
        parse_mode='Markdown'
    )
    
    results = []
    for i, rc in enumerate(rc_numbers, 1):
        # Update progress
        if i % 2 == 0:
            await processing_msg.edit_text(
                f"📊 *BATCH PROCESSING*\n\n"
                f"Progress: {i}/{len(rc_numbers)}\n"
                f"⏳ Processing...",
                parse_mode='Markdown'
            )
        
        # Validate format
        if not bot_instance.validate_rc_number(rc):
            results.append(f"❌ {rc}: Invalid format")
            continue
        
        # Query API
        intel_report = await bot_instance.query_rc_api(rc)
        success = "error" not in intel_report
        bot_instance.log_query(user_id, rc, success, intel_report.get('error'))
        bot_instance.log_user_activity(user_id, user.username, user.first_name, user.last_name)
        
        if success:
            owner = intel_report['ownership'].get('😀 Owner Name', 'N/A')
            model = intel_report['vehicle'].get('🚘 Model Name', 'N/A')
            results.append(f"✅ {rc}: {owner} - {model}")
        else:
            error = intel_report.get('error', 'Unknown error')
            results.append(f"❌ {rc}: {error}")
        
        # Small delay to avoid rate limiting
        if i < len(rc_numbers):
            await asyncio.sleep(2)
    
    # Send summary
    summary = "📊 *BATCH PROCESSING COMPLETE*\n\n"
    summary += "\n".join(results)
    summary += f"\n\n✅ Processed: {len(rc_numbers)} vehicles"
    
    await processing_msg.edit_text(summary, parse_mode='Markdown')
    
    # Send detailed reports
    await update.message.reply_text(
        "📄 Sending detailed reports...",
        parse_mode='Markdown'
    )
    
    for rc in rc_numbers:
        if bot_instance.validate_rc_number(rc):
            cached = bot_instance.get_cached_response(rc)
            if cached:
                formatted = bot_instance.format_intel_message(cached)
                await update.message.reply_text(formatted, parse_mode='Markdown')
                await asyncio.sleep(1)
    
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if query.data == "single_lookup":
        # Check quota
        has_quota, remaining = bot_instance.check_user_quota(user.id)
        if not has_quota:
            await query.edit_message_text(
                "⚠️ *DAILY LIMIT REACHED*\n\n"
                f"You've used all {MAX_QUERIES_PER_DAY} free queries for today.\n\n"
                "💎 Upgrade to Premium for unlimited queries!",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        quota_text = f"Remaining: {remaining}" if remaining >= 0 else "Unlimited"
        await query.edit_message_text(
            f"🎯 *SINGLE VEHICLE LOOKUP*\n\n"
            f"Enter RC number (e.g., MH12DE1433)\n\n"
            f"⚡ {quota_text}",
            parse_mode='Markdown'
        )
        return WAITING_RC
    
    elif query.data == "batch_mode":
        has_quota, remaining = bot_instance.check_user_quota(user.id)
        if not has_quota:
            await query.edit_message_text(
                "⚠️ Daily limit reached!",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        await query.edit_message_text(
            "📊 *BATCH PROCESSING MODE*\n\n"
            "Send multiple RC numbers (comma or line separated)",
            parse_mode='Markdown'
        )
        return BATCH_MODE
    
    elif query.data == "user_stats":
        stats = bot_instance.get_user_stats(user.id)
        if not stats:
            await query.edit_message_text(
                "📈 No statistics available yet. Start by looking up a vehicle!",
                parse_mode='Markdown'
            )
            return
        
        stats_text = f"""
📈 *YOUR STATISTICS*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: {user.first_name}
🆔 ID: `{user.id}`

📊 *USAGE STATS*
• Total Queries: {stats['total_queries']}
• Queries Today: {stats['queries_today']}
• Remaining Today: {stats['remaining_today'] if stats['remaining_today'] >= 0 else 'Unlimited ♾️'}

📅 *ACCOUNT INFO*
• Member Since: {stats['first_seen'][:10]}
• Last Active: {stats['last_seen'][:16]}
• Status: {'💎 Premium' if stats['is_premium'] else '🆓 Free'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *RECENT SEARCHES*
"""
        
        for i, (rc, timestamp, success) in enumerate(stats['recent_queries'][:5], 1):
            status = "✅" if success else "❌"
            stats_text += f"{i}. {status} {rc} - {timestamp[:16]}\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "help":
        help_text = """
📚 *QUICK HELP*

🔍 *How to search:*
1. Click "Lookup Vehicle"
2. Enter RC number
3. Get instant report!

📋 *RC Format:*
MH12DE1433
DL9CAB1234

⚡ *Daily Limit:*
Free users: 50 queries/day
Premium: Unlimited

💡 *Tips:*
• Use batch mode for multiple vehicles
• Reports are cached for 24 hours
• Insurance alerts are automatic

Need more help? Send /help
"""
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif query.data == "feedback":
        await query.edit_message_text(
            "💬 *SEND FEEDBACK*\n\n"
            "Please send your feedback, suggestions, or bug reports.\n\n"
            "Your input helps us improve! 🚀",
            parse_mode='Markdown'
        )
        return WAITING_FEEDBACK
    
    elif query.data == "back_to_menu":
        # Re-show start menu
        keyboard = [
            [InlineKeyboardButton("🔍 Lookup Vehicle", callback_data="single_lookup")],
            [InlineKeyboardButton("📊 Batch Process", callback_data="batch_mode")],
            [InlineKeyboardButton("📈 My Stats", callback_data="user_stats"),
             InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [InlineKeyboardButton("💬 Feedback", callback_data="feedback")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"*RC INFO BOT v3.0*\n\n"
            f"Welcome back, {user.first_name}! 👋\n\n"
            f"What would you like to do?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user feedback"""
    user = update.effective_user
    feedback_text = update.message.text.strip()
    
    if len(feedback_text) < 10:
        await update.message.reply_text(
            "⚠️ Feedback too short. Please provide more details (at least 10 characters)."
        )
        return WAITING_FEEDBACK
    
    # Save feedback
    bot_instance.save_feedback(user.id, feedback_text)
    
    await update.message.reply_text(
        "✅ *FEEDBACK RECEIVED!*\n\n"
        "Thank you for your feedback! 🙏\n"
        "We'll review it and get back to you if needed.\n\n"
        "Your input helps us improve! 🚀",
        parse_mode='Markdown'
    )
    
    # Notify admins if configured
    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"📬 *NEW FEEDBACK*\n\n"
                    f"From: {user.first_name} (@{user.username or 'N/A'})\n"
                    f"ID: `{user.id}`\n\n"
                    f"Message:\n{feedback_text}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    return ConversationHandler.END

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command"""
    user = update.effective_user
    stats = bot_instance.get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text(
            "📈 No statistics available yet. Start by looking up a vehicle!"
        )
        return
    
    stats_text = f"""
📈 *YOUR STATISTICS*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 User: {user.first_name}
🆔 ID: `{user.id}`

📊 *USAGE STATS*
• Total Queries: {stats['total_queries']}
• Queries Today: {stats['queries_today']}
• Remaining Today: {stats['remaining_today'] if stats['remaining_today'] >= 0 else 'Unlimited ♾️'}

📅 *ACCOUNT INFO*
• Member Since: {stats['first_seen'][:10]}
• Last Active: {stats['last_seen'][:16]}
• Status: {'💎 Premium' if stats['is_premium'] else '🆓 Free'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *RECENT SEARCHES*
"""
    
    for i, (rc, timestamp, success) in enumerate(stats['recent_queries'][:5], 1):
        status = "✅" if success else "❌"
        stats_text += f"{i}. {status} {rc} - {timestamp[:16]}\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /admin command - Admin only"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ This command is for administrators only.")
        return
    
    # Get admin stats
    stats = bot_instance.get_admin_stats()
    feedback_list = bot_instance.get_feedback_list()
    
    admin_text = f"""
👑 *ADMIN DASHBOARD*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 *SYSTEM STATISTICS*

👥 Total Users: {stats['total_users']}
📈 Total Queries: {stats['total_queries']}
✅ Successful: {stats['successful_queries']}
❌ Failed: {stats['total_queries'] - stats['successful_queries']}
📊 Success Rate: {stats['success_rate']:.1f}%

📅 *TODAY'S ACTIVITY*
• Queries Today: {stats['queries_today']}
• Active Users: {stats['active_today']}

💾 *CACHE*
• Cached Vehicles: {stats['cache_size']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 *TOP 5 USERS*
"""
    
    for i, (uid, username, count) in enumerate(stats['top_users'], 1):
        admin_text += f"{i}. @{username or 'Unknown'} - {count} queries\n"
    
    admin_text += "\n🚗 *MOST QUERIED VEHICLES*\n"
    for i, (rc, count) in enumerate(stats['top_rcs'], 1):
        admin_text += f"{i}. {rc} - {count} times\n"
    
    admin_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    admin_text += f"💬 *RECENT FEEDBACK* ({len(feedback_list)} total)\n"
    
    for fid, uid, username, msg, timestamp in feedback_list[:3]:
        admin_text += f"\n• @{username or 'Unknown'}: {msg[:50]}...\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_refresh")],
        [InlineKeyboardButton("📊 Export Data", callback_data="admin_export")],
        [InlineKeyboardButton("💬 View Feedback", callback_data="admin_feedback")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    keyboard = [[InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n\nWhat would you like to do next?",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def main():
    """Start the bot with comprehensive error handling"""
    logger.info("🚀 Starting RC Info Bot v3.0...")
    
    # Validate bot token
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not configured! Please set the BOT_TOKEN environment variable.")
        print("\n⚠️  ERROR: BOT_TOKEN not configured!")
        print("Please set your Telegram bot token:")
        print("  export BOT_TOKEN='your_bot_token_here'")
        print("\nOr add it to your .env file")
        return
    
    try:
        # Create Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Conversation handler for lookup
        lookup_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("lookup", lookup_command),
                CallbackQueryHandler(button_handler, pattern="^single_lookup$")
            ],
            states={
                WAITING_RC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rc_input)]
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="lookup_conversation",
            persistent=False
        )
        
        # Conversation handler for batch
        batch_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("batch", batch_command),
                CallbackQueryHandler(button_handler, pattern="^batch_mode$")
            ],
            states={
                BATCH_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_batch_input)]
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="batch_conversation",
            persistent=False
        )
        
        # Conversation handler for feedback
        feedback_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(button_handler, pattern="^feedback$")
            ],
            states={
                WAITING_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_handler)]
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="feedback_conversation",
            persistent=False
        )
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("admin", admin_command))
        
        # Add conversation handlers
        application.add_handler(lookup_conv_handler)
        application.add_handler(batch_conv_handler)
        application.add_handler(feedback_conv_handler)
        
        # Add callback query handler for other buttons
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Start bot
        logger.info("✅ RC Info Bot v3.0 is now running!")
        logger.info("━" * 50)
        logger.info("Bot Features:")
        logger.info("  • Comprehensive RC vehicle lookup")
        logger.info("  • Batch processing support")
        logger.info("  • Smart caching system")
        logger.info("  • Usage statistics tracking")
        logger.info("  • Admin dashboard")
        logger.info("  • User feedback system")
        logger.info("━" * 50)
        logger.info("Press Ctrl+C to stop the bot")
        
        print("\n" + "=" * 50)
        print("🤖 RC INFO BOT v3.0 - RUNNING")
        print("=" * 50)
        print("✅ Bot is online and ready!")
        print("📱 Start chatting with your bot on Telegram")
        print("⚡ Features: RC Lookup, Batch Processing, Stats, Admin Panel")
        print("=" * 50 + "\n")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        print(f"\n❌ Error starting bot: {str(e)}")
        raise

if __name__ == "__main__":
    main()
