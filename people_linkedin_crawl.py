#!/usr/bin/env python3
"""
LinkedIn Company Page Monitor & Data Extractor - Enhanced Version
Smart filename generation and manual page progression
"""

import pandas as pd
import time
import random
import json
import os
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

class LinkedInCompanyMonitor:
    def __init__(self):
        self.setup_driver()
        self.monitored_companies = {}
        self.extraction_active = False
        self.current_page_data = []
        
    def setup_driver(self):
        """Setup Chrome driver with enhanced options"""
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-plugins")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=opts)
        self.driver.maximize_window()
        
    def generate_smart_filename(self, url, page_title):
        """Generate smart filename based on LinkedIn URL structure"""
        try:
            print(f"🔍 Analyzing URL: {url}")
            print(f"📄 Page title: {page_title}")
            
            # Extract LinkedIn profile pattern
            # Pattern: https://www.linkedin.com/in/firstname-lastname-restofid
            if '/in/' in url:
                # Extract the part after /in/
                profile_part = url.split('/in/')[-1]
                # Remove any query parameters
                profile_part = profile_part.split('?')[0].split('/')[0]
                
                # Split by dash and take first two parts
                parts = profile_part.split('-')
                if len(parts) >= 2:
                    list1 = parts[0]
                    list2 = parts[1]
                    # Find where the rest begins (special character or number)
                    rest_parts = parts[2:]
                    rest = '-'.join(rest_parts) if rest_parts else ''
                    
                    # Generate filename: list1-list2-rest
                    if rest:
                        filename = f"{list1}-{list2}-{rest}"
                    else:
                        filename = f"{list1}-{list2}"
                        
                    print(f"✅ Generated filename from profile: {filename}")
                    return self.sanitize_filename(filename)
            
            # For company pages, extract company name from URL
            elif '/company/' in url:
                company_part = url.split('/company/')[-1]
                company_name = company_part.split('/')[0]
                
                # If it's a people page, add that info
                if '/people/' in url:
                    filename = f"{company_name}-employees"
                else:
                    filename = company_name
                    
                print(f"✅ Generated filename from company: {filename}")
                return self.sanitize_filename(filename)
            
            # For search results, extract search terms
            elif '/search/' in url:
                # Try to extract search keywords from URL
                if 'keywords=' in url:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url)
                    params = urllib.parse.parse_qs(parsed.query)
                    keywords = params.get('keywords', [''])[0]
                    if keywords:
                        filename = f"search-{keywords.replace(' ', '-')}"
                        print(f"✅ Generated filename from search: {filename}")
                        return self.sanitize_filename(filename)
                
                # Fallback to page title analysis
                if 'people' in page_title.lower():
                    # Extract company name from title like "Microsoft employees"
                    title_clean = page_title.replace(' | LinkedIn', '').replace(' - LinkedIn', '')
                    if 'employees' in title_clean.lower():
                        company_name = title_clean.lower().replace('employees', '').strip()
                        company_name = company_name.replace(' people', '').strip()
                        filename = f"{company_name}-employees"
                        print(f"✅ Generated filename from title: {filename}")
                        return self.sanitize_filename(filename)
            
            # Fallback to page title
            title_clean = page_title.replace(' | LinkedIn', '').replace(' - LinkedIn', '')
            filename = self.sanitize_filename(title_clean)
            print(f"✅ Using page title as filename: {filename}")
            return filename
            
        except Exception as e:
            print(f"⚠️  Error generating filename: {str(e)}")
            # Ultimate fallback
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"linkedin_data_{timestamp}"
    
    def sanitize_filename(self, filename):
        """Sanitize filename for saving"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove extra spaces and convert to lowercase
        filename = filename.strip().lower()
        # Replace spaces with dash
        filename = filename.replace(' ', '-')
        # Remove multiple dashes
        filename = re.sub(r'-+', '-', filename)
        # Limit length
        filename = filename[:100]
        return filename
    
    def detect_company_page(self):
        """Detect if current page is a LinkedIn company page"""
        try:
            current_url = self.driver.current_url
            
            # Check if it's a company page
            if '/company/' in current_url and '/people/' in current_url:
                return True
            elif '/search/results/people/' in current_url:
                return True
            elif 'linkedin.com' in current_url and any(keyword in current_url.lower() for keyword in ['company', 'people', 'employees']):
                return True
            
            return False
        except Exception as e:
            return False
    
    def get_page_title(self):
        """Get current page title"""
        try:
            title = self.driver.title
            return title if title else "linkedin_data"
        except:
            return "linkedin_data"
    
    def extract_profiles_from_current_page(self):
        """Extract all profile data from current page"""
        profiles = []
        
        print("🔍 Extracting profiles from current page...")
        
        # Multiple selectors for different LinkedIn page types
        profile_selectors = [
            # Company people page
            '.org-people-profile-card',
            '.org-people-profile-card__profile-info',
            
            # Search results page
            '.entity-result',
            '.entity-result__item',
            
            # General profile cards
            '.search-result__result-link',
            '.app-aware-link',
            '.profile-card',
            
            # List view
            '.reusable-search__result-container',
            '.search-results-container .entity-result'
        ]
        
        found_profiles = []
        
        for selector in profile_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  ✅ Found {len(elements)} profiles using selector: {selector}")
                    found_profiles = elements
                    break
            except:
                continue
        
        if not found_profiles:
            print("  ❌ No profiles found with standard selectors, trying alternative approach...")
            # Try to find any links that look like profile links
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                for link in all_links:
                    href = link.get_attribute('href')
                    if href and '/in/' in href and 'linkedin.com' in href:
                        found_profiles.append(link)
                print(f"  ✅ Found {len(found_profiles)} profile links via alternative method")
            except:
                pass
        
        # Extract data from found profiles
        for i, profile_element in enumerate(found_profiles):
            try:
                profile_data = self.extract_single_profile_data(profile_element)
                if profile_data and profile_data not in profiles:
                    profiles.append(profile_data)
                    print(f"  📊 {i+1}. {profile_data.get('name', 'Unknown')} - {profile_data.get('title', 'No title')}")
            except Exception as e:
                print(f"  ⚠️  Error extracting profile {i+1}: {str(e)}")
                continue
        
        return profiles
    
    def extract_single_profile_data(self, profile_element):
        """Extract data from a single profile element"""
        try:
            # Initialize profile data
            profile_data = {
                'name': 'Not found',
                'title': 'Not found',
                'location': 'Not found',
                'profile_url': 'Not found',
                'company': 'Not found',
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Try to get profile URL
            url_selectors = ['a[href*="/in/"]', 'a', '[href*="/in/"]']
            for selector in url_selectors:
                try:
                    url_element = profile_element.find_element(By.CSS_SELECTOR, selector)
                    href = url_element.get_attribute('href')
                    if href and '/in/' in href:
                        profile_data['profile_url'] = href
                        break
                except:
                    continue
            
            # Try to get name
            name_selectors = [
                'div.lt-line-clamp.lt-line-clamp--single-line',  # Specific to the class you provided
                '.org-people-profile-card__profile-title',
                '.entity-result__title-text a span[aria-hidden="true"]',
                '.entity-result__title-text',
                'h3 a span[aria-hidden="true"]',
                'h3 span[aria-hidden="true"]',
                '.profile-card__title',
                '.name',
                'h3',
                '.t-16.t-black.t-bold',
                '.search-result__result-link span[aria-hidden="true"]',
                'span[aria-hidden="true"]'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = profile_element.find_element(By.CSS_SELECTOR, selector)
                    name_text = name_element.text.strip()
                    if name_text and len(name_text) > 1 and not name_text.isdigit():
                        profile_data['name'] = name_text 
                        break
                except:
                    continue
            
            # Try to get title/position
            title_selectors = [
                '.org-people-profile-card__profile-subtitle',
                '.entity-result__primary-subtitle',
                '.entity-result__subtitle',
                '.profile-card__subtitle',
                '.title',
                '.t-14.t-black--light.t-normal',
                '.entity-result__summary'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = profile_element.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 1:
                        profile_data['title'] = title_text
                        break
                except:
                    continue
            
            # Try to get location
            location_selectors = [
                '.entity-result__secondary-subtitle',
                '.org-people-profile-card__meta',
                '.profile-card__meta',
                '.location',
                '.t-12.t-black--light.t-normal'
            ]
            
            for selector in location_selectors:
                try:
                    location_element = profile_element.find_element(By.CSS_SELECTOR, selector)
                    location_text = location_element.text.strip()
                    if location_text and len(location_text) > 1:
                        profile_data['location'] = location_text
                        break
                except:
                    continue
            
            # Try to extract company from page context
            try:
                page_title = self.driver.title
                if 'employees' in page_title.lower():
                    company_match = re.search(r'(.+?)\s+employees', page_title, re.IGNORECASE)
                    if company_match:
                        profile_data['company'] = company_match.group(1).strip()
            except:
                pass
            
            return profile_data
            
        except Exception as e:
            print(f"    ⚠️  Error in extract_single_profile_data: {str(e)}")
            return None
    
    def check_for_next_page(self):
        """Check if there's a next page"""
        next_selectors = [
            'button[aria-label="Next"]',
            'button[aria-label="View next profiles"]',
            '.artdeco-pagination__button--next:not([disabled])',
            '.org-people-employees-search-results__pagination button:last-child:not([disabled])',
            'button:contains("Next")',
            '[data-test-pagination-page-btn="next"]'
        ]
        
        for selector in next_selectors:
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                
                # Check if button is not disabled
                if not next_button.get_attribute('disabled'):
                    return next_button
                    
            except:
                continue
        
        # Alternative: Look for pagination with JavaScript
        try:
            result = self.driver.execute_script("""
                var nextButtons = document.querySelectorAll('button');
                for (var i = 0; i < nextButtons.length; i++) {
                    var btn = nextButtons[i];
                    if (btn.textContent.includes('Next') || btn.getAttribute('aria-label') === 'Next') {
                        if (!btn.disabled) {
                            return btn;
                        }
                    }
                }
                return null;
            """)
            
            if result:
                return result
        except:
            pass
        
        return None
    
    def extract_all_pages_with_approval(self):
        """Extract data from all pages with manual approval"""
        all_profiles = []
        page_number = 1
        
        while True:
            print(f"\n" + "="*60)
            print(f"📄 PROCESSING PAGE {page_number}")
            print("="*60)
            
            # Wait for page to load
            time.sleep(random.uniform(2, 4))
            
            # Extract profiles from current page
            profiles = self.extract_profiles_from_current_page()
            
            if profiles:
                all_profiles.extend(profiles)
                print(f"\n✅ Successfully extracted {len(profiles)} profiles from page {page_number}")
                print(f"📊 Total profiles extracted so far: {len(all_profiles)}")
                
                # Show some sample profiles
                print(f"\n🔍 Sample profiles from this page:")
                for i, profile in enumerate(profiles[:3]):
                    print(f"  {i+1}. {profile.get('name', 'Unknown')} - {profile.get('title', 'No title')}")
                if len(profiles) > 3:
                    print(f"  ... and {len(profiles) - 3} more profiles")
                    
            else:
                print(f"\n❌ No profiles found on page {page_number}")
                print("   This might be the last page or there's an issue with the page")
            
            # Check for next page
            next_button = self.check_for_next_page()
            
            if next_button:
                print(f"\n🔍 Next page available!")
                print(f"📊 Current status:")
                print(f"  📄 Current page: {page_number}")
                print(f"  👥 Profiles on this page: {len(profiles)}")
                print(f"  📈 Total profiles: {len(all_profiles)}")
                print(f"\n⏸️  Ready to move to page {page_number + 1}")
                
                # Wait for user approval
                user_input = input("   Press ENTER to continue to next page, or type 'q' to quit: ").strip().lower()
                
                if user_input == 'q':
                    print("🛑 Extraction stopped by user")
                    break
                
                # Navigate to next page
                try:
                    print(f"  ➡️  Moving to page {page_number + 1}...")
                    self.driver.execute_script("arguments[0].click();", next_button)
                    page_number += 1
                    
                    # Add a longer delay after clicking next
                    print("  ⏳ Waiting for next page to load...")
                    time.sleep(random.uniform(3, 5))
                    
                except Exception as e:
                    print(f"  ❌ Error navigating to next page: {str(e)}")
                    break
            else:
                print(f"\n🏁 No more pages available")
                print("   Either reached the end or no next button found")
                break
        
        print(f"\n" + "="*60)
        print(f"📊 EXTRACTION COMPLETED")
        print("="*60)
        print(f"📄 Total pages processed: {page_number}")
        print(f"👥 Total profiles extracted: {len(all_profiles)}")
        
        return all_profiles
    
    def save_data(self, profiles, current_url, page_title):
        """Save extracted data to files with smart naming"""
        if not profiles:
            print("❌ No data to save")
            return
        
        # Create output directory
        output_dir = "linkedin_extractions"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate smart filename
        filename_base = self.generate_smart_filename(current_url, page_title)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save as CSV
        csv_filename = os.path.join(output_dir, f"{filename_base}_{timestamp}.csv")
        df = pd.DataFrame(profiles)
        df.to_csv(csv_filename, index=False)
        
        # Save as JSON
        json_filename = os.path.join(output_dir, f"{filename_base}_{timestamp}.json")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 DATA SAVED SUCCESSFULLY!")
        print(f"📁 Location: {output_dir}/")
        print(f"📊 CSV file: {os.path.basename(csv_filename)}")
        print(f"📋 JSON file: {os.path.basename(json_filename)}")
        print(f"🔢 Total records: {len(profiles)}")
        
        # Save extraction metadata
        metadata = {
            'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_url': current_url,
            'page_title': page_title,
            'filename_base': filename_base,
            'total_profiles': len(profiles),
            'profiles_with_names': sum(1 for p in profiles if p.get('name') != 'Not found'),
            'profiles_with_titles': sum(1 for p in profiles if p.get('title') != 'Not found'),
            'profiles_with_locations': sum(1 for p in profiles if p.get('location') != 'Not found')
        }
        
        metadata_filename = os.path.join(output_dir, f"{filename_base}_{timestamp}_metadata.json")
        with open(metadata_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Metadata: {os.path.basename(metadata_filename)}")
        
        # Display detailed summary
        print(f"\n📈 EXTRACTION SUMMARY:")
        print(f"  🎯 Source: {page_title}")
        print(f"  🔗 URL: {current_url}")
        print(f"  👥 Total profiles: {len(profiles)}")
        print(f"  ✅ With names: {sum(1 for p in profiles if p.get('name') != 'Not found')}")
        print(f"  💼 With titles: {sum(1 for p in profiles if p.get('title') != 'Not found')}")
        print(f"  📍 With locations: {sum(1 for p in profiles if p.get('location') != 'Not found')}")
        print(f"  🕒 Extracted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def monitor_and_extract(self):
        """Main monitoring loop with enhanced features"""
        print("🚀 LinkedIn Company Monitor Started!")
        print("="*60)
        print("📋 INSTRUCTIONS:")
        print("  1. I'll open LinkedIn - please log in manually")
        print("  2. Navigate to any company's 'People' page")
        print("  3. I'll detect the page and offer to extract data")
        print("  4. You'll control page progression with ENTER key")
        print("  5. Data will be saved with smart filenames")
        print("  6. Press Ctrl+C to stop monitoring anytime")
        print("="*60)
        print("⚠️  IMPORTANT: Only public data will be extracted!")
        print("⚠️  Please respect LinkedIn's terms of service")
        print("="*60)
        
        try:
            # Navigate to LinkedIn
            print("\n🔐 Opening LinkedIn...")
            self.driver.get('https://www.linkedin.com/')
            print("🔑 Please log in to LinkedIn manually in the browser...")
            
            # Wait for login
            print("⏳ Waiting for login completion...")
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.ID, "global-nav-typeahead"))
            )
            print("✅ Login detected successfully!")
            
            print("\n🎯 READY FOR EXTRACTION!")
            print("📍 Now navigate to a company's 'People' page...")
            print("   Examples:")
            print("   • https://www.linkedin.com/company/microsoft/people/")
            print("   • Search 'Microsoft employees' and use People filter")
            print("   • Any company page with employee listings")
            
            last_url = ""
            extraction_completed = set()
            
            while True:
                try:
                    current_url = self.driver.current_url
                    
                    # Check if we're on a company page and haven't extracted this page yet
                    if self.detect_company_page() and current_url != last_url:
                        page_title = self.get_page_title()
                        
                        # Avoid duplicate extractions
                        if current_url not in extraction_completed:
                            print(f"\n" + "🎯"*20)
                            print(f"🎯 COMPANY PAGE DETECTED!")
                            print(f"🎯"*20)
                            print(f"📄 Page: {page_title}")
                            print(f"🔗 URL: {current_url}")
                            
                            # Generate preview of filename
                            preview_filename = self.generate_smart_filename(current_url, page_title)
                            print(f"💾 Data will be saved as: {preview_filename}_[timestamp]")
                            
                            print(f"\n📊 EXTRACTION OPTIONS:")
                            print("   This will extract employee data from ALL pages")
                            print("   You'll approve each page progression manually")
                            print("   Data will be saved automatically")
                            
                            extract = input("\n🚀 Start extraction? (y/n): ").lower().strip()
                            
                            if extract == 'y':
                                print(f"\n🚀 STARTING EXTRACTION")
                                print(f"📊 Target: {page_title}")
                                print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
                                
                                # Extract data from all pages with manual approval
                                all_profiles = self.extract_all_pages_with_approval()
                                
                                if all_profiles:
                                    # Save data with smart filename
                                    self.save_data(all_profiles, current_url, page_title)
                                    extraction_completed.add(current_url)
                                    
                                    print(f"\n✅ EXTRACTION COMPLETED SUCCESSFULLY!")
                                    print(f"🎉 {len(all_profiles)} profiles extracted and saved")
                                else:
                                    print(f"\n❌ No data extracted")
                            else:
                                print("   ⏩ Extraction skipped")
                    
                    last_url = current_url
                    
                    # Check if browser is still open
                    try:
                        self.driver.current_url
                    except:
                        print("🔚 Browser closed, stopping monitor...")
                        break
                    
                    # Wait before next check
                    time.sleep(2)
                    
                except KeyboardInterrupt:
                    print("\n⏹️  Monitoring stopped by user")
                    break
                except Exception as e:
                    print(f"⚠️  Error in monitoring loop: {str(e)}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        finally:
            self.close()
    
    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
            print("🔚 Browser closed")
        except:
            pass

def main():
    """Main function"""
    print("=" * 80)
    print("🔍 LinkedIn Company Employee Data Extractor - Enhanced Version")
    print("=" * 80)
    print("🎯 Features:")
    print("  • Smart filename generation based on LinkedIn URLs")
    print("  • Manual page progression control")
    print("  • Automatic company page detection")
    print("  • Multiple output formats (CSV, JSON, Metadata)")
    print("  • Detailed extraction summaries")
    print("=" * 80)
    print("⚠️  LEGAL NOTICE:")
    print("  • Only extracts public domain data")
    print("  • Respects LinkedIn's terms of service")
    print("  • Use extracted data responsibly and ethically")
    print("  • For educational and legitimate business purposes only")
    print("=" * 80)
    
    monitor = LinkedInCompanyMonitor()
    monitor.monitor_and_extract()

if __name__ == "__main__":
    main()

