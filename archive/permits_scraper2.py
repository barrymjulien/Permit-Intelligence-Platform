import re
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Keep headless=False for testing
        page = await browser.new_page()

        print("Navigating to permit search page...")
        await page.goto("https://aca-prod.accela.com/HCFL/Cap/CapHome.aspx?TabName=Home&module=Building", timeout=60000, wait_until='networkidle')
        print("Page loaded and settled.")

        # --- Calculate Yesterday's Date ---
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%m/%d/%Y") # Confirmed: MM/DD/YYYY is the correct input format

        print(f"Searching for records from: {yesterday_str} to {yesterday_str}")

        # --- Input Yesterday's Date into Start and End Date Fields ---
        start_date_input_selector = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate"
        end_date_input_selector = "#ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate"

        try:
            print(f"Clearing and filling Start Date ({yesterday_str})...")
            # Clear the field first
            await page.fill(start_date_input_selector, "") # Fill with empty string to clear
            # Then fill with the correct date
            await page.fill(start_date_input_selector, yesterday_str)
            await page.press(start_date_input_selector, "Tab") # Tab out of the field to trigger validation/closure of date picker

            print(f"Clearing and filling End Date ({yesterday_str})...")
            # Clear the field first
            await page.fill(end_date_input_selector, "") # Fill with empty string to clear
            # Then fill with the correct date
            await page.fill(end_date_input_selector, yesterday_str)
            await page.press(end_date_input_selector, "Tab") # Tab out of the field
            
            await page.wait_for_timeout(1000) # Small pause for UI to register

        except Exception as e:
            print(f"Error clearing/filling date fields: {e}")
            await browser.close()
            return

        # --- Click the Search Button ---
        search_button_selector = "#ctl00_PlaceHolderMain_btnNewSearch"

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
            async with page.expect_navigation(timeout=60000):
                await page.click(search_button_selector)
            print("Search button clicked and page navigation/update completed.")
        except Exception as e:
            print(f"Error clicking search button or waiting for navigation: {e}")
            await page.screenshot(path="click_error_debug.png")
            await browser.close()
            return

        await page.screenshot(path="after_click_debug.png")
        print("Screenshot 'after_click_debug.png' taken (should show results).")

        # --- Check for the error message after submission ---
        # Look for general error messages, specifically the red box
        error_message_selector = "div.ACA_ErrorBox, div.validation-summary-errors, span.error-message"
        error_box_locator = page.locator(error_message_selector).filter(has_text=re.compile(r"error|invalid", re.IGNORECASE))

        if await error_box_locator.is_visible():
            error_text = await error_box_locator.first.inner_text()
            print(f"\n!!! Error message detected on page: '{error_text.strip()}' !!!")
            await page.screenshot(path="submission_error_screenshot.png") # Capture the error
            await browser.close()
            return # Exit early if we hit a submission error

        # --- Scrape Data and Handle Pagination (only if no error) ---
        results_table_selector = "#ctl00_PlaceHolderMain_gvSearchResults"
        all_scraped_results = []
        page_num = 1

        while True:
            print(f"\n--- Scraping Page {page_num} ---")
            try:
                await page.wait_for_selector(results_table_selector, state='visible', timeout=30000)
                print("Results table found.")
            except Exception as e:
                print(f"Error: Results table not found on page {page_num}. Ending pagination. {e}")
                break

            data_rows = await page.locator(f"{results_table_selector} tbody tr").all()
            print(f"Found {len(data_rows)} potential permit rows on Page {page_num}.")

            if len(data_rows) == 0 and page_num == 1:
                print("No records found for the specified date range. Ending.")
                break
            elif len(data_rows) == 0 and page_num > 1:
                print("No more data rows found. Ending pagination.")
                break

            for i, row in enumerate(data_rows):
                cells = await row.locator("td").all()

                if len(cells) < 5:
                    continue

                try:
                    permit_number = await cells[0].inner_text()
                    address = await cells[1].inner_text()
                    description = await cells[2].inner_text()
                    status = await cells[3].inner_text()
                    date = await cells[4].inner_text()

                    zip_match = re.search(r"\b\d{5}\b", address)
                    zip_code = zip_match.group() if zip_match else "Unknown"

                    all_scraped_results.append({
                        "permit_number": permit_number.strip(),
                        "address": address.strip(),
                        "zip": zip_code,
                        "description": description.strip(),
                        "status": status.strip(),
                        "date": date.strip()
                    })
                except Exception as e:
                    print(f"Error processing row {i} on page {page_num}: {e}. Row content: {await row.inner_text()}")

            # --- Pagination Logic ---
            # Targeting a:has-text('Next') is often reliable for Accela
            # The '>>' selector is also common: a:has-text('>>')
            next_page_link_selector = "a:has-text('Next'), a:has-text('>>')"
            next_button_locator = page.locator(next_page_link_selector).last # Get the last one if multiple "Next" links exist

            if await next_button_locator.is_visible() and await next_button_locator.is_enabled():
                href_attr = await next_button_locator.get_attribute('href')
                if href_attr and 'javascript:void(0)' not in href_attr and 'return false;' not in href_attr:
                    page_num += 1
                    print(f"Clicking 'Next' for Page {page_num}...")
                    async with page.expect_navigation(timeout=60000):
                        await next_button_locator.click()
                    await page.wait_for_timeout(1000)
                else:
                    print("Next pagination link found but appears disabled/inactive. Ending pagination.")
                    break
            else:
                print("No active 'Next' pagination link found. Ending pagination.")
                break

        print(f"\n--- Finished Scraping. Total Records: {len(all_scraped_results)} ---")
        if not all_scraped_results:
            print("No permit results found for yesterday's date.")
        else:
            for r in all_scraped_results[:20]:
                print(r)
            if len(all_scraped_results) > 20:
                print(f" ... and {len(all_scraped_results) - 20} more records.")

        await browser.close()
        print("Browser closed.")

asyncio.run(run())