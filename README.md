# Vehicle Intelligence Telegram Bot

A Telegram bot for vehicle registration lookup and intelligence gathering.

## Features

- 🔍 Vehicle registration lookup
- 👤 Owner identity verification
- ⚖️ Legal status monitoring
- 🚨 Security alert system
- 📊 Batch processing mode

## Deployment to Railway

### Prerequisites
1. A Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
2. A Railway account (https://railway.app)

### Steps

1. **Fork or clone this repository**

2. **Connect to Railway**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose this repository

3. **Set Environment Variables**
   - In Railway dashboard, go to your project
   - Click on "Variables" tab
   - Add the following variable:
     - `BOT_TOKEN`: Your Telegram bot token from @BotFather

4. **Deploy**
   - Railway will automatically detect the `railway.toml` configuration
   - The bot will start automatically using `python bot.py`
   - Check logs to confirm the bot is running

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your bot token:
   ```bash
   export BOT_TOKEN="your_bot_token_here"
   # or create a .env file (copy from .env.example)
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Configuration

The bot uses environment variables for configuration:
- `BOT_TOKEN` (required): Your Telegram bot token
- Falls back to hardcoded token for local testing if not set

## Commands

- `/start` - Show welcome message and menu
- `/lookup` - Single vehicle query
- `/batch` - Multiple vehicle processing
- `/stats` - Your usage statistics
- `/admin` - Administrator panel

## Support

For issues or questions, please open an issue on GitHub.
