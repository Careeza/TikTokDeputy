# Deployment Guide - Railway

## ✅ Prerequisites Created

I've created the following files for Railway deployment:
- `Procfile` - Tells Railway how to start the app
- `railway.json` - Railway configuration
- `runtime.txt` - Python version
- `.gitignore` - Files to exclude from git
- `.railwayignore` - Files to exclude from deployment

## 📝 Step-by-Step Deployment

### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for Railway deployment"

# Create a new repository on GitHub
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Railway

1. **Go to https://railway.app**
2. Click **"Start a New Project"**
3. Sign in with GitHub
4. Click **"Deploy from GitHub repo"**
5. Select your repository
6. Railway will automatically detect and deploy!

### Step 3: Initialize Database

After first deployment:

1. In Railway dashboard, click on your service
2. Go to **"Settings"** → **"Generate Domain"**
3. Copy your app URL (e.g., `https://your-app.railway.app`)
4. Open terminal and run:

```bash
# SSH into Railway or use their CLI
railway login
railway link
railway run python load_data.py
```

Or manually:
- Visit `https://your-app.railway.app` (it will show empty data)
- Download the database, run `python load_data.py` locally
- Upload `tiktok_verification.db` to Railway via their dashboard

### Step 4: Configure Environment (Optional)

In Railway dashboard:
- Go to **Variables** tab
- Add any environment variables if needed

## 🎯 Your App URL

After deployment, Railway will give you a URL like:
`https://your-app-name.railway.app`

Share this URL with your collaborators!

## 💾 Database Persistence

Railway provides:
- **Persistent volumes** - Your SQLite database will be saved
- **Automatic backups** - Database is backed up
- **File persistence** - Uploads and changes are kept

## 🔄 Automatic Updates

Every time you push to GitHub:
1. Railway automatically rebuilds
2. Deploys new version
3. Restarts the app

Just:
```bash
git add .
git commit -m "Your changes"
git push
```

## 🚨 Troubleshooting

**If deployment fails:**
1. Check Railway logs in dashboard
2. Verify `requirements.txt` has all dependencies
3. Make sure `tiktok_results.json` is committed

**If database is empty:**
1. Run `railway run python load_data.py`
2. Or manually upload `tiktok_verification.db`

**If static files don't load:**
- Railway serves them automatically from `/static`
- Check paths in HTML files are correct

## 💰 Cost

- **Free tier**: 500 hours/month
- **Your app**: ~720 hours/month (always on)
- **Solution**: Add payment method for $5/month (500 hours free + $5 for extra)

Or use **Render.com** (completely free, but slower):
See `DEPLOYMENT_RENDER.md` for instructions.

