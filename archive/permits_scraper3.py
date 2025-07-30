import re
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import csv

async def run():
    async with async_playwright() as p:
        # Launch browser with increased viewport for robustness
        browser = await p.chromium.launch(headless=False, args=["--window-size=1920,1080"])
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        print("Navigating to permit search page...")
        await page.goto("https://aca-prod.accela.com/HCFL/Cap/CapHome.aspx?TabName=Home&module=Building", timeout=60000, wait_until='domcontentloaded')
        print("Page loaded and settled.")

        # --- Calculate Yesterday's Date ---
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%m/%d/%Y")

        print(f"Searching for records from: {yesterday_str} to {yesterday_str}")

        # --- Date Input Selectors (CONFIRMED) ---
        start_date_input_selector = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate"
        end_date_input_selector = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate"

        try:
            print(f"Clearing and filling Start Date ({yesterday_str})...")
            await page.fill(start_date_input_selector, "")
            await page.fill(start_date_input_selector, yesterday_str)
            await page.press(start_date_input_selector, "Tab")

            print(f"Clearing and filling End Date ({yesterday_str})...")
            await page.fill(end_date_input_selector, "")
            await page.fill(end_date_input_selector, yesterday_str)
            await page.press(end_date_input_selector, "Tab")

            await page.wait_for_timeout(1000)

        except Exception as e:
            print(f"Error clearing/filling date fields: {e}")
            await browser.close()
            return

        # --- Click the Search Button (CONFIRMED SELECTOR) ---
        search_button_selector = "#ctl00_PlaceHolderMain_btnNewSearch"
        # Download button selector (CONFIRMED SELECTOR)
        download_button_selector = "#ctl00_PlaceHolderMain_dgvPermitList_gdvPermitList_gdvPermitListtop4btnExport"
        # Error message selectors (for general error checking)
        error_message_selector = "div.ACA_ErrorBox, div.validation-summary-errors, span.error-message, div:has-text('no results'), div:has-text('no records found')"
        results_table_selector = "#ctl00_PlaceHolderMain_gvSearchResults" # Still used for error check

        print(f"Waiting for search button with selector: {search_button_selector} to be visible...")
        try:
            await page.wait_for_selector(search_button_selector, timeout=30000)
            print("Search button found and is ready.")
        except Exception as e:
            print(f"Error: Search button not found or not ready within timeout. {e}")
            await browser.close()
            return

        print("Clicking search button...")
        try:
            await page.click(search_button_selector)

            # --- CRITICAL NEW STRATEGY: Wait for network idle, then FORCE RELOAD ---
            print("Waiting for page to become network idle after search click (max 60s)...")
            await page.wait_for_load_state('networkidle', timeout=60000)
            print("Page is network idle. Attempting a hard refresh to ensure elements are visible.")

            # This is the aggressive part: reload the page to make sure all elements re-render cleanly
            # If the search results are stored in the session or parameters, they should persist.
            await page.reload(wait_until='domcontentloaded', timeout=60000) # Reload and wait for DOM to be ready
            await page.wait_for_load_state('networkidle', timeout=60000) # Then wait for network to settle after reload
            await page.wait_for_timeout(2000) # Small pause for visual stability

            print("Page reloaded and settled. Attempting to find download button directly.")

        except Exception as e:
            print(f"Error during search click or page reload: {e}")
            await page.screenshot(path="click_reload_error_debug.png")
            
            # Re-check for error messages if timeout occurred
            error_box_locator = page.locator(error_message_selector).filter(has_text=re.compile(r"error|invalid|no records|no result|zero result", re.IGNORECASE))
            if await error_box_locator.is_visible():
                error_text = await error_box_locator.first.inner_text()
                print(f"\n!!! Detected error/no results message after timeout: '{error_text.strip()}' !!!")
                await page.screenshot(path="submission_error_screenshot.png")
            else:
                print("No explicit error/no results message found after reload, but page update failed.")
            await browser.close()
            return

        await page.screenshot(path="after_reload_debug.png")
        print("Screenshot 'after_reload_debug.png' taken.")

        # --- Check for 'No Results' explicitly in the table (before attempting download) ---
        # This is a final safeguard. If the table itself has a 'no records' message, then don't try download.
        no_results_in_table_locator = page.locator(results_table_selector).filter(has_text=re.compile(r"no records|no result|zero result", re.IGNORECASE))
        if await no_results_in_table_locator.is_visible():
            print(f"!!! Results table explicitly shows 'no records found'. No data to download. !!!")
            await browser.close()
            return

        # --- Proceed to Click the Download Button ---
        # We assume the download button should be visible/clickable after the refresh
        download_button_locator = page.locator(download_button_selector)


        print("Attempting to click download button and capture file...")
        try:
            # Wait for the download button to be actionable (visible, enabled) before clicking
            await download_button_locator.wait_for(state='visible', timeout=15000) # Generous timeout for button visibility
            print("Download button is confirmed visible for clicking.")

            async with page.expect_download(timeout=90000) as download_info: # Increased timeout for large downloads
                await download_button_locator.click()
            
            download = await download_info.value
            
            suggested_file_name = download.suggested_filename
            if not suggested_file_name:
                suggested_file_name = f"hillsborough_permits_download_{yesterday.strftime('%Y%m%d')}.csv"

            save_path = suggested_file_name
            await download.save_as(save_path)
            print(f"Successfully downloaded file to: {save_path}")

        except Exception as e:
            print(f"Error during file download: {e}.")
            print("This could be due to the download button not being clickable, or the download failing.")
            await page.wait_for_timeout(2000)
            await browser.close()
            return

        print("\n--- Download complete. ---")
        await browser.close()
        print("Browser closed.")

# Run the script
asyncio.run(run())