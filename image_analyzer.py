"""
Image Analysis with Google Vision API and Azure Computer Vision
Analyzes images from GoFundMe campaigns to extract labels and descriptions
"""

import json
import csv
import time
import os
from typing import List, Dict, Optional
import requests
from datetime import datetime

# Google Cloud Vision
try:
    from google.cloud import vision
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("Google Cloud Vision not installed. Install with: pip install google-cloud-vision")

# Azure Computer Vision
try:
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
    from msrest.authentication import CognitiveServicesCredentials
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("Azure Computer Vision not installed. Install with: pip install azure-cognitiveservices-vision-computervision")


class ImageAnalyzer:
    """Analyze images using Google Vision or Azure Computer Vision"""
    
    def __init__(self, service='google', credentials=None):
        """
        Initialize the image analyzer
        
        Args:
            service: 'google' or 'azure'
            credentials: dict with API credentials
                For Google: {'credentials_path': 'path/to/key.json'}
                For Azure: {'subscription_key': 'your_key', 'endpoint': 'your_endpoint'}
        """
        self.service = service.lower()
        self.credentials = credentials or {}
        self.client = None
        self.results = []
        
        self._setup_google()
 
    
    def _setup_google(self):
        """Setup Google Vision API client"""
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google Cloud Vision not installed")
        
        # Set credentials path if provided
        if 'credentials_path' in self.credentials:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials['credentials_path']
        
        self.client = vision.ImageAnnotatorClient()
        print("✓ Google Vision API initialized")
    

    
    def analyze_image_google(self, image_url: str) -> Dict:
        """Analyze image using Google Vision API"""
        try:
            image = vision.Image()
            image.source.image_uri = image_url
            
            # Perform multiple detections
            response = self.client.annotate_image({
                'image': image,
                'features': [
                    {'type_': vision.Feature.Type.LABEL_DETECTION, 'max_results': 10},
                    {'type_': vision.Feature.Type.TEXT_DETECTION},
                    {'type_': vision.Feature.Type.IMAGE_PROPERTIES},
                    {'type_': vision.Feature.Type.SAFE_SEARCH_DETECTION},
                ]
            })
            
            # Extract labels
            labels = [
                {
                    'description': label.description,
                    'score': round(label.score, 4),
                    'confidence': round(label.score * 100, 2)
                }
                for label in response.label_annotations
            ]
            
            # Extract text (OCR)
            texts = []
            if response.text_annotations:
                # First annotation contains full text
                full_text = response.text_annotations[0].description if response.text_annotations else ""
                texts = [text.description for text in response.text_annotations[1:]]  # Individual words
            else:
                full_text = ""
            
            # Extract dominant colors
            colors = []
            if response.image_properties_annotation:
                colors = [
                    {
                        'color': f"RGB({int(c.color.red)}, {int(c.color.green)}, {int(c.color.blue)})",
                        'score': round(c.score, 4),
                        'pixel_fraction': round(c.pixel_fraction, 4)
                    }
                    for c in response.image_properties_annotation.dominant_colors.colors[:5]
                ]
            
            # Safe search detection
            safe_search = None
            if response.safe_search_annotation:
                safe = response.safe_search_annotation
                safe_search = {
                    'adult': safe.adult.name,
                    'violence': safe.violence.name,
                    'racy': safe.racy.name
                }
            
            return {
                'success': True,
                'labels': labels,
                'top_labels': [l['description'] for l in labels[:10]],
                'full_text': full_text,
                'text_snippets': texts[:10],  # First 10 words
                'dominant_colors': colors,
                'safe_search': safe_search,
                'error': None
            }
            
        except Exception as e:
            print(f"Error analyzing image with Google: {e}")
            return {
                'success': False,
                'labels': [],
                'top_labels': [],
                'full_text': '',
                'text_snippets': [],
                'dominant_colors': [],
                'safe_search': None,
                'error': str(e)
            }
    
 
            
    
    def analyze_image(self, image_url: str) -> Dict:
        """Analyze image using configured service"""
        if not image_url or not image_url.startswith('http'):
            return {
                'success': False,
                'error': 'Invalid image URL'
            }
        
        if self.service == 'google':
            return self.analyze_image_google(image_url)
        elif self.service == 'azure':
            return self.analyze_image_azure(image_url)
    
    def process_campaigns(self, campaigns: List[Dict], delay: float = 1.0) -> List[Dict]:
        """
        Process multiple campaigns and analyze their images
        
        Args:
            campaigns: List of campaign dicts with 'image_url' key
            delay: Delay between API calls in seconds
        """
        print(f"\nAnalyzing {len(campaigns)} images with {self.service.upper()} Vision API")
        print("=" * 60)
        
        enriched_campaigns = []
        successful = 0
        failed = 0
        
        for i, campaign in enumerate(campaigns, 1):
            image_url = campaign.get('image_url', '')
            
            if not image_url:
                print(f"[{i}/{len(campaigns)}] Skipping - No image URL")
                campaign['image_analysis'] = {'success': False, 'error': 'No image URL'}
                enriched_campaigns.append(campaign)
                failed += 1
                continue
            
            print(f"[{i}/{len(campaigns)}] Analyzing: {campaign.get('title', 'Unknown')[:50]}...")
            
            # Analyze image
            analysis = self.analyze_image(image_url)
            campaign['image_analysis'] = analysis
            
            if analysis['success']:
                successful += 1
                # Print top labels
                top_labels = analysis.get('top_labels', [])
                print(f"  ✓ Labels: {', '.join(top_labels[:3])}")
            else:
                failed += 1
                print(f"  ✗ Failed: {analysis.get('error', 'Unknown error')}")
            
            enriched_campaigns.append(campaign)
            
            # Rate limiting
            if i < len(campaigns):
                time.sleep(delay)
        
        print("=" * 60)
        print(f"Analysis complete!")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Total: {len(campaigns)}")
        
        self.results = enriched_campaigns
        return enriched_campaigns
    
    def save_results(self, output_file='campaigns_with_image_analysis.json'):
        """Save enriched results to JSON file"""
        if not self.results:
            print("No results to save!")
            return
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to {output_file}")
    
    def save_to_csv(self, output_file='campaigns_with_labels.csv'):
        """Save flattened results to CSV"""
        if not self.results:
            print("No results to save!")
            return
        
        rows = []
        for campaign in self.results:
            analysis = campaign.get('image_analysis', {})
            
            row = {
                      
                'url': campaign.get('url', ''),
                'image_url': campaign.get('image_url', ''),
                'amount_raised': campaign.get('amount_raised', ''),
                'days_running': campaign.get('days_running', ''),
                'description': campaign.get('description', ''),
                'all_labels': ', '.join(analysis.get('top_labels', [])),
       
            }
            
            # Add service-specific fields
            if self.service == 'azure' and 'captions' in analysis:
                captions = analysis.get('captions', [])
                row['image_caption'] = captions[0]['text'] if captions else ''
                row['caption_confidence'] = captions[0]['confidence'] if captions else ''
            
            rows.append(row)
        
        # Write CSV
        if rows:
            keys = rows[0].keys()
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"✓ CSV saved to {output_file}")


def load_campaigns_from_json(filepath='gofundme_animal_campaigns.json') -> List[Dict]:
    """Load campaigns from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_campaigns_from_csv(filepath='gofundme_animal_campaigns.csv') -> List[Dict]:
    """Load campaigns from CSV file"""
    campaigns = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        campaigns = list(reader)
    return campaigns


def main():
    """Main execution function"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  Image Analysis with Vision APIs                         ║
    ║  Supports: Google Cloud Vision & Azure Computer Vision   ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Configuration - CHANGE THESE
    SERVICE = 'google'  # or 'azure'
    INPUT_FILE = 'gofundme_campaigns_final.json'  # or .csv
    MAX_IMAGES = 1000  # Limit for testing (APIs cost money!)
    DELAY = 1.0  # Seconds between API calls
    
    # Credentials - REPLACE WITH YOUR OWN
    credentials = {}
    
    if SERVICE == 'google':
        # Option 1: Set environment variable before running script
        # export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
        
        # Option 2: Specify in code
        credentials = {
            'credentials_path': '/Users/ruyiyang/Desktop/MSITM-Materials/UDA/AnimalRescuer/starry-tracker-476318-e7-febfc5402dbd.json'
        }
        print("\n⚠️  Google Vision Setup:")
        print("   1. Enable Vision API: https://console.cloud.google.com/apis/library/vision.googleapis.com")
        print("   2. Create service account key: https://console.cloud.google.com/apis/credentials")
        print("   3. Download JSON key and set path above\n")
        
    elif SERVICE == 'azure':
        credentials = {
            'subscription_key': 'YOUR_AZURE_SUBSCRIPTION_KEY',
            'endpoint': 'https://YOUR_RESOURCE_NAME.cognitiveservices.azure.com/'
        }
        print("\n⚠️  Azure Computer Vision Setup:")
        print("   1. Create resource: https://portal.azure.com/#create/Microsoft.CognitiveServicesComputerVision")
        print("   2. Copy 'Key' and 'Endpoint' from Keys and Endpoint section")
        print("   3. Set credentials above\n")
    
    # Load campaigns
    try:
        if INPUT_FILE.endswith('.json'):
            campaigns = load_campaigns_from_json(INPUT_FILE)
        else:
            campaigns = load_campaigns_from_csv(INPUT_FILE)
        
        print(f"✓ Loaded {len(campaigns)} campaigns from {INPUT_FILE}")
        
        # Limit number for testing
        campaigns = campaigns[:MAX_IMAGES]
        print(f"  Processing first {len(campaigns)} campaigns")
        
    except FileNotFoundError:
        print(f"✗ File not found: {INPUT_FILE}")
        print("  Run the scraper first to generate campaign data")
        return
    except Exception as e:
        print(f"✗ Error loading campaigns: {e}")
        return
    
    # Initialize analyzer
    try:
        analyzer = ImageAnalyzer(service=SERVICE, credentials=credentials)
    except Exception as e:
        print(f"✗ Failed to initialize {SERVICE} API: {e}")
        print("  Check your credentials and API setup")
        return
    
    # Process campaigns
    enriched_campaigns = analyzer.process_campaigns(campaigns, delay=DELAY)
    
    # Save results
    analyzer.save_results(f'campaigns_with_{SERVICE}_analysis.json')
    analyzer.save_to_csv(f'campaigns_with_{SERVICE}_labels.csv')
    
    # Print sample results
    print("\n" + "=" * 60)
    print("SAMPLE RESULTS")
    print("=" * 60)
    
    successful_campaigns = [c for c in enriched_campaigns if c.get('image_analysis', {}).get('success')]
    if successful_campaigns:
        sample = successful_campaigns[0]
        analysis = sample['image_analysis']
        
        print(f"\nCampaign: {sample.get('title', 'Unknown')[:60]}")
        print(f"Image: {sample.get('image_url', 'N/A')[:60]}...")
        print(f"\nTop Labels:")
        for label in analysis.get('labels', [])[:10]:
            print(f"  • {label['description']} ({label['confidence']}% confidence)")
        
        if SERVICE == 'azure' and analysis.get('captions'):
            print(f"\nImage Caption:")
            for caption in analysis['captions']:
                print(f"  • {caption['text']} ({caption['confidence']}% confidence)")
        
        if analysis.get('full_text'):
            print(f"\nExtracted Text:")
            print(f"  {analysis['full_text'][:200]}...")
    
    print("\n" + "=" * 60)
    print("✓ Analysis complete! Check the output files.")
    print("=" * 60)


if __name__ == "__main__":
    main()
