import re
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Keep headless=False for debugging
        page = await browser.new_page()

        print("Navigating to permit search page...")
        await page.goto("https://aca-prod.accela.com/HCFL/Cap/CapHome.aspx?TabName=Home&module=Building", timeout=60000, wait_until='networkidle')
        print("Page loaded and settled.")

        # --- Calculate Yesterday's Date ---
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%m/%d/%Y") # Format as MM/DD/YYYY

        print(f"Searching for records from: {yesterday_str}")

        # --- STEP 1: Input Yesterday's Date into Start and End Date Fields ---
        # *** YOU MUST VERIFY THESE IDS BY INSPECTING THE LIVE PAGE ***
        start_date_input_selector = "#ctl00_PlaceHolderMain_txtApplicationDate" # Common ID for single date input, or check for specific Start Date
        end_date_input_selector = "#ctl00_PlaceHolderMain_txtApplicationDateTo"   # Common ID for "To" date input if there are two

        # On your screenshot, it looks like there's a "Start Date" and "End Date" field.
        # Please inspect them for their exact IDs. Let's assume the following common pattern:
        # If there's only one "Application Date" field, you might need to find a specific "Search By" dropdown for date range.
        # For now, I'll assume common Accela pattern of two distinct date fields or one main date field.
        # Let's target the "Application Date" and "To" fields shown in your screenshot.

        # Based on visual guess from your screenshot (you NEED to verify these IDs!)
        application_date_start_id = "#ctl00_PlaceHolderMain_txtApplicationDate" # This is for "Start Date"
        application_date_end_id = "#ctl00_PlaceHolderMain_txtApplicationDateTo" # This is for "End Date"

        try:
            print(f"Filling Start Date ({yesterday_str})...")
            await page.fill(application_date_start_id, yesterday_str)
            print(f"Filling End Date ({yesterday_str})...")
            await page.fill(application_date_end_id, yesterday_str)
            await page.wait_for_timeout(1000) # Give it a moment to register input
        except Exception as e:
            print(f"Error filling date fields. Please verify their selectors: {e}")
            await browser.close()
            return

        # --- STEP 2: Click the Search Button ---
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
            # Use expect_navigation to wait for the page to update after clicking.
            async with page.expect_navigation(timeout=60000):
                await page.click(search_button_selector)
            print("Search button clicked and page navigation/update completed.")
        except Exception as e:
            print(f"Error clicking search button or waiting for navigation: {e}")
            await page.screenshot(path="click_error_debug.png")
            await browser.close()
            return

        # Optional: Take a screenshot after the click to see the results page
        await page.screenshot(path="after_click_debug.png")
        print("Screenshot 'after_click_debug.png' taken (should show results).")

        # --- STEP 3: Scrape Data and Handle Pagination ---
        results_table_selector = "#ctl00_PlaceHolderMain_gvSearchResults" # Verify this!
        all_scraped_results = []
        page_num = 1

        while True:
            print(f"\n--- Scraping Page {page_num} ---")
            try:
                await page.wait_for_selector(results_table_selector, state='visible', timeout=30000)
                print("Results table found.")
            except Exception as e:
                print(f"Error: Results table not found on page {page_num}. Ending pagination. {e}")
                break # Exit loop if table isn't found

            # Scrape rows from the current page
            rows = await page.query_selector_all(f"{results_table_selector} tbody tr")
            print(f"Found {len(rows)} potential permit rows on Page {page_num}.")

            if len(rows) < 2 and page_num == 1: # If only header or no data on first page
                print("No actual data rows found for the specified date range. Ending.")
                break
            elif len(rows) < 2 and page_num > 1: # No more data on subsequent pages
                print("No more data rows found. Ending pagination.")
                break

            for i, row in enumerate(rows):
                # Skip what looks like a header row if tbody contains it, or empty rows
                # A common heuristic is to check if the first cell contains "Record Number" or similar.
                first_cell_text = await row.query_selector("td:nth-child(1)")
                if first_cell_text and "Record Number" in await first_cell_text.inner_text():
                     continue # This is likely a header or filter row within tbody

                cells = await row.query_selector_all("td")

                if len(cells) < 5: # Basic check for incomplete rows
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
            # *** YOU MUST VERIFY THE SELECTOR FOR THE NEXT PAGE LINK/BUTTON ***
            # Common patterns:
            # - An 'a' tag with specific text like "Next" or ">>"
            # - An 'a' tag with a specific class or ID, or a title like "Next Page"
            # - An 'a' tag whose 'onclick' event navigates
            # - A span or a with a specific class that becomes disabled on the last page.

            # Example selector for "Next" button/link
            # Inspect the "Next" link in the pagination part of the table
            next_page_selector = "a[title='Next Page'], a:has-text('Next')" # Try these first, or find a specific ID
            # If the "Next" button has an ID, use it for robustness, e.g., "#ctl00_PlaceHolderMain_lnkNext"

            next_button = await page.query_selector(next_page_selector)

            if next_button and await next_button.is_enabled() and await next_button.is_visible():
                page_num += 1
                print(f"Clicking 'Next' for Page {page_num}...")
                await next_button.click()
                await page.wait_for_load_state('networkidle', timeout=60000) # Wait for next page to load
                await page.wait_for_timeout(2000) # Small pause for rendering stability
            else:
                print("No 'Next' button found or it's disabled. Ending pagination.")
                break # Exit loop if no next button or it's disabled

        print(f"\n--- Finished Scraping. Total Records: {len(all_scraped_results)} ---")
        if not all_scraped_results:
            print("No permit results found for yesterday's date.")
        else:
            for r in all_scraped_results:
                print(r)

        await browser.close()
        print("Browser closed.")

# Run the script
asyncio.run(run())