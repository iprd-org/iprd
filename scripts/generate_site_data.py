#!/usr/bin/env python3
import os
import re
import json
import datetime
import hashlib
import logging
import urllib.parse
import shutil
from pathlib import Path
from collections import defaultdict, Counter

"""
Generate site data for the IPRD project, including:
- Metadata catalog file in JSON
- Unified playlist
- Statistics per country
- Total number of available stations
- Genre information
"""

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Project root directory
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STREAMS_DIR = ROOT_DIR / "streams"
METADATA_DIR = ROOT_DIR / "metadata"
OUTPUT_DIR = ROOT_DIR / "docs" / "site_data"  # Added for docs output
VALIDATION_RESULTS_FILE = ROOT_DIR / "validation-results.json"

# Create output directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
METADATA_DIR.mkdir(exist_ok=True)

# Common audio format extensions and their details
AUDIO_FORMATS = {
    'mp3': {'name': 'MP3', 'default_bitrate': 128},
    'aac': {'name': 'AAC', 'default_bitrate': 128},
    'ogg': {'name': 'OGG', 'default_bitrate': 128},
    'flac': {'name': 'FLAC', 'default_bitrate': 960},
    'm4a': {'name': 'AAC', 'default_bitrate': 128},
    'opus': {'name': 'OPUS', 'default_bitrate': 96},
    'wav': {'name': 'WAV', 'default_bitrate': 1411},
}

# Country code to language mapping (for major official languages)
COUNTRY_LANGUAGES = {
    'FR': 'French',
    'DE': 'German',
    'IT': 'Italian',
    'ES': 'Spanish',
    'US': 'English',
    'GB': 'English',
    'PT': 'Portuguese',
    'BR': 'Portuguese',
    'NL': 'Dutch',
    'BE': ['Dutch', 'French', 'German'],
    'JP': 'Japanese',
    'CN': 'Chinese',
    'RU': 'Russian',
    'AR': 'Spanish',
    'MX': 'Spanish',
    'CA': ['English', 'French'],
    'CH': ['German', 'French', 'Italian', 'Romansh'],
    # Add more as needed
}

def get_language_from_country(country_code):
    """Determine likely language based on country code."""
    if country_code.upper() in COUNTRY_LANGUAGES:
        languages = COUNTRY_LANGUAGES[country_code.upper()]
        if isinstance(languages, list):
            return languages[0]  # Return first language as default
        return languages
    return ""

def extract_bitrate_from_url(url):
    """Attempt to extract bitrate information from URL."""
    # Common patterns in URLs for bitrate: 128k, 320, 64, etc.
    bitrate_patterns = [
        r'[-_/](\d+)k[-_/.]',
        r'[-_/](\d+)kbps[-_/.]',
        r'[-_/](\d+)kb[-_/.]',
        r'[-_/.](\d+)[-_/.]',  # More generic pattern, lower priority
    ]
    
    for pattern in bitrate_patterns:
        match = re.search(pattern, url.lower())
        if match:
            try:
                bitrate = int(match.group(1))
                # Filter out unlikely bitrates
                if 32 <= bitrate <= 1411:  # Common bitrate range
                    return bitrate
            except ValueError:
                pass
    
    # Try to determine from known stream providers
    if 'icecast' in url.lower():
        return 128  # Common default for Icecast
    
    return 0  # Unknown

def determine_audio_format(url):
    """Determine audio format from URL and parameters."""
    # Check for format in the file extension
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path.lower()
    
    # Extract extension from path
    if '.' in path:
        ext = path.split('.')[-1].lower()
        if ext in AUDIO_FORMATS:
            return AUDIO_FORMATS[ext]['name'], AUDIO_FORMATS[ext]['default_bitrate']
    
    # Check common format identifiers in the URL
    format_identifiers = {
        'mp3': ['mp3', 'mpeg'],
        'aac': ['aac', 'aacp', 'he-aac'],
        'ogg': ['ogg', 'vorbis'],
        'flac': ['flac'],
        'opus': ['opus'],
        'wav': ['wav', 'pcm'],
    }
    
    for fmt, identifiers in format_identifiers.items():
        for identifier in identifiers:
            if identifier in url.lower():
                return AUDIO_FORMATS[fmt]['name'], AUDIO_FORMATS[fmt]['default_bitrate']
    
    # Check query parameters for format clues
    query_params = urllib.parse.parse_qs(parsed_url.query)
    for param_name, param_values in query_params.items():
        param_name = param_name.lower()
        if param_name in ['format', 'fmt', 'type']:
            for value in param_values:
                value = value.lower()
                for fmt, identifiers in format_identifiers.items():
                    if value in identifiers:
                        return AUDIO_FORMATS[fmt]['name'], AUDIO_FORMATS[fmt]['default_bitrate']
    
    return "Unknown", 0

def parse_m3u_file(file_path):
    """Parse an M3U file and extract station information."""
    stations = []
    current_station = None
    country_code = os.path.basename(os.path.dirname(file_path))
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            if line.startswith('#EXTM3U'):
                continue
                
            if line.startswith('#EXTINF:'):
                # Parse the EXTINF line
                match = re.search(r'tvg-logo="([^"]*)".*group-title="([^"]*)",(.*)', line)
                if match:
                    logo_url = match.group(1)
                    group_title = match.group(2)
                    station_name = match.group(3).strip()
                    
                    # Extract genres
                    genres = [genre.strip() for genre in group_title.split(';')]
                    
                    current_station = {
                        'name': station_name,
                        'logo': logo_url,
                        'genres': genres,
                        'country_code': country_code.upper(),
                        'country': get_country_name(country_code),
                        'language': get_language_from_country(country_code)
                    }
            elif current_station and line.startswith(('http://', 'https://')):
                # This is a URL line
                current_station['url'] = line
                
                # Determine audio format and bitrate
                audio_format, default_bitrate = determine_audio_format(line)
                bitrate = extract_bitrate_from_url(line) or default_bitrate
                
                current_station['format'] = audio_format
                current_station['bitrate'] = bitrate
                
                # Generate a unique ID
                unique_id = generate_station_id(current_station)
                current_station['id'] = unique_id
                
                stations.append(current_station)
                current_station = None
                
    return stations

def generate_station_id(station):
    """Generate a unique ID for a station based on name, country, and URL."""
    # Create a base string from station name and country
    base = f"{station['country_code'].lower()}-{station['name'].lower()}"
    
    # Clean the base string to create a URL-friendly ID
    base = re.sub(r'[^a-z0-9]', '-', base)
    base = re.sub(r'-+', '-', base)  # Replace multiple hyphens with a single one
    base = base.strip('-')
    
    # Add a unique hash based on the URL to avoid conflicts
    url_hash = hashlib.md5(station['url'].encode()).hexdigest()[:8]
    
    return f"{base}-{url_hash}"

def get_country_name(country_code):
    """Get the full country name from a country code."""
    # A more comprehensive approach would be to use a library like pycountry
    # For now, this is a simplified mapping of common codes
    country_names = {
        'us': 'United States',
        'gb': 'United Kingdom',
        'ca': 'Canada',
        'au': 'Australia',
        'fr': 'France',
        'de': 'Germany',
        'it': 'Italy',
        'es': 'Spain',
        'jp': 'Japan',
        'cn': 'China',
        'br': 'Brazil',
        'ru': 'Russia',
        'in': 'India',
        'za': 'South Africa',
        'mx': 'Mexico',
        # Add more as needed
    }
    
    return country_names.get(country_code.lower(), country_code.upper())

def load_validation_results():
    """Load validation results if available."""
    if VALIDATION_RESULTS_FILE.exists():
        try:
            with open(VALIDATION_RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to load validation results: {e}")
    
    return {'stations': {}}

def get_all_stations():
    """Get all stations from all M3U files."""
    all_stations = []
    country_counts = defaultdict(int)
    country_files = []
    
    for file_path in STREAMS_DIR.glob('**/*.m3u'):
        if file_path.is_file():
            country_code = file_path.parent.name
            stations = parse_m3u_file(file_path)
            
            for station in stations:
                station['source_file'] = str(file_path.relative_to(ROOT_DIR))
            
            all_stations.extend(stations)
            country_counts[country_code.upper()] = len(stations) + country_counts[country_code.upper()]
            country_files.append({
                'code': country_code.upper(),
                'file': str(file_path.relative_to(ROOT_DIR)),
                'count': len(stations)
            })
            logging.info(f"Processed {file_path.name}: {len(stations)} stations")
    
    return all_stations, country_counts, country_files

def analyze_genres(stations):
    """Analyze genres across all stations."""
    genre_counter = Counter()
    for station in stations:
        for genre in station['genres']:
            genre_counter[genre.lower()] += 1
    
    # Get top genres
    top_genres = genre_counter.most_common(50)
    
    return {
        'total_unique_genres': len(genre_counter),
        'top_genres': [{'name': genre, 'count': count} for genre, count in top_genres]
    }

def generate_metadata_catalog(stations, validation_results):
    """Generate metadata catalog JSON file with station information."""
    now = datetime.datetime.now(datetime.UTC)
    updated_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Create the catalog structure
    catalog = {
        "version": "1.0",
        "updated": updated_time,
        "stations": []
    }
    
    # Add stations to the catalog
    for station in stations:
        station_id = station['id']
        
        # Determine reliability based on validation results
        reliability = 0.5  # Default reliability
        if validation_results and 'stations' in validation_results:
            if station['url'] in validation_results['stations']:
                status = validation_results['stations'][station['url']]
                reliability = 0.95 if status == 'ok' else 0.3
        
        # Extract website from logo URL if possible
        website = ""
        if station['logo'] and station['logo'].startswith('http'):
            parsed_url = urllib.parse.urlparse(station['logo'])
            if parsed_url.netloc:
                website = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Create the station entry
        station_entry = {
            "id": station_id,
            "name": station['name'],
            "country": station['country'],
            "language": station['language'],
            "genres": station['genres'],
            "website": website,
            "streams": [
                {
                    "url": station['url'],
                    "format": station['format'],
                    "bitrate": station['bitrate'],
                    "reliability": reliability
                }
            ],
            "tags": station['genres'][:3] if station['genres'] else [],
            "lastChecked": updated_time,
            "logo": station['logo'],
            "source": station['source_file']
        }
        
        catalog["stations"].append(station_entry)
    
    # Write to JSON file
    catalog_file = METADATA_DIR / 'catalog.json'
    with open(catalog_file, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Generated metadata catalog with {len(stations)} stations")
    return catalog

def generate_unified_playlist(stations, output_file):
    """Generate a unified M3U playlist with all stations."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for station in stations:
            genres = ','.join(station['genres'])
            f.write(f'#EXTINF:-1 tvg-logo="{station["logo"]}" '
                   f'group-title="{genres}",{station["name"]}\n')
            f.write(f'{station["url"]}\n')
    
    logging.info(f"Generated unified playlist with {len(stations)} stations")

def generate_by_country_playlists(stations):
    """Generate country-specific M3U playlists for all stations."""
    # Create a directory for country playlists if it doesn't exist
    country_dir = OUTPUT_DIR / 'by_country'
    country_dir.mkdir(exist_ok=True)
    
    # Group stations by country code
    stations_by_country = defaultdict(list)
    for station in stations:
        country_code = station['country_code'].lower()
        stations_by_country[country_code].append(station)
    
    # Generate a playlist for each country
    for country_code, country_stations in stations_by_country.items():
        output_file = country_dir / f"{country_code}.m3u"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for station in country_stations:
                genres = ';'.join(station['genres'])
                f.write(f'#EXTINF:-1 tvg-logo="{station["logo"]}" '
                       f'group-title="{genres}",{station["name"]}\n')
                f.write(f'{station["url"]}\n')
        
        logging.info(f"Generated {country_code} playlist with {len(country_stations)} stations")
    
    return len(stations_by_country)

def generate_summary_metadata(stations, country_counts, country_files, genre_data):
    """Generate summary metadata JSON file with project statistics."""
    metadata = {
        'total_stations': len(stations),
        'total_countries': len(country_counts),
        'countries': [
            {'code': code, 'count': count}
            for code, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        'country_files': country_files,
        'genre_stats': genre_data,
        'updated':datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # Write metadata to JSON file
    with open(OUTPUT_DIR / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logging.info(f"Generated summary metadata with {len(stations)} stations from {len(country_counts)} countries")
    return metadata

def main():
    logging.info("Starting metadata catalog generation")
    
    # Load validation results if available
    validation_results = load_validation_results()
    logging.info(f"Loaded validation results for {len(validation_results.get('stations', {}))} stations")
    
    # Get all stations and country statistics
    all_stations, country_counts, country_files = get_all_stations()
    
    # Generate metadata catalog
    catalog = generate_metadata_catalog(all_stations, validation_results)
    
    # Generate unified playlist
    unified_playlist_path = OUTPUT_DIR / 'all_stations.m3u'
    generate_unified_playlist(all_stations, unified_playlist_path)
    
    # Generate country-specific playlists
    country_count = generate_by_country_playlists(all_stations)
    logging.info(f"Generated {country_count} country-specific playlists")
    
    # Analyze genres
    genre_data = analyze_genres(all_stations)
    
    # Generate summary metadata
    summary = generate_summary_metadata(all_stations, country_counts, country_files, genre_data)
    
    # Print summary
    logging.info(f"Generated data for {summary['total_stations']} stations from {summary['total_countries']} countries")
    logging.info(f"Found {genre_data['total_unique_genres']} unique genres")
    logging.info(f"Top 5 genres: {', '.join([g['name'] for g in genre_data['top_genres'][:5]])}")
    logging.info(f"Top 5 countries by station count: {', '.join([c['code'] + ' (' + str(c['count']) + ')' for c in summary['countries'][:5]])}")
    
    logging.info("Metadata catalog generation complete")

if __name__ == "__main__":
    main()