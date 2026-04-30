# ThingSpeak License User Management Scripts

Automation scripts for managing ThingSpeak license users in the MathWorks License Center via Selenium.

## Overview

This project provides two complementary tools:

- **Add Users**: Bulk import users from a CSV file
- **Remove Users**: Bulk remove all license users

Both scripts automate the MathWorks License Center UI and require manual login to complete authentication.

## Requirements

- Python 3.9+
- Selenium
- Chrome/Chromium browser with matching ChromeDriver
- MathWorks account with license management permissions

Install dependencies:
```bash
pip install selenium
```

## Scripts

### `add_user_thingspeak_macro.py`

Adds users to the ThingSpeak license from a CSV file.

**Setup:**
1. Create `add_to_license.csv` with user data
   - Required column: `Email` (or `Username`, `email`, `email_address`)
   - Optional columns: `Timestamp`, `Name` (used for logging)

**Usage:**
```bash
python add_user_thingspeak_macro.py
```

Then:

1. Browser opens automatically
2. Complete Canvas/MathWorks login manually (do not save credentials)
3. Script waits for confirmation before proceeding
4. Enter the starting row index (0-based) or press Enter for 0
5. Users are added sequentially

**Output:**

- Console logs all additions/skips

---

### `remove_thingspeak_users_v2.py`

Removes all current users from the ThingSpeak license.

**Usage:**
```bash
python remove_thingspeak_users_v2.py
```

Then:

1. Browser opens automatically
2. Complete Canvas/MathWorks login manually
3. Script waits for confirmation before proceeding
4. All users are removed one by one with retry logic

**Output:**

- Console logs each removal
- Summary printed at the end (removed count / failed count)
---

## Troubleshooting

- **Website detects botting**: Press Ctrl+R to reload. The script should recover.
- **Too many requests**: Website may rate-limit. Wait a few minutes and retry, or use `INTER_DELAY_SECONDS` to slow down removals.
- **Login fails**: Ensure you don't save credentials to the browser; clear cookies if needed.
- **Element not found**: Check the MathWorks License Center UI hasn't changed significantly. Save debug artifacts and inspect the HTML.

## Configuration

Edit constants at the top of each script:

- `TIMEOUT_SECONDS`: Selenium wait timeout
- `HEADLESS`: Set to `True` to run without showing browser window (not recommended for login)
- `INTER_DELAY_SECONDS`: Delay between user removals (adds script more gracefully to server)

## License

Internal use only.
