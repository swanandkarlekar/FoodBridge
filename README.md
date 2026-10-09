# 🍲 FoodBridge — Food Donation & Food-Waste Reduction Platform

> *"Good Food Deserves a Second Chance."*

**FoodBridge** is a modern, full-stack web platform connecting restaurants, hotels, event caterers, bakeries, and food businesses directly with local shelters, food pantries, and community kitchens. By turning edible surplus into community meals, FoodBridge prevents landfill emissions, saves water, and fights local food insecurity.

---

## 🌟 Key Features

- **Real-Time Surplus Listings**: Donors can list food in 60 seconds with servings, container details, pickup windows, and allergen disclosures.
- **Dynamic Surplus Directory**: Filter by category (Cooked Meals, Bakery, Produce, Dairy, Packaged Goods), city, availability status, and sorting order.
- **NGO Rescue Claims**: Verified non-profits can claim full or partial servings with pickup logistics notes and estimated arrival times.
- **Interactive Multi-Role Dashboards**:
  - **Food Donors**: Manage listings, review incoming claims, approve or decline requests, and mark donations as collected.
  - **NGOs & Shelters**: Track submitted claims, inspect approved pickup details, and cancel pending requests.
  - **Volunteers**: Claim and complete rescue transport missions between donors and soup kitchens.
- **Administrator Control Panel**: Moderation dashboard to inspect all registered users, toggle food listing visibility, track all rescue claims, and manage support tickets.
- **Instant Demo Switcher**: One-click demo login buttons to test all roles without typing passwords.
- **Security & Integrity**: Session-based CSRF protection, salted Werkzeug password hashing, parameter-sanitized SQLite queries, and strict role authorization.
- **Zero Heavy Dependencies**: Pure Python 3, Flask, SQLite3, HTML5, semantic CSS3, and Vanilla JavaScript. Runs everywhere without Node.js or Docker.

---

## 💻 Tech Stack

- **Backend**: Python 3.10+, Flask 3.1+
- **Database**: SQLite3 with foreign keys and index optimization
- **Templating**: Jinja2 with template inheritance
- **Styling**: Modern CSS3 (CSS Variables, Flexbox, CSS Grid, mobile-responsive breakpoints)
- **Frontend Interactivity**: Vanilla JavaScript (ES6+)
- **Security**: Werkzeug security hashing, CSRF tokens, session state management

---

## 📂 Project Structure

```text
FoodBridge/
├── app.py                  # Main Flask application and routing logic
├── config.py               # Application configuration and settings
├── db.py                   # SQLite database connection & schema manager
├── seed.py                 # Seed script with realistic demo accounts & listings
├── requirements.txt        # Lightweight dependencies
├── README.md               # Documentation and execution guide
├── .env.example            # Environment variables example template
├── .gitignore              # Git ignore rules (ignoring SQLite db, venv, secrets)
├── instance/               # Auto-created directory for SQLite database file
│   └── foodbridge.sqlite   # SQLite database file
├── static/
│   ├── css/
│   │   └── style.css       # Custom modern responsive styling
│   └── js/
│       └── main.js         # Navigation, modals, alerts, and demo helpers
└── templates/
    ├── base.html           # Master layout with navigation and footer
    ├── index.html          # Landing home page
    ├── donations.html      # Available food donations catalog & filters
    ├── donation_detail.html# Full donation details & NGO request dialog
    ├── donate.html         # Food donation submission form
    ├── login.html          # Authentication with 1-click demo accounts
    ├── register.html       # Role-based user registration
    ├── dashboard.html      # Dynamic Donor, NGO, and Volunteer dashboard
    ├── about.html          # Mission, vision, SDGs, and food safety standards
    ├── contact.html        # Contact inquiry form & FAQs
    ├── admin.html          # Administrative moderation control center
    ├── 403.html            # Forbidden error page
    ├── 404.html            # Not found error page
    └── 500.html            # Internal server error page
```

---

## 🚀 Quick Start Guide (Windows)

### 1. Prerequisites
Ensure you have Python 3 installed. You can check in PowerShell by running:
```powershell
py --version
# or: python --version
```

### 2. Set Up a Virtual Environment (Recommended)
Open PowerShell in the project directory:
```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is restricted in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Seed the Database
Populate the database with realistic sample food listings, demo accounts, and requests:
```powershell
py seed.py
```

### 5. Launch the Application
```powershell
py app.py
```
Open your browser at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 👥 Demo Accounts for Testing

You can use the **1-click autofill buttons** on the [Login Page](http://127.0.0.1:5000/login) or enter these credentials manually:

| Role | Account Name | Email | Password | What You Can Test |
| :--- | :--- | :--- | :--- | :--- |
| **Donor** | Marcus Vance (*GreenLeaf Bistro*) | `donor@foodbridge.org` | `FoodBridge123!` | Create listings, approve incoming NGO claims, mark donations collected |
| **NGO** | Sarah Jenkins (*Hope Kitchen*) | `ngo@foodbridge.org` | `FoodBridge123!` | Browse directory, submit rescue requests, review pickup instructions |
| **Volunteer** | Alex Rivera (*Green Fleet*) | `volunteer@foodbridge.org` | `FoodBridge123!` | Claim reserved deliveries and mark rescue missions delivered |
| **Admin** | System Administrator | `admin@foodbridge.org` | `AdminSecret2026!` | Manage users, toggle listing visibility, review messages & metrics |

*(Note: These are local demonstration credentials intended for testing only).*

---

## 🛡️ Creating a Custom Admin Account

To create a new administrator account securely from the command line:
```powershell
flask create-admin
```
Follow the prompt to enter your email, name, and password.

---

## 📤 How to Upload to GitHub

Follow these steps to publish this project to a new GitHub repository:

1. Create a new repository on [GitHub](https://github.com/new) named `FoodBridge` (do **not** initialize it with a README or `.gitignore` since they are already included).
2. Open PowerShell in the project folder and run:

```powershell
# 1. Initialize git repository
git init

# 2. Stage all files
git add .

# 3. Create initial commit
git commit -m "Initial commit: Complete FoodBridge food rescue platform"

# 4. Set main branch
git branch -M main

# 5. Link your remote GitHub repository (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/FoodBridge.git

# 6. Push code to GitHub
git push -u origin main
```

---

## 🌐 Production Deployment Guide

FoodBridge is lightweight and ready for deployment on any standard Python hosting service (e.g., Render, Railway, PythonAnywhere, or AWS EC2).

### Deployment on Render / Railway:
1. Add `gunicorn` to `requirements.txt`:
   ```text
   Flask>=3.0.0
   python-dotenv>=1.0.0
   gunicorn>=21.2.0
   ```
2. Build Command:
   ```bash
   pip install -r requirements.txt && python seed.py
   ```
3. Start Command:
   ```bash
   gunicorn app:app
   ```
4. Set Environment Variables:
   - `SECRET_KEY`: Set to a strong random secret key.
   - `FLASK_DEBUG`: `False`

---

## 📄 License
This project is open-source under the MIT License.
