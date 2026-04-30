"""Bulk-remove ThingSpeak license users through the MathWorks License Center UI.

Flow:
1. Launches the browser automatically and navigates to the login page
2. Complete Canvas/MathWorks login manually
3. Script removes all current users one by one

Troubleshoot:
- Matlab website does not like too many repeated requests - so might need to space out if we have a lot of users
- Sometimes the website just detects botting and refueses to load - Cntrl+R to reload usually works
- If nothing else works, try a few minutes later
"""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
	ElementClickInterceptedException,
	JavascriptException,
	NoSuchElementException,
	StaleElementReferenceException,
	TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_URL = "https://www.mathworks.com/licensecenter/licenses/41012247/8966129/end_users"
TIMEOUT_SECONDS = 20
HEADLESS = False
RETRIES = 3
INTER_DELAY_SECONDS = 0.5
MIN_JITTER_SECONDS = 0.05
MAX_JITTER_SECONDS = 0.1
MANAGEMENT_TABLE_AREA_ID = "tab_content_area"
REMOVE_ICON_LINK_XPATH = "//span[contains(@class,'icon-remove-circle-reverse')]/ancestor::a[1]"
REMOVE_HEADER_XPATH = "//th[contains(normalize-space(),'Remove User')]"
REMOVE_CONFIRM_BUTTON_ID = "remove_user_btn"
DONE_BUTTON_XPATH = "//a[normalize-space()='Done' and @href='https://www.mathworks.com/licensecenter/licenses/41012247/8966129/end_users']"


class ThingSpeakRemover:
	"""Handles resilient remove-all automation for MathWorks license end users."""

	def __init__(
		self,
	) -> None:
		self.url = DEFAULT_URL
		self.timeout = TIMEOUT_SECONDS
		self.retries = RETRIES
		self.inter_delay = INTER_DELAY_SECONDS

		options = webdriver.ChromeOptions()
		if HEADLESS:
			options.add_argument("--headless=new")
		options.add_argument("--start-maximized")
		options.add_argument("--disable-notifications")
		options.add_argument("--disable-popup-blocking")

		self.driver = webdriver.Chrome(options=options)
		self.wait = WebDriverWait(self.driver, self.timeout)

		self.removed_count = 0
		self.failed_count = 0

	def open_and_wait_for_manual_login(self) -> None:
		self.driver.get(self.url)
		print("Browser opened. Complete Canvas/MathWorks login in that browser window.")
		input("Press Enter here once you are on the Manage Users page... ")
		# Force the known users page in case login returns to a different tab/state.
		self.driver.get(self.url)
		self._wait_for_management_page()
		print("[PAGE] Management page ready.")

	def _wait_for_management_page(self) -> None:
		self.wait.until(EC.presence_of_element_located((By.ID, MANAGEMENT_TABLE_AREA_ID)))
		self.wait.until(EC.presence_of_element_located((By.XPATH, REMOVE_HEADER_XPATH)))
		self.wait.until(EC.presence_of_element_located((By.XPATH, REMOVE_ICON_LINK_XPATH)))

	def _wait_for_remove_confirmation_page(self) -> None:
		self.wait.until(EC.presence_of_element_located((By.ID, REMOVE_CONFIRM_BUTTON_ID)))
		self.wait.until(EC.visibility_of_element_located((By.ID, REMOVE_CONFIRM_BUTTON_ID)))

	def _open_remove_confirmation_page(self, link: WebElement) -> None:
		print("[ACTION] Clicking circle-cross remove icon from management page.")
		self._click_element(self.wait.until(EC.element_to_be_clickable(link)))
		# The icon click uses AJAX (data-sremote). If replacement lags/fails, force navigation.
		try:
			WebDriverWait(self.driver, 4).until(
				EC.presence_of_element_located((By.ID, REMOVE_CONFIRM_BUTTON_ID))
			)
		except TimeoutException:
			remove_href = link.get_attribute("href")
			if not remove_href:
				raise
			print("[SYNC] Confirm page not loaded via AJAX; opening remove URL directly.")
			self.driver.get(remove_href)
		self._wait_for_remove_confirmation_page()

	def _wait_for_success_page(self) -> None:
		self.wait.until(EC.presence_of_element_located((By.XPATH, DONE_BUTTON_XPATH)))
		self.wait.until(EC.element_to_be_clickable((By.XPATH, DONE_BUTTON_XPATH)))

	def _first_remove_icon_link(self) -> Optional[WebElement]:
		icon_links = self.driver.find_elements(By.XPATH, REMOVE_ICON_LINK_XPATH)
		return icon_links[0] if icon_links else None

	def _click_element(self, element: WebElement) -> None:
		try:
			self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
		except JavascriptException:
			pass
		try:
			element.click()
		except ElementClickInterceptedException:
			self.driver.execute_script("arguments[0].click();", element)

	@staticmethod
	def _tiny_jitter() -> None:
		time.sleep(random.uniform(MIN_JITTER_SECONDS, MAX_JITTER_SECONDS))

	def _extract_row_identity_from_link(self, link: WebElement) -> tuple[str, str]:
		row = link.find_element(By.XPATH, "./ancestor::tr")
		cells = row.find_elements(By.TAG_NAME, "td")
		if len(cells) < 3:
			title = (link.get_attribute("title") or "").replace("Remove User", "").strip()
			return title or "<unknown>", ""
		first_name = cells[0].text.strip()
		last_name = cells[1].text.strip()
		email = cells[2].text.strip()
		full_name = (first_name + " " + last_name).strip()
		return full_name or "<unknown>", email

	def _click_confirm_remove(self) -> None:
		self._wait_for_remove_confirmation_page()
		print("[PAGE] On remove confirmation page.")
		remove_btn = self.wait.until(EC.presence_of_element_located((By.ID, REMOVE_CONFIRM_BUTTON_ID)))
		btn_enabled = remove_btn.is_enabled()
		btn_displayed = remove_btn.is_displayed()
		print(f"[DEBUG] remove_user_btn state: displayed={btn_displayed}, enabled={btn_enabled}")
		print("[ACTION] Clicking Remove User button (#remove_user_btn).")
		self._tiny_jitter()
		try:
			self._click_element(remove_btn)
		except (ElementClickInterceptedException, JavascriptException):
			pass

		# Ensure submission even if the button is present but blocked by overlays/transitions.
		self.driver.execute_script(
			"""
			const btn = document.getElementById('remove_user_btn');
			if (btn) {
			  btn.click();
			  const form = btn.closest('form');
			  if (form) {
			    form.submit();
			  }
			}
			"""
		)
		self._tiny_jitter()

	def _click_done(self) -> None:
		self._wait_for_success_page()
		print("[PAGE] On success page.")
		done_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, DONE_BUTTON_XPATH)))
		print("[ACTION] Clicking Done to return to management page.")
		self._tiny_jitter()
		self._click_element(done_btn)
		self._wait_for_management_page()
		print("[PAGE] Returned to management page.")
		self._tiny_jitter()

	def remove_one_user(self) -> bool:
		last_error = None
		for attempt in range(1, self.retries + 1):
			try:
				self._wait_for_management_page()
				link = self._first_remove_icon_link()
				if link is None:
					icons = self.driver.find_elements(By.XPATH, "//span[contains(@class,'icon-remove-circle-reverse')]")
					print(f"[INFO] Remove icon count detected: {len(icons)}")
					return False

				name, email = self._extract_row_identity_from_link(link)
				print(f"[REMOVE] {name} <{email}> (attempt {attempt}/{self.retries})")
				self._tiny_jitter()
				self._open_remove_confirmation_page(link)
				self._click_confirm_remove()
				self._click_done()

				self.removed_count += 1
				if self.inter_delay > 0:
					time.sleep(self.inter_delay)
				return True
			except (TimeoutException, StaleElementReferenceException, ElementClickInterceptedException) as exc:
				last_error = exc
				print(f"[WARN] Retryable error: {type(exc).__name__}; retrying...")
				if attempt < self.retries:
					time.sleep(min(1.5 * attempt, 5.0))
			except NoSuchElementException as exc:
				last_error = exc
				break

		self.failed_count += 1
		self._capture_failure_artifacts("remove_failure")
		raise RuntimeError(f"Failed to remove next user after {self.retries} retries: {last_error}") from last_error

	def remove_all(self) -> None:
		while True:
			removed = self.remove_one_user()
			if not removed:
				print("No removable users left.")
				break

	def _capture_failure_artifacts(self, prefix: str) -> None:
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		screenshot_path = Path(f"{prefix}_{timestamp}.png")
		html_path = Path(f"{prefix}_{timestamp}.html")
		self.driver.save_screenshot(str(screenshot_path))
		html_path.write_text(self.driver.page_source, encoding="utf-8")
		print(f"Saved debug screenshot: {screenshot_path}")
		print(f"Saved debug HTML: {html_path}")

	def close(self) -> None:
		self.driver.quit()


def main() -> None:
	manager = ThingSpeakRemover()

	try:
		manager.open_and_wait_for_manual_login()
		manager.remove_all()
	except KeyboardInterrupt:
		print("Interrupted by user (Ctrl+C).")
	finally:
		print(f"Summary: removed={manager.removed_count}, failed={manager.failed_count}")
		manager.close()


if __name__ == "__main__":
	main()
