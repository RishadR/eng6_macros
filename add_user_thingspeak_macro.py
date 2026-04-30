"""Add users to ThingSpeak license center from add_to_license.csv using Selenium.

Flow:
0. Check the `add_to_license.csv` file and add all the emails in the Email column
1. Opens the Manage Users page automatically
2. Complete Canvas/MathWorks login manually (Probably should not save credentials)
3. Script adds users starting from the row index you provide

Troubleshoot
- Matlab website does not like too many repeated requests - so might need to space out if we have a lot of users
- Sometimes the website just detects botting and refueses to load - Cntrl+R to reload usually works
- If nothing else works, try a few minutes later
"""

import csv
import random
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

MANAGE_USERS_URL = "https://www.mathworks.com/licensecenter/licenses/41012247/8966129/end_users"
CSV_PATH = Path("add_to_license.csv")
TIMEOUT_SECONDS = 20
FIRST_NAME_PLACEHOLDER = "x"
LAST_NAME_PLACEHOLDER = "x"
MIN_JITTER_SECONDS = 0.05
MAX_JITTER_SECONDS = 0.1


def _tiny_jitter() -> None:
    time.sleep(random.uniform(MIN_JITTER_SECONDS, MAX_JITTER_SECONDS))


def _click_element(driver: webdriver.Chrome, element: WebElement) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _resolve_email_field(rows: list[dict[str, str]]) -> str:
    if not rows:
        raise ValueError("CSV is empty.")
    candidates = ["Username", "Email", "email", "email_address"]
    available = set(rows[0].keys())
    for field in candidates:
        if field in available:
            return field
    raise ValueError(f"No email column found. Available columns: {sorted(available)}")


def _wait_for_manage_users(wait: WebDriverWait) -> None:
    wait.until(EC.presence_of_element_located((By.ID, "tab_content_area")))
    wait.until(EC.element_to_be_clickable((By.ID, "add_user_link")))


def _open_add_user_form(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    add_users_btn = wait.until(EC.element_to_be_clickable((By.ID, "add_user_link")))
    _click_element(driver, add_users_btn)
    wait.until(EC.presence_of_element_located((By.ID, "forms_add_user_email_address")))
    wait.until(EC.presence_of_element_located((By.ID, "forms_add_user_first_name")))
    wait.until(EC.presence_of_element_located((By.ID, "forms_add_user_last_name")))
    wait.until(EC.element_to_be_clickable((By.ID, "add_user")))


def _submit_user(driver: webdriver.Chrome, wait: WebDriverWait, email: str) -> None:
    email_input = wait.until(EC.element_to_be_clickable((By.ID, "forms_add_user_email_address")))
    first_name_input = wait.until(EC.element_to_be_clickable((By.ID, "forms_add_user_first_name")))
    last_name_input = wait.until(EC.element_to_be_clickable((By.ID, "forms_add_user_last_name")))

    email_input.clear()
    first_name_input.clear()
    last_name_input.clear()

    email_input.send_keys(email)
    _tiny_jitter()
    first_name_input.send_keys(FIRST_NAME_PLACEHOLDER)
    _tiny_jitter()
    last_name_input.send_keys(LAST_NAME_PLACEHOLDER)
    _tiny_jitter()

    submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "add_user")))
    _click_element(driver, submit_btn)


def _finish_success(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    done_btn = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(normalize-space(),'Done')] | "
                "//a[contains(normalize-space(),'Done')] | "
                "//input[((@type='submit') or (@type='button')) and contains(@value,'Done')]",
            )
        )
    )
    _click_element(driver, done_btn)
    _wait_for_manage_users(wait)


def main() -> None:
    rows = _load_rows(CSV_PATH)
    email_field = _resolve_email_field(rows)

    start_row_input = input("Start row index (0-based, default 0): ").strip()
    start_row = int(start_row_input) if start_row_input else 0
    if start_row < 0 or start_row >= len(rows):
        raise ValueError(f"Start row must be between 0 and {len(rows) - 1}")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, TIMEOUT_SECONDS)

    added_count = 0
    failed_count = 0

    try:
        driver.get(MANAGE_USERS_URL)
        print("Browser opened. Complete login in this browser.")
        input("Press Enter here once login is complete and Manage Users is visible... ")
        driver.get(MANAGE_USERS_URL)
        _wait_for_manage_users(wait)

        for row_index in range(start_row, len(rows)):
            row = rows[row_index]
            email = (row.get(email_field) or "").strip()
            row_label = (row.get("Timestamp") or row.get("Name") or row.get("name") or "").strip()
            row_name_text = row_label if row_label else "(no label)"
            if not email:
                print(f"[SKIP] row={row_index} row_name={row_name_text} email is empty")
                continue

            try:
                _wait_for_manage_users(wait)
                _open_add_user_form(driver, wait)
                _submit_user(driver, wait, email)
                _finish_success(driver, wait)
                added_count += 1
                print(f"[ADDED] row={row_index} row_name={row_name_text} email={email}")
            except TimeoutException:
                failed_count += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_path = Path(f"add_user_failure_row_{row_index}_{timestamp}.png")
                html_path = Path(f"add_user_failure_row_{row_index}_{timestamp}.html")
                driver.save_screenshot(str(shot_path))
                html_path.write_text(driver.page_source, encoding="utf-8")
                print(f"[FAILED] row={row_index} row_name={row_name_text} email={email} (timeout)")
                print(f"Saved debug screenshot: {shot_path}")
                print(f"Saved debug HTML: {html_path}")
                # Try to recover back to Manage Users page and continue.
                driver.get(MANAGE_USERS_URL)

    finally:
        print(f"Summary: added={added_count}, failed={failed_count}")
        driver.quit()


if __name__ == "__main__":
    main()
