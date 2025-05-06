import requests
import pandas as pd
import xml.etree.ElementTree as ET
import re
from urllib.parse import urlparse
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class SitemapParser:
    def __init__(self):
        self.urls = []
        self.namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
        }
    
    def fetch_sitemap(self, sitemap_url):
        """Fetch the sitemap from the provided URL."""
        try:
            logger.info(f"Fetching sitemap from {sitemap_url}")
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching sitemap: {e}")
            raise
    
    def parse_sitemap(self, sitemap_content):
        """Parse the sitemap content and extract URLs."""
        try:
            root = ET.fromstring(sitemap_content)
            
            sitemap_tags = root.findall('.//sm:sitemap', self.namespaces)
            if sitemap_tags:
                logger.info("Found a sitemap index, processing sub-sitemaps")
                for sitemap in sitemap_tags:
                    sub_sitemap_url = sitemap.find('./sm:loc', self.namespaces).text
                    sub_content = self.fetch_sitemap(sub_sitemap_url)
                    self.parse_sitemap(sub_content)
            
            url_tags = root.findall('.//sm:url', self.namespaces)
            for url in url_tags:
                loc = url.find('./sm:loc', self.namespaces)
                if loc is not None and loc.text:
                    lastmod = url.find('./sm:lastmod', self.namespaces)
                    lastmod_text = lastmod.text if lastmod is not None else None
                    
                    self.urls.append({
                        'url': loc.text,
                        'lastmod': lastmod_text
                    })
            
            logger.info(f"Found {len(self.urls)} URLs in total")
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
            raise
    
    def categorize_urls(self):
        """Categorize URLs based on their path patterns."""
        categorized_urls = []
        
        for url_data in self.urls:
            url = url_data['url']
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # Default category
            category = "page"
            
            # Categorize based on common patterns
            if re.search(r'/products?/[^/]+/?$', path):
                category = "product"
            elif re.search(r'/collections?/[^/]+/?$', path):
                category = "collection"
            elif re.search(r'/blogs?/[^/]+/[^/]+/?$', path):
                category = "blog"
            
            categorized_urls.append({
                'url': url,
                'category': category,
                'lastmod': url_data.get('lastmod')
            })
        
        return categorized_urls
    
    def export_to_excel(self, categorized_urls, output_file=None):
        """Export the categorized URLs to an Excel file."""
        df = pd.DataFrame(categorized_urls)
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'sitemap_results_{timestamp}.xlsx'
        
        df.to_excel(output_file, index=False)
        logger.info(f"Results exported to {output_file}")
        
        categories = df['category'].value_counts().to_dict()
        logger.info("URL Summary:")
        for category, count in categories.items():
            logger.info(f"  {category}: {count}")
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Parse a sitemap, categorize URLs, and export to Excel')
    parser.add_argument('sitemap_url', help='URL of the sitemap to parse')
    parser.add_argument('-o', '--output', help='Output Excel file name')
    args = parser.parse_args()
    
    sitemap_parser = SitemapParser()
    
    try:
        sitemap_content = sitemap_parser.fetch_sitemap(args.sitemap_url)
        sitemap_parser.parse_sitemap(sitemap_content)
        categorized_urls = sitemap_parser.categorize_urls()
        output_file = sitemap_parser.export_to_excel(categorized_urls, args.output)
        print(f"\nSuccessfully processed sitemap. Results saved to: {output_file}")
    except Exception as e:
        logger.error(f"Error processing sitemap: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())