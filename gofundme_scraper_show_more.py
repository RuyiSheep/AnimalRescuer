"""
GoFundMe Scraper - FINAL WORKING VERSION
- Clicks "Show more" button (not pagination)
- Handles "hrs ago" format (returns 0 days)
- Extracts: url, image_url, amount_raised, description, days_running
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import csv
import random
import re
from typing import List, Dict
from datetime import datetime

class GoFundMeFinalScraper:
    def __init__(self, headless=True):
        self.campaign_urls = set()
        self.campaigns = []
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print("✓ Chrome driver initialized")
    
    def random_delay(self, min_seconds=2, max_seconds=4):
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    # ========== PHASE 1: COLLECT URLs WITH "SHOW MORE" ==========
    
    def click_show_more(self) -> bool:
        """Click the 'Show more' button. Returns True if successful."""
        try:
            # Scroll to bottom first
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Try to find and click "Show more" button
            try:
                # XPath to find button with "Show more" text
                button = self.driver.find_element(By.XPATH, '//button[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show more")]')
                
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                time.sleep(1)
                
                # Click it
                button.click()
                print("    ✓ Clicked 'Show more'")
                return True
            except:
                # Fallback: find any button with "more" text
                buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for button in buttons:
                    if 'more' in button.text.lower():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        button.click()
                        print(f"    ✓ Clicked: '{button.text}'")
                        return True
            
            return False
            
        except Exception as e:
            return False
    
    def extract_visible_urls(self) -> List[str]:
        """Extract all currently visible campaign URLs"""
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/f/"]')
            
            urls = []
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/f/' in href:
                        clean_url = href.split('?')[0].rstrip('/')
                        if clean_url not in urls:
                            urls.append(clean_url)
                except:
                    continue
            
            return urls
        except:
            return []
    
    def collect_all_urls(self, max_campaigns=100):
        """Collect URLs by clicking 'Show more' button"""
        print("\n" + "=" * 80)
        print(f"PHASE 1: Collecting {max_campaigns} URLs via 'Show more' button")
        print("=" * 80)
        
        self.setup_driver()
        
        url = "https://www.gofundme.com/discover/animal-fundraiser"
        print(f"\nLoading: {url}\n")
        
        try:
            self.driver.get(url)
            time.sleep(4)
            
            # Initial scroll
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            attempts = 0
            no_new_count = 0
            
            while len(self.campaign_urls) < max_campaigns and attempts <= 100:
                # Get visible URLs
                visible_urls = self.extract_visible_urls()
                new_urls = [u for u in visible_urls if u not in self.campaign_urls]
                
                if new_urls:
                    print(f"[Attempt {attempts + 1}]")
                    print(f"  Visible: {len(visible_urls)} | New: {len(new_urls)} | Total: {len(self.campaign_urls) + len(new_urls)}")
                    
                    # Add new URLs
                    for u in new_urls:
                        self.campaign_urls.add(u)
                    
                    no_new_count = 0
                else:
                    no_new_count += 1
                    print(f"[Attempt {attempts + 1}] No new URLs (strike {no_new_count}/3)")
                
                # Stop conditions
                if len(self.campaign_urls) >= max_campaigns:
                    print(f"\n✓ Reached {max_campaigns} URLs!")
                    break
                
                if no_new_count >= 3:
                    print(f"\n✗ No new URLs for 3 attempts")
                    break
                
                # Click "Show more"
                if not self.click_show_more():
                    print("    ✗ 'Show more' button not found")
                    # Try scrolling anyway
                    for i in range(3):
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                
                attempts += 1
                time.sleep(3)  # Wait for content to load
            
        finally:
            if self.driver:
                self.driver.quit()
                print(f"\n✓ Browser closed")
        
        urls_list = list(self.campaign_urls)[:max_campaigns]
        print(f"\n{'=' * 80}")
        print(f"✓ Phase 1: Collected {len(urls_list)} unique URLs")
        print("=" * 80)
        
        return urls_list
    
    # ========== PHASE 2: EXTRACT DETAILS ==========
    
    def extract_days_running(self) -> str:
        """Extract days - handles 'X d ago', 'X hrs ago', and 'Month Day, Year'"""
        try:
            # Find created element
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, 'span.m-campaign-byline-created')
                text = elem.text.strip()
            except:
                # Fallback to page text
                text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Pattern 1: "X hrs ago" → 0 days
            if re.search(r'(\d+)\s*hrs?\s+ago', text, re.IGNORECASE):
                return '0'
            
            # Pattern 2: "X d ago" → extract number
            days_match = re.search(r'(\d+)\s*d(?:ays?)?\s+ago', text, re.IGNORECASE)
            if days_match:
                return days_match.group(1)
            
            # Pattern 3: "Month Day, Year" → calculate
            date_match = re.search(r'Created\s+([A-Za-z]+)\s+(\d+)(?:st|nd|rd|th)?,?\s+(\d{4})', text)
            if date_match:
                month_name = date_match.group(1)
                day = date_match.group(2)
                year = date_match.group(3)
                
                try:
                    date_str = f"{month_name} {day}, {year}"
                    created_date = datetime.strptime(date_str, "%B %d, %Y")
                    today = datetime(2025, 10, 26)
                    days_diff = (today - created_date).days
                    return str(days_diff) if days_diff >= 0 else 'Unknown'
                except:
                    pass
            
            return 'Unknown'
            
        except:
            return 'Unknown'
    
    def extract_campaign_details(self, url: str, index: int, total: int) -> Dict:
        """Extract details from individual campaign page"""
        try:
            campaign_id = url.split('/f/')[-1]
            print(f"  [{index}/{total}] {campaign_id[:40]}...", end=" ", flush=True)
            
            self.driver.get(url)
            time.sleep(2.5)
            
            data = {'url': url}
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # 1. IMAGE URL
            try:
                img_meta = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:image"]')
                data['image_url'] = img_meta.get_attribute('content')
            except:
                data['image_url'] = ''
            
            # 2. AMOUNT RAISED
            try:
                amounts = re.findall(r'\$[\d,]+', page_text)
                if amounts:
                    amounts_numeric = [int(a.replace('$', '').replace(',', '')) for a in amounts]
                    data['amount_raised'] = str(max(amounts_numeric))
                else:
                    data['amount_raised'] = '0'
            except:
                data['amount_raised'] = '0'
            
            # 3. DESCRIPTION
            try:
                desc_selectors = [
                    'div[class*="o-campaign-description"]',
                    'div[class*="campaign-description"]',
                    'meta[property="og:description"]'
                ]
                
                description = ''
                for selector in desc_selectors:
                    try:
                        if 'meta' in selector:
                            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            description = elem.get_attribute('content')
                        else:
                            elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                            description = elem.text.strip()
                        
                        if description and len(description) > 20:
                            break
                    except:
                        continue
                
                data['description'] = description[:500] if description else ''
            except:
                data['description'] = ''
            
            # 4. DAYS RUNNING
            data['days_running'] = self.extract_days_running()
            
            print(f"${data['amount_raised']} | {data['days_running']} days")
            
            return data
            
        except Exception as e:
            print(f"Error: {str(e)[:30]}")
            return {
                'url': url,
                'image_url': '',
                'amount_raised': '0',
                'description': '',
                'days_running': 'Unknown'
            }
    
    def extract_all_details(self, urls: List[str]):
        """Extract details from all URLs"""
        print("\n" + "=" * 80)
        print(f"PHASE 2: Extracting details from {len(urls)} campaigns")
        print("=" * 80)
        print("Fields: url, image_url, amount_raised, description, days_running\n")
        
        self.setup_driver()
        
        try:
            for i, url in enumerate(urls, 1):
                campaign_data = self.extract_campaign_details(url, i, len(urls))
                self.campaigns.append(campaign_data)
                
                if i % 25 == 0:
                    with_days = sum(1 for c in self.campaigns if c.get('days_running') != 'Unknown')
                    print(f"\n  Progress: {i}/{len(urls)} | Days: {with_days}/{i} ({with_days/i*100:.0f}%)\n")
                
                self.random_delay(2, 4)
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted! Saving {len(self.campaigns)} campaigns...")
        finally:
            if self.driver:
                self.driver.quit()
        
        print("\n" + "=" * 80)
        print(f"✓ Phase 2: Extracted {len(self.campaigns)} campaigns")
        print("=" * 80)
    
    # ========== SAVE ==========
    
    def save_to_csv(self, filename='gofundme_campaigns_final.csv'):
        if not self.campaigns:
            return
        
        keys = ['url', 'image_url', 'amount_raised', 'description', 'days_running']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.campaigns)
        
        print(f"\n✓ Saved to {filename}")
    
    def save_to_json(self, filename='gofundme_campaigns_final.json'):
        if not self.campaigns:
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.campaigns, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved to {filename}")


def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  GoFundMe Scraper - FINAL VERSION                        ║
    ║  ✓ Clicks "Show more" button (not pagination)            ║
    ║  ✓ Handles "hrs ago" format (0 days)                     ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Configuration
    MAX_CAMPAIGNS = 1100
    HEADLESS = True
    
    print(f"Configuration:")
    print(f"  Target: {MAX_CAMPAIGNS} campaigns")
    print(f"  Headless: {HEADLESS}")
    print(f"  Time: ~15 minutes total\n")
    
    scraper = GoFundMeFinalScraper(headless=HEADLESS)
    
    # PHASE 1: Click "Show more" to collect URLs
    urls = scraper.collect_all_urls(max_campaigns=MAX_CAMPAIGNS)
    
    if not urls:
        print("\n✗ No URLs collected")
        return
    
    # PHASE 2: Extract details
    scraper.extract_all_details(urls)
    
    # Save
    if scraper.campaigns:
        scraper.save_to_csv()
        scraper.save_to_json()
        
        print("\n" + "=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print(f"\nScraped {len(scraper.campaigns)} campaigns")
        
        # Sample
        print(f"\nSample:")
        for i, c in enumerate(scraper.campaigns[:3], 1):
            print(f"\n[{i}] ${c['amount_raised']} | {c['days_running']} days")
            print(f"    {c['url'].split('/f/')[-1][:50]}")
        
        # Stats
        total = sum(int(c['amount_raised']) for c in scraper.campaigns if c['amount_raised'].isdigit())
        with_days = sum(1 for c in scraper.campaigns if c['days_running'] != 'Unknown')
        with_desc = sum(1 for c in scraper.campaigns if c['description'])
        
        print(f"\n📊 Quality:")
        print(f"  Total raised: ${total:,}")
        print(f"  Days extracted: {with_days}/{len(scraper.campaigns)} ({with_days/len(scraper.campaigns)*100:.0f}%)")
        print(f"  Descriptions: {with_desc}/{len(scraper.campaigns)} ({with_desc/len(scraper.campaigns)*100:.0f}%)")
    else:
        print("\n✗ No campaigns")


if __name__ == "__main__":
    main()
