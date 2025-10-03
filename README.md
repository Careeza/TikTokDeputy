# TikTok Deputy Verification

A web application to manually verify TikTok accounts of French deputies.

## Features

- Display cards for each French deputy with their potential TikTok accounts
- Manual verification system for validating accounts
- Check multiple possible accounts with detailed information
- Mark deputies as having no TikTok account (counts as verified)
- **Filter & Sort**: By verification status, legislature, name, or confidence score
- Real-time statistics dashboard
- Add TikTok accounts manually (automatically verified)
- **Export verified accounts to CSV** (includes both accounts with TikTok and those with no account)
- Modern, responsive UI with SVG icons

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database with existing data:
```bash
python load_data.py
```

## Running the Application

### Local Access Only
Start the server for local access only:
```bash
python main.py
```

The application will be available at: `http://localhost:8000`

### Network Access (Share with Others)

#### Option 1: Local Network (LAN) - Same WiFi/Network
The server is already configured to accept connections from other computers on your network.

1. **Start the server:**
```bash
python main.py
```

2. **Find your computer's IP address:**
   - **macOS**: Open Terminal and run `ipconfig getifaddr en0` or `ifconfig | grep "inet "`
   - **Windows**: Open Command Prompt and run `ipconfig`
   - **Linux**: Run `hostname -I` or `ip addr show`

3. **Share the URL with others:**
   - Your IP will be something like `192.168.1.100`
   - Others can access at: `http://YOUR_IP:8000`
   - Example: `http://192.168.1.100:8000`

**Important**: All users must be on the **same WiFi/network** as your computer.

#### Option 2: Internet Access (Anyone, Anywhere)
For remote collaboration when people are not on your network, use **ngrok**:

1. **Install ngrok:**
   - Download from https://ngrok.com/download
   - Or use: `brew install ngrok` (macOS) or `choco install ngrok` (Windows)

2. **Start your server:**
```bash
python main.py
```

3. **In a new terminal, start ngrok:**
```bash
ngrok http 8000
```

4. **Share the ngrok URL:**
   - ngrok will display a URL like: `https://abc123.ngrok.io`
   - Share this URL with anyone - they can access from anywhere!
   - The URL changes each time you restart ngrok (free version)

**Note**: The database is shared, so all users will see the same data and verifications in real-time!

## Project Structure

```
.
├── main.py                 # FastAPI application and API endpoints
├── models.py               # SQLAlchemy database models
├── load_data.py            # Script to load data from JSON to database
├── tiktok_results.json     # Source data file
├── requirements.txt        # Python dependencies
├── static/                 # Frontend files
│   ├── index.html         # Main HTML page
│   ├── styles.css         # Styling
│   └── app.js             # JavaScript frontend logic
└── tiktok_verification.db  # SQLite database (created on first run)
```

## Database Schema

The `Deputy` model includes:
- Basic information: name, legislature
- Best match TikTok account details
- Top 3 alternative matches
- Verification fields: `verified_by_human`, `human_verified_username`
- Testing tracking: `username_tested`, `username_to_test`

## API Endpoints

- `GET /api/deputies` - Get all deputies (with optional filters)
- `GET /api/deputies/{id}` - Get specific deputy
- `PUT /api/deputies/{id}/verify` - Verify a deputy's TikTok account
- `POST /api/deputies/{id}/add-manual` - Add a manual TikTok account (auto-verified)
- `PUT /api/deputies/{id}/usernames` - Update username lists
- `GET /api/stats` - Get verification statistics
- `GET /api/export/verified-accounts` - Export verified accounts to CSV

## Usage

1. **Load the initial data** from `tiktok_results.json` (WARNING: This overwrites the database)
2. **Browse through deputy cards** on the main page
3. **Click "Vérifier les comptes"** to view possible TikTok accounts
4. **For multiple accounts**: Click "Vérifier ce compte" on each to see detailed information
5. **For single account**: Details are shown directly
6. **Validate**: Click "Valider ce compte" to confirm the correct TikTok account
7. **Add manually**: Use the manual add section to add a TikTok account not found by the scripts
8. **Unverify**: If needed, you can cancel verification from the verified account view
9. **Use filters**: Filter by verification status or legislature

## Important Notes

### Database Overwrites
When you run `python load_data.py`, it **DELETES ALL EXISTING DATA** including manual verifications. 
Only use this command:
- For initial setup
- When you want to completely refresh from the JSON file
- **After updating this README**: You need to reload the data to get the bio and mentions fields properly enriched in all accounts

### Data Enrichment
The loading script now automatically enriches the `top_3_matches` data:
- When a match's username equals the best_match username, it copies over the bio and mentions fields
- This ensures all account details show proper biography and mention badges
- Non-best matches will have empty bio and false mention flags by default

### Workflow
1. **Unverified deputies** show a count of possible accounts
2. **Verified deputies** show the validated TikTok account directly on the card
3. **No account deputies** show "Aucun compte TikTok" (counts as verified)
4. Click any card to see details and verify accounts
5. Once verified, the modal only shows the validated account (with option to unverify)

### Verification Options
When viewing an unverified deputy, you can:
1. **Validate an existing account** - Click "Valider ce compte" on any suggested account
2. **Add a manual account** - Enter a TikTok URL/username (automatically verified)
3. **Mark as no account** - Confirm the deputy has no TikTok (counts as verified)
4. **Search TikTok** - Click "Rechercher sur TikTok" to search Google for the deputy

### Collaboration Features
- **Shared Database**: All users see the same data
- **Auto-Refresh**: Data automatically refreshes every 30 seconds
- **Manual Refresh**: Click "Actualiser" button to immediately sync
- **Last Update Indicator**: Shows when data was last synced
- **Network Access**: Share with colleagues on the same network
- **Internet Access**: Use ngrok for remote collaboration
- **CSV Export**: Download verified accounts list at any time

### How Concurrent Access Works
When multiple people use the website simultaneously:
1. **Auto-sync every 30 seconds** - Everyone's view updates automatically
2. **Manual refresh** - Click "Actualiser" to sync immediately
3. **Database handles conflicts** - Last write wins (no data loss)
4. **Modal closes on verify** - Returns to updated list after making changes

## Future Enhancements

The JSON data will include additional fields:
- `username_tested`: List of usernames already tested
- `username_to_test`: List of usernames to test
- `verified_by_human`: Boolean flag for manual verification

