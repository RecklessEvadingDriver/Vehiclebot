#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TELEGRAM VEHICLE OSINT BOT by Darkhunter<3
# Deployment: Any server with Python 3.7+

import logging
import requests
import json
import time
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ConversationHandler
)

# ===== CONFIGURATION =====
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
API_BASE = "https://vvvin-ng.vercel.app/lookup?rc="
ADMIN_IDS = [123456789]  # Your Telegram ID
DATABASE_FILE = "vehicle_intel.db"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_RC, BATCH_MODE = range(2)

class VehicleIntelBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for user tracking and analytics"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                queries_count INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                rc_number TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_user_activity(self, user_id, username, first_name, last_name):
        """Log user activity in database"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, queries_count, last_seen)
            VALUES (?, ?, ?, ?, 
                COALESCE((SELECT queries_count FROM users WHERE user_id = ?), 0) + 1,
                CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name, user_id))
        
        conn.commit()
        conn.close()

    def log_query(self, user_id, rc_number, success):
        """Log individual query"""
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO queries (user_id, rc_number, success)
            VALUES (?, ?, ?)
        ''', (user_id, rc_number, success))
        
        conn.commit()
        conn.close()

    async def query_rc_api(self, rc_number):
        """Enhanced API query with better error handling"""
        try:
            url = f"{API_BASE}{rc_number}"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                return self.parse_intel_data(response.json(), rc_number)
            else:
                return {"error": f"API Error: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            return {"error": "Query timeout - API unresponsive"}
        except Exception as e:
            return {"error": f"System error: {str(e)}"}

    def parse_intel_data(self, data, rc_number):
        """Parse and structure intelligence data"""
        if not isinstance(data, dict):
            return {"error": "Invalid API response"}
        
        # Create comprehensive intelligence report
        intel_report = {
            "metadata": {
                "target": rc_number,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_confidence": "HIGH"
            },
            "personal_intel": {
                "👤 Owner": data.get("Owner Name", "N/A"),
                "👨‍👩‍👧‍👦 Father": data.get("Father's Name", "N/A"),
                "🔢 Owner Serial": data.get("Owner Serial No", "N/A")
            },
            "vehicle_specs": {
                "🚗 Model": data.get("Model Name", "N/A"),
                "🏭 Manufacturer": data.get("Maker Model", "N/A"),
                "📊 Class": data.get("Vehicle Class", "N/A"),
                "⛽ Fuel Type": data.get("Fuel Type", "N/A"),
                "🔩 Chassis": data.get("Chassis Number", "N/A"),
                "⚙️ Engine": data.get("Engine Number", "N/A")
            },
            "legal_status": {
                "📅 Registration": data.get("Registration Date", "N/A"),
                "🔄 Fitness Valid": data.get("Fitness Upto", "N/A"),
                "💰 Tax Paid": data.get("Tax Upto", "N/A"),
                "🌫️ PUC Valid": data.get("PUC Upto", "N/A"),
                "🛡️ Insurance": data.get("Insurance Upto", "N/A")
            },
            "alerts": {
                "🚨 Insurance Expiry": data.get("Insurance Expiry In", "N/A"),
                "⚠️ PUC Expiry": data.get("PUC Expiry In", "N/A"),
                "🔴 Blacklist": data.get("Blacklist Status", "N/A")
            }
        }
        
        return intel_report

    def format_intel_message(self, report):
        """Format intelligence report for Telegram"""
        if "error" in report:
            return f"❌ QUERY FAILED:\n{report['error']}"
        
        message = "🔍 *VEHICLE INTELLIGENCE REPORT*\n"
        message += "═" * 30 + "\n\n"
        
        # Add metadata
        meta = report["metadata"]
        message += f"🎯 *Target:* `{meta['target']}`\n"
        message += f"🕐 *Acquired:* {meta['timestamp']}\n"
        message += f"📊 *Confidence:* {meta['data_confidence']}\n\n"
        
        # Personal intelligence
        message += "*👤 PERSONAL INTELLIGENCE:*\n"
        for key, value in report["personal_intel"].items():
            if value and value != "N/A":
                message += f"• {key}: `{value}`\n"
        
        # Vehicle specs
        message += "\n*🚗 VEHICLE SPECIFICATIONS:*\n"
        for key, value in report["vehicle_specs"].items():
            if value and value != "N/A":
                message += f"• {key}: `{value}`\n"
        
        # Legal status
        message += "\n*⚖️ LEGAL STATUS:*\n"
        for key, value in report["legal_status"].items():
            if value and value != "N/A":
                message += f"• {key}: `{value}`\n"
        
        # Alerts
        message += "\n*🚨 SECURITY ALERTS:*\n"
        for key, value in report["alerts"].items():
            if value and value != "N/A":
                message += f"• {key}: `{value}`\n"
        
        return message

# ===== TELEGRAM BOT HANDLERS =====
bot_instance = VehicleIntelBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user = update.effective_user
    bot_instance.log_user_activity(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = """
🤖 *VEHICLE INTELLIGENCE BOT v2.0*

*Capabilities:*
• 🔍 Vehicle registration lookup
• 👤 Owner identity verification  
• ⚖️ Legal status monitoring
• 🚨 Security alert system
• 📊 Batch processing mode

*Commands:*
/start - Show this message
/lookup - Single vehicle query  
/batch - Multiple vehicle processing
/stats - Your usage statistics
/admin - Administrator panel

*Usage:* Send /lookup or click button below.
"""
    
    keyboard = [
        [InlineKeyboardButton("🔍 Single Lookup", callback_data="single_lookup")],
        [InlineKeyboardButton("📊 Batch Mode", callback_data="batch_mode")],
        [InlineKeyboardButton("📈 My Stats", callback_data="user_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /lookup command"""
    await update.message.reply_text(
        "🎯 *SINGLE TARGET MODE*\n\n"
        "Send me the vehicle RC number (e.g., MH12DE1433)\n"
        "I'll gather full intelligence within 15 seconds.",
        parse_mode='Markdown'
    )
    return WAITING_RC

async def handle_rc_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle RC number input"""
    rc_number = update.message.text.strip().upper()
    user_id = update.effective_user.id
    
    # Basic validation
    if len(rc_number) < 5:
        await update.message.reply_text("❌ Invalid RC number format")
        return WAITING_RC
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔍 *Querying Intelligence Database...*\n"
        f"Target: `{rc_number}`\n"
        f"Please wait ⏳",
        parse_mode='Markdown'
    )
    
    # Query API
    intel_report = await bot_instance.query_rc_api(rc_number)
    
    # Log the query
    success = "error" not in intel_report
    bot_instance.log_query(user_id, rc_number, success)
    
    # Format and send response
    response_text = bot_instance.format_intel_message(intel_report)
    
    # Edit original message with results
    await processing_msg.edit_text(
        response_text,
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /batch command"""
    await update.message.reply_text(
        "📊 *BATCH PROCESSING MODE*\n\n"
        "Send me RC numbers separated by commas or new lines.\n"
        "Example:\n"
        "MH12DE1433, DL9CAB1234, KA01AB1234",
        parse_mode='Markdown'
    )
    return BATCH_MODE

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "single_lookup":
        await query.edit_message_text(
            "🎯 *SINGLE TARGET MODE*\n\nSend me the RC number:",
            parse_mode='Markdown'
        )
        return WAITING_RC
    
    elif query.data == "batch_mode":
        await query.edit_message_text(
            "📊 *BATCH PROCESSING MODE*\n\nSend multiple RC numbers:",
            parse_mode='Markdown'
        )
        return BATCH_MODE

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
    """Start the bot"""
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for main flow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("lookup", lookup_command),
            CommandHandler("batch", batch_command),
            CallbackQueryHandler(button_handler)
        ],
        states={
            WAITING_RC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rc_input)],
            BATCH_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rc_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(conv_handler)
    
    # Start bot
    print("🤖 Vehicle Intelligence Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
