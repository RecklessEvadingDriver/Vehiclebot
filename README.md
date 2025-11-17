# 🚗 RC Info Bot - Professional Vehicle Information Lookup Bot

A comprehensive, professional Telegram bot for Indian vehicle registration certificate (RC) lookup with advanced features and beautiful formatting.

## ✨ Features

### 🔥 Core Features
- **Comprehensive RC Lookup**: Get complete vehicle information including:
  - 👤 Owner details (Name, Father's name, Serial number)
  - 🚗 Vehicle specifications (Model, Maker, Class, Fuel type, Engine/Chassis numbers)
  - 📄 Insurance information (Company, Policy number, Expiry dates, Alerts)
  - 🗓️ Important dates (Registration, Fitness, Tax, PUC validity)
  - 🚫 Security alerts (Blacklist status, NOC details)
  - 🏢 RTO information
  - 📍 Additional details (Financer, Permit type, Capacity)

### 💎 Advanced Features
- **Batch Processing**: Look up multiple vehicles at once
- **Smart Caching**: 24-hour cache for faster repeated queries
- **Usage Quota System**: Daily query limits with premium support
- **Statistics Dashboard**: Track your usage and history
- **Admin Panel**: Comprehensive admin dashboard with analytics
- **Feedback System**: Built-in user feedback collection
- **Error Handling**: Robust retry logic and error recovery
- **Input Validation**: Smart RC number format validation

### 🎨 Professional Design
- Beautiful formatted reports with emojis
- Progress indicators for long operations
- Interactive inline keyboards
- Detailed help documentation
- Clean, organized code structure

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Internet connection

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/RecklessEvadingDriver/Vehiclebot.git
cd Vehiclebot

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Set your bot token as an environment variable:

```bash
# Linux/Mac
export BOT_TOKEN="your_bot_token_here"

# Windows (Command Prompt)
set BOT_TOKEN=your_bot_token_here

# Windows (PowerShell)
$env:BOT_TOKEN="your_bot_token_here"
```

**Optional configurations:**
```bash
export ADMIN_IDS="123456789,987654321"  # Comma-separated admin Telegram IDs
export MAX_QUERIES_PER_DAY="50"          # Daily query limit for free users
```

### 3. Run the Bot

```bash
python bot.py
```

You should see:
```
==================================================
🤖 RC INFO BOT v3.0 - RUNNING
==================================================
✅ Bot is online and ready!
📱 Start chatting with your bot on Telegram
⚡ Features: RC Lookup, Batch Processing, Stats, Admin Panel
==================================================
```

## 🌐 Deployment

### Deploy to Railway

1. **Fork this repository** to your GitHub account

2. **Go to [Railway.app](https://railway.app)** and sign in

3. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your forked repository

4. **Add Environment Variables**
   - Go to your project settings
   - Click "Variables" tab
   - Add:
     - `BOT_TOKEN`: Your Telegram bot token
     - `ADMIN_IDS`: Your Telegram user ID(s) (optional)
     - `MAX_QUERIES_PER_DAY`: Daily query limit (optional, default: 50)

5. **Deploy**
   - Railway will automatically detect `railway.toml`
   - The bot will start automatically

6. **Check Logs**
   - Monitor the deployment in Railway dashboard
   - Ensure bot is running successfully

### Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create new app
heroku create your-rc-bot

# Set environment variables
heroku config:set BOT_TOKEN="your_bot_token_here"
heroku config:set ADMIN_IDS="your_telegram_id"

# Push and deploy
git push heroku main
```

### Deploy to VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone repository
git clone https://github.com/RecklessEvadingDriver/Vehiclebot.git
cd Vehiclebot

# Install dependencies
pip3 install -r requirements.txt

# Set environment variable
export BOT_TOKEN="your_bot_token_here"

# Run with screen or tmux
screen -S rcbot
python3 bot.py

# Detach: Ctrl+A, then D
```

## 📱 Bot Commands

### User Commands
- `/start` - Welcome message and main menu
- `/lookup` - Single vehicle RC lookup
- `/batch` - Batch processing mode (multiple vehicles)
- `/stats` - View your usage statistics
- `/help` - Detailed help and usage instructions
- `/cancel` - Cancel current operation

### Admin Commands (Admins only)
- `/admin` - Admin dashboard with system statistics
- View all user statistics
- Monitor bot usage and performance
- Access feedback from users

## 🎯 Usage Examples

### Single Lookup
1. Start the bot: `/start`
2. Click "🔍 Lookup Vehicle" or send `/lookup`
3. Enter RC number: `MH12DE1433`
4. Receive comprehensive report instantly!

### Batch Processing
1. Send `/batch` or click "📊 Batch Process"
2. Enter multiple RC numbers:
   ```
   MH12DE1433, DL9CAB1234, KA01AB1234
   ```
   Or line-separated:
   ```
   MH12DE1433
   DL9CAB1234
   KA01AB1234
   ```
3. Get all reports together!

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | - | ✅ Yes |
| `ADMIN_IDS` | Comma-separated admin Telegram IDs | - | ❌ No |
| `MAX_QUERIES_PER_DAY` | Daily query limit for free users | 50 | ❌ No |

### Database

The bot uses SQLite database (`vehicle_intel.db`) to store:
- User information and activity
- Query history
- Cache data
- User feedback

## 📊 API Information

This bot uses the VVVin RC Lookup API:
- **Base URL**: `https://vvvin-ng.vercel.app/lookup?rc=`
- **Method**: GET
- **Response**: JSON with comprehensive vehicle data

Example:
```
https://vvvin-ng.vercel.app/lookup?rc=MH12DE1433
```

## 🛡️ Security Features

- Input validation for RC numbers
- Rate limiting with daily quotas
- User ban system (admin feature)
- Secure API token handling
- Error logging without exposing sensitive data

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

**Important**: This bot is provided for **educational and informational purposes only**.

- Users are **fully responsible** for their actions when using this bot
- We do **not promote or support** any illegal activities
- Vehicle information should be used ethically and legally
- Respect privacy and data protection laws
- This bot is not affiliated with any government agency or RTO

By using this bot, you agree to use it responsibly and in compliance with all applicable laws and regulations.

## 🆘 Support

### Common Issues

**Bot not starting?**
- Check if `BOT_TOKEN` is set correctly
- Ensure all dependencies are installed
- Check Python version (3.8+ required)

**API errors?**
- The VVVin API might be down temporarily
- Check your internet connection
- Verify RC number format is correct

**Queries not working?**
- Check if you've reached daily limit
- Verify RC number format (e.g., MH12DE1433)
- Try again after a few seconds

### Get Help
- 📧 Open an issue on GitHub
- 💬 Contact via Telegram (if configured)
- 📖 Read the `/help` command in bot

## 🎉 Features Coming Soon

- [ ] Export reports as PDF
- [ ] Export reports as Excel
- [ ] Premium subscription system
- [ ] Multi-language support
- [ ] Voice command support
- [ ] Advanced analytics dashboard
- [ ] Webhook deployment option
- [ ] Custom report templates

## 👨‍💻 Developer

Created with ❤️ by RC Info Bot Team

## 🌟 Acknowledgments

- Telegram Bot API
- VVVin API for RC data
- Python Telegram Bot library
- All contributors and users

---

**Made with 🔥 by RC Info Bot Team** | **Powered by VVVin API**

*Give this repository a ⭐ if you find it helpful!*
