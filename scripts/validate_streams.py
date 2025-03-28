import json
import requests
import concurrent.futures
import time
import os
import logging
import datetime
from pathlib import Path

"""
Validate streams in the metadata catalog by checking if they're accessible.
This script will:
1. Load the catalog.json file
2. Check each stream URL to see if it's reachable
3. Save the validation results with status information
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Project root directory
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
METADATA_DIR = ROOT_DIR / "metadata"
CATALOG_FILE = METADATA_DIR / "catalog.json"
RESULTS_FILE = ROOT_DIR / "validation-results.json"

# Maximum number of threads to use for validation
MAX_WORKERS = 20

def check_stream(stream_info):
    """Check if a stream URL is accessible"""
    url = stream_info.get('url')
    
    if not url:
        return {
            'url': None,
            'status': 0,
            'working': False,
            'error': 'Missing URL'
        }
    
    try:
        start = time.time()
        # Use a short timeout to check if the stream responds
        response = requests.head(
            url, 
            timeout=10, 
            headers={
                'User-Agent': 'IPRD-Validator/1.0',
                'Accept': '*/*'
            },
            allow_redirects=True
        )
        latency = time.time() - start
        
        # Some stream servers might not properly respond to HEAD requests,
        # so if we get a 4xx error, try a GET request with a small range
        if 400 <= response.status_code < 500:
            try:
                start = time.time()
                response = requests.get(
                    url, 
                    timeout=10,
                    headers={
                        'User-Agent': 'IPRD-Validator/1.0',
                        'Accept': '*/*',
                        'Range': 'bytes=0-1024'  # Only request a small chunk
                    },
                    stream=True  # Don't download the entire content
                )
                # Read just a bit of the content to verify stream is working
                next(response.iter_content(chunk_size=1024), None)
                latency = time.time() - start
                
                # Close the connection
                response.close()
                
            except Exception as e:
                # If the GET request also fails, return the original HEAD result
                logging.warning(f"GET request failed for {url}: {str(e)}")
        
        return {
            'url': url,
            'status': response.status_code,
            'working': 200 <= response.status_code < 400,
            'latency': round(latency, 2),
            'station_id': stream_info.get('station_id'),
            'station_name': stream_info.get('station_name'),
            'check_time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'status': 0,
            'working': False,
            'error': 'Timeout',
            'station_id': stream_info.get('station_id'),
            'station_name': stream_info.get('station_name'),
            'check_time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except requests.exceptions.ConnectionError:
        return {
            'url': url,
            'status': 0,
            'working': False,
            'error': 'Connection error',
            'station_id': stream_info.get('station_id'),
            'station_name': stream_info.get('station_name'),
            'check_time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except Exception as e:
        return {
            'url': url,
            'status': 0,
            'working': False,
            'error': str(e),
            'station_id': stream_info.get('station_id'),
            'station_name': stream_info.get('station_name'),
            'check_time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

def load_catalog():
    """Load the station catalog"""
    if not CATALOG_FILE.exists():
        logging.error(f"Catalog file not found: {CATALOG_FILE}")
        return None
    
    try:
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Failed to load catalog: {e}")
        return None

def extract_streams_from_catalog(catalog):
    """Extract stream information from the catalog"""
    if not catalog or 'stations' not in catalog:
        return []
    
    streams = []
    for station in catalog['stations']:
        station_id = station.get('id', '')
        station_name = station.get('name', '')
        
        for stream in station.get('streams', []):
            stream_info = {
                'url': stream.get('url', ''),
                'station_id': station_id,
                'station_name': station_name
            }
            streams.append(stream_info)
    
    return streams

def main():
    # Load the catalog
    logging.info("Loading station catalog...")
    catalog = load_catalog()
    
    if not catalog:
        logging.error("Failed to load catalog. Exiting.")
        return
    
    # Extract streams to check
    streams_to_check = extract_streams_from_catalog(catalog)
    logging.info(f"Found {len(streams_to_check)} streams to validate")
    
    if not streams_to_check:
        logging.warning("No streams found to validate. Exiting.")
        return
    
    # Results structure
    results = {
        'total': 0,
        'working': 0,
        'failed': 0,
        'stations': {},
        'details': [],
        'validation_time': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # Validate streams in parallel
    logging.info(f"Starting validation with {MAX_WORKERS} workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for stream in streams_to_check:
            futures.append(executor.submit(check_stream, stream))
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            
            results['total'] += 1
            if result['working']:
                results['working'] += 1
                status = 'ok'
            else:
                results['failed'] += 1
                status = 'failed'
            
            # Store detailed result
            results['details'].append(result)
            
            # Store simplified status per URL for easy lookups
            if 'url' in result and result['url']:
                results['stations'][result['url']] = status
            
            # Log progress periodically
            if results['total'] % 100 == 0:
                logging.info(f"Processed {results['total']}/{len(streams_to_check)} streams")
    
    # Calculate success rate
    success_rate = results['working'] / results['total'] if results['total'] > 0 else 0
    results['success_rate'] = round(success_rate, 4)
    
    # Add summary text
    results['summary'] = (
        f"{results['working']}/{results['total']} streams working "
        f"({round(success_rate * 100, 1)}%), {results['failed']} failures"
    )
    
    # Save results
    logging.info(f"Validation complete. {results['summary']}")
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    main()