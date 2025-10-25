# GoFundMe Animal Fundraiser Scraper

## ⚠️ IMPORTANT DISCLAIMER

**This script is for EDUCATIONAL PURPOSES ONLY.**

- ❌ Violates GoFundMe's Terms of Service
- ❌ May result in IP bans or legal action
- ❌ Not intended for commercial use
- ✅ Use responsibly with proper rate limiting
- ✅ Consider contacting GoFundMe for official data access

## What It Does

Scrapes animal fundraiser campaigns from GoFundMe and extracts:
- 🖼️ Image URLs
- 📝 Campaign title and description
- 💰 Amount raised
- 📅 Campaign duration (days running)
- 🔗 Campaign URL

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python gofundme_scraper.py
```

By default, it scrapes 100 campaigns. To change this, edit line 225:

```python
campaigns = scraper.scrape_campaigns(max_campaigns=1000)  # Change to desired number
```

### Output Files

The scraper creates two files:
- `gofundme_animal_campaigns.csv` - Easy to import into Excel/Google Sheets
- `gofundme_animal_campaigns.json` - Structured data for further processing

### Customization

```python
from gofundme_scraper import GoFundMeScraper

# Create scraper instance
scraper = GoFundMeScraper()

# Scrape with custom settings
campaigns = scraper.scrape_campaigns(
    max_campaigns=500,  # Number of campaigns to scrape
    max_pages=25        # Maximum pages to check
)

# Save in your preferred format
scraper.save_to_csv('my_output.csv')
scraper.save_to_json('my_output.json')
```

## How It Works

1. **Page Scraping**: Fetches campaign listing pages from the animal category
2. **Data Extraction**: Parses HTML to extract basic campaign info
3. **Detail Fetching**: Visits individual campaign pages for full descriptions
4. **Rate Limiting**: Includes random delays (2-10 seconds) to avoid detection
5. **Export**: Saves data to CSV and JSON formats

## Important Notes

### Rate Limiting
- 2-5 second delays between campaign cards
- 3-6 second delays when visiting individual pages  
- 5-10 second delays between category pages
- **Recommendation**: Use even longer delays for large scrapes

### Detection Avoidance
- Uses realistic browser headers
- Implements random delays
- Session management to maintain cookies

### If You Get Blocked
1. Wait 24-48 hours before trying again
2. Use a VPN to change your IP address
3. Reduce `max_campaigns` to smaller batches
4. Increase delay times in `random_delay()` calls

## Ethical Alternatives

Instead of scraping, consider:
1. **Official API**: Contact GoFundMe for API access (if available for researchers)
2. **Research Partnerships**: Reach out to GoFundMe's data team
3. **Public Datasets**: Check Kaggle or academic repositories for existing data
4. **Manual Collection**: For small samples, manual collection respects ToS

## Troubleshooting

### "No campaigns found"
- The HTML structure may have changed
- Check if the URL is still valid
- Inspect page source to update CSS selectors

### "Connection timeout"
- Your IP may be rate-limited
- Try again later or use a VPN
- Increase timeout values in the code

### Missing data fields
- Some campaigns may not have all fields
- The script handles missing data gracefully
- Check the output files for what was captured

## Legal Considerations

Web scraping legality varies by jurisdiction and use case:
- ✅ Generally OK: Personal research, non-commercial analysis
- ⚠️ Gray area: Academic research (get permission)
- ❌ Not OK: Commercial use, republishing data, overwhelming servers

**Always check the website's Terms of Service and robots.txt file.**

## Contributing

This is an educational project. Improvements welcome:
- Better error handling
- More robust HTML parsing
- Additional data fields
- Export format options

## License

MIT License - For educational purposes only

---

**Remember**: Just because you *can* scrape something doesn't mean you *should*. 
Consider the ethical implications and respect the platform's resources.
