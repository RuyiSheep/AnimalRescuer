"""
GoFundMe Animal Fundraiser Scraper
WARNING: This script is for EDUCATIONAL PURPOSES ONLY
- Violates GoFundMe Terms of Service
- Use responsibly with rate limiting
- Consider official API or data partnership instead
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import csv
import re
from datetime import datetime
from typing import List, Dict
import random

class GoFundMeScraper:
    def __init__(self):
        self.base_url = "https://www.gofundme.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.campaigns = []
        
    def random_delay(self, min_seconds=2, max_seconds=5):
        """Implement random delays to appear more human-like"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def extract_campaign_data(self, campaign_element) -> Dict:
        """Extract data from a single campaign card"""
        try:
            data = {}
            
            # Extract campaign URL and ID
            link = campaign_element.find('a', class_=re.compile('.*Campaign.*'))
            if link and link.get('href'):
                data['url'] = self.base_url + link['href']
                data['id'] = link['href'].split('/')[-1]
            else:
                return None
            
            # Extract image URL
            img = campaign_element.find('img')
            if img:
                data['image_url'] = img.get('src') or img.get('data-src', '')
            else:
                data['image_url'] = ''
            
            # Extract title/description
            title_elem = campaign_element.find('div', class_=re.compile('.*title.*|.*heading.*', re.IGNORECASE))
            if not title_elem:
                title_elem = campaign_element.find('h2') or campaign_element.find('h3')
            data['title'] = title_elem.get_text(strip=True) if title_elem else ''
            
            # Extract amount raised
            amount_elem = campaign_element.find('span', class_=re.compile('.*raised.*|.*amount.*', re.IGNORECASE))
            if not amount_elem:
                # Look for any element with $ symbol
                amount_elem = campaign_element.find(text=re.compile(r'\$[\d,]+'))
            
            if amount_elem:
                amount_text = amount_elem if isinstance(amount_elem, str) else amount_elem.get_text()
                # Extract numeric value
                amount_match = re.search(r'\$?([\d,]+)', amount_text)
                data['amount_raised'] = amount_match.group(1).replace(',', '') if amount_match else '0'
            else:
                data['amount_raised'] = '0'
            
            return data
            
        except Exception as e:
            print(f"Error extracting campaign data: {e}")
            return None
    
    def get_campaign_details(self, campaign_url: str) -> Dict:
        """Fetch detailed information from individual campaign page"""
        try:
            print(f"Fetching details from: {campaign_url}")
            self.random_delay(3, 6)  # Longer delay for individual pages
            
            response = self.session.get(campaign_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            details = {}
            
            # Try to find JSON-LD structured data (most reliable)
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    structured_data = json.loads(json_ld.string)
                    details['description'] = structured_data.get('description', '')
                except:
                    pass
            
            # Fallback: Extract description from page
            if not details.get('description'):
                desc_elem = soup.find('div', class_=re.compile('.*description.*|.*story.*', re.IGNORECASE))
                if desc_elem:
                    details['description'] = desc_elem.get_text(strip=True)[:500]  # Limit length
                else:
                    details['description'] = ''
            
            # Extract campaign duration/creation date
            date_elem = soup.find(text=re.compile(r'Created|Started'))
            if date_elem:
                # Look for date near this text
                parent = date_elem.find_parent()
                if parent:
                    date_text = parent.get_text()
                    details['created_date'] = date_text
            else:
                details['created_date'] = 'Unknown'
            
            # Calculate days running (if possible)
            meta_created = soup.find('meta', property='article:published_time')
            if meta_created:
                created_date = meta_created.get('content')
                try:
                    created = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    days_running = (datetime.now() - created.replace(tzinfo=None)).days
                    details['days_running'] = days_running
                except:
                    details['days_running'] = 'Unknown'
            else:
                details['days_running'] = 'Unknown'
            
            return details
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching campaign details: {e}")
            return {}
    
    def scrape_category_page(self, page_num=1) -> List[Dict]:
        """Scrape campaigns from a category page"""
        url = f"https://www.gofundme.com/discover/animal-fundraiser?page={page_num}"
        
        try:
            print(f"Scraping page {page_num}: {url}")
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find campaign cards - the class names may vary
            campaigns = soup.find_all('div', class_=re.compile('.*campaign.*|.*card.*|.*tile.*', re.IGNORECASE))
            
            # Alternative: look for links containing /f/
            if not campaigns:
                campaign_links = soup.find_all('a', href=re.compile(r'/f/'))
                campaigns = [link.find_parent('div') for link in campaign_links if link.find_parent('div')]
            
            page_campaigns = []
            
            for campaign in campaigns:
                campaign_data = self.extract_campaign_data(campaign)
                if campaign_data and campaign_data.get('url'):
                    page_campaigns.append(campaign_data)
            
            print(f"Found {len(page_campaigns)} campaigns on page {page_num}")
            return page_campaigns
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page_num}: {e}")
            return []
    
    def scrape_campaigns(self, max_campaigns=1000, max_pages=50):
        """Main method to scrape multiple campaigns"""
        print(f"Starting scrape for up to {max_campaigns} campaigns...")
        print("=" * 60)
        
        page = 1
        total_scraped = 0
        
        while total_scraped < max_campaigns and page <= max_pages:
            # Scrape category page
            page_campaigns = self.scrape_category_page(page)
            
            if not page_campaigns:
                print(f"No campaigns found on page {page}. Stopping.")
                break
            
            # Get detailed info for each campaign
            for campaign in page_campaigns:
                if total_scraped >= max_campaigns:
                    break
                
                details = self.get_campaign_details(campaign['url'])
                campaign.update(details)
                
                self.campaigns.append(campaign)
                total_scraped += 1
                
                print(f"[{total_scraped}/{max_campaigns}] Scraped: {campaign.get('title', 'Unknown')[:50]}")
            
            page += 1
            self.random_delay(5, 10)  # Longer delay between pages
        
        print("=" * 60)
        print(f"Scraping complete! Total campaigns: {len(self.campaigns)}")
        return self.campaigns
    
    def save_to_csv(self, filename='gofundme_animal_campaigns.csv'):
        """Save scraped data to CSV file"""
        if not self.campaigns:
            print("No campaigns to save!")
            return
        
        keys = ['id', 'title', 'url', 'image_url', 'amount_raised', 
                'description', 'created_date', 'days_running']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.campaigns)
        
        print(f"Data saved to {filename}")
    
    def save_to_json(self, filename='gofundme_animal_campaigns.json'):
        """Save scraped data to JSON file"""
        if not self.campaigns:
            print("No campaigns to save!")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.campaigns, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")


def main():
    """Main execution function"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  GoFundMe Animal Fundraiser Scraper                      ║
    ║  ⚠️  FOR EDUCATIONAL PURPOSES ONLY                       ║
    ║  This violates GoFundMe's Terms of Service               ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Initialize scraper
    scraper = GoFundMeScraper()
    
    # Scrape campaigns (adjust max_campaigns as needed)
    campaigns = scraper.scrape_campaigns(max_campaigns=100)  # Start with 100 for testing
    
    # Save results
    if campaigns:
        scraper.save_to_csv()
        scraper.save_to_json()
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total campaigns scraped: {len(campaigns)}")
        
        if campaigns:
            total_raised = sum(int(c.get('amount_raised', 0)) for c in campaigns if c.get('amount_raised', '').isdigit())
            print(f"Total amount raised: ${total_raised:,}")
            print(f"\nSample campaign:")
            sample = campaigns[0]
            print(f"  Title: {sample.get('title', 'N/A')}")
            print(f"  Raised: ${sample.get('amount_raised', 'N/A')}")
            print(f"  Days running: {sample.get('days_running', 'N/A')}")
            print(f"  URL: {sample.get('url', 'N/A')}")
    else:
        print("No campaigns were scraped. Check your connection or the site structure may have changed.")


if __name__ == "__main__":
    main()
