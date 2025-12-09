#!/usr/bin/env python3
import os
import re
import json
import datetime
import hashlib
import logging
import urllib.parse
from functools import lru_cache
from pathlib import Path
from collections import defaultdict, Counter

import pycountry
from babel import Locale, UnknownLocaleError

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
METADATA_DIR = ROOT_DIR / "docs" / "site_data" / "metadata"
OUTPUT_DIR = ROOT_DIR / "docs" / "site_data"
VALIDATION_RESULTS_FILE = ROOT_DIR / "validation-results.json"

# Create output directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
METADATA_DIR.mkdir(exist_ok=True)

# Common audio format extensions and their details
AUDIO_FORMATS = {
    'mp3': ('MP3', 128),
    'aac': ('AAC', 128),
    'ogg': ('OGG', 128),
    'flac': ('FLAC', 960),
    'm4a': ('AAC', 128),
    'opus': ('OPUS', 96),
    'wav': ('WAV', 1411),
}

# Pre-compiled regex patterns for better performance
BITRATE_PATTERNS = [
    re.compile(r'[-_/](\d+)k[-_/.]', re.IGNORECASE),
    re.compile(r'[-_/](\d+)kbps[-_/.]', re.IGNORECASE),
    re.compile(r'[-_/](\d+)kb[-_/.]', re.IGNORECASE),
    re.compile(r'[-_/.](\d+)[-_/.]'),
]
EXTINF_PATTERN = re.compile(r'tvg-logo="([^"]*)".*group-title="([^"]*)",(.*)')
STATION_ID_CLEAN_PATTERN = re.compile(r'[^a-z0-9]')
STATION_ID_HYPHEN_PATTERN = re.compile(r'-+')

@lru_cache(maxsize=256)
def get_language_from_country(code: str) -> tuple[str, ...]:
    """Get official languages for a country code using babel and pycountry.
    
    Returns a tuple for hashability (required for lru_cache).
    """
    code = code.upper()
    langs = []
    
    try:
        # Get language codes commonly associated with this country
        country = pycountry.countries.get(alpha_2=code)
        if not country:
            return ()
        
        # Try common locale pattern for this country
        locale_str = f"{code.lower()}_{code}"  # e.g., fr_FR, de_DE
        try:
            locale = Locale.parse(locale_str)
            lang = pycountry.languages.get(alpha_2=locale.language)
            if lang and lang.name:
                langs.append(lang.name)
        except (UnknownLocaleError, ValueError):
            pass
        
        # Fallback: try to get language from country code directly
        if not langs:
            lang = pycountry.languages.get(alpha_2=code.lower())
            if lang and lang.name:
                langs.append(lang.name)
                
    except Exception:
        pass
    
    return tuple(langs)

def extract_bitrate_from_url(url: str) -> int:
    """Attempt to extract bitrate information from URL."""
    url_lower = url.lower()
    
    for pattern in BITRATE_PATTERNS:
        match = pattern.search(url_lower)
        if match:
            try:
                bitrate = int(match.group(1))
                # Filter out unlikely bitrates
                if 32 <= bitrate <= 1411:  # Common bitrate range
                    return bitrate
            except ValueError:
                pass
    
    # Try to determine from known stream providers
    if 'icecast' in url_lower:
        return 128  # Common default for Icecast
    
    return 0  # Unknown

# Format identifiers mapping (defined once at module level)
FORMAT_IDENTIFIERS = {
    'mp3': ('mp3', 'mpeg'),
    'aac': ('aac', 'aacp', 'he-aac'),
    'ogg': ('ogg', 'vorbis'),
    'flac': ('flac',),
    'opus': ('opus',),
    'wav': ('wav', 'pcm'),
}

def determine_audio_format(url: str) -> tuple[str, int]:
    """Determine audio format from URL and parameters."""
    parsed_url = urllib.parse.urlparse(url)
    path_lower = parsed_url.path.lower()
    url_lower = url.lower()
    
    # Extract extension from path
    dot_pos = path_lower.rfind('.')
    if dot_pos != -1:
        ext = path_lower[dot_pos + 1:]
        if ext in AUDIO_FORMATS:
            return AUDIO_FORMATS[ext]
    
    # Check common format identifiers in the URL
    for fmt, identifiers in FORMAT_IDENTIFIERS.items():
        for identifier in identifiers:
            if identifier in url_lower:
                return AUDIO_FORMATS[fmt]
    
    # Check query parameters for format clues
    if parsed_url.query:
        query_params = urllib.parse.parse_qs(parsed_url.query)
        for param_name, param_values in query_params.items():
            if param_name.lower() in ('format', 'fmt', 'type'):
                for value in param_values:
                    value_lower = value.lower()
                    for fmt, identifiers in FORMAT_IDENTIFIERS.items():
                        if value_lower in identifiers:
                            return AUDIO_FORMATS[fmt]
    
    return "Unknown", 0

def parse_m3u_file(file_path: Path) -> list[dict]:
    """Parse an M3U file and extract station information."""
    stations = []
    current_station = None
    country_code = file_path.parent.name
    country_code_upper = country_code.upper()
    
    # Cache country name and language for this file (all stations share the same country)
    country_name = get_country_name(country_code)
    language = list(get_language_from_country(country_code))
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('//', '#EXTM3U')):
                continue
                
            if line.startswith('#EXTINF:'):
                # Parse the EXTINF line
                match = EXTINF_PATTERN.search(line)
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
                        'country_code': country_code_upper,
                        'country': country_name,
                        'language': language
                    }
            elif current_station and (line.startswith('http://') or line.startswith('https://')):
                # This is a URL line
                current_station['url'] = line
                
                # Determine audio format and bitrate
                audio_format, default_bitrate = determine_audio_format(line)
                bitrate = extract_bitrate_from_url(line) or default_bitrate
                
                current_station['format'] = audio_format
                current_station['bitrate'] = bitrate
                
                # Generate a unique ID
                current_station['id'] = generate_station_id(current_station)
                
                stations.append(current_station)
                current_station = None
                
    return stations

def generate_station_id(station: dict) -> str:
    """Generate a unique ID for a station based on name, country, and URL."""
    # Create a base string from station name and country
    base = f"{station['country_code'].lower()}-{station['name'].lower()}"
    
    # Clean the base string to create a URL-friendly ID
    base = STATION_ID_CLEAN_PATTERN.sub('-', base)
    base = STATION_ID_HYPHEN_PATTERN.sub('-', base)  # Replace multiple hyphens with a single one
    base = base.strip('-')
    
    # Add a unique hash based on the URL to avoid conflicts
    url_hash = hashlib.md5(station['url'].encode(), usedforsecurity=False).hexdigest()[:8]
    
    return f"{base}-{url_hash}"

@lru_cache(maxsize=256)
def get_country_name(country_code: str) -> str:
    """Get the full country name from a country code using pycountry."""
    code_upper = country_code.upper()
    try:
        country = pycountry.countries.get(alpha_2=code_upper)
        if country:
            return country.name
    except (KeyError, LookupError):
        pass
    
    return code_upper

def load_validation_results():
    """Load validation results if available."""
    if VALIDATION_RESULTS_FILE.exists():
        try:
            with open(VALIDATION_RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to load validation results: {e}")
    
    return {'stations': {}}

def get_all_stations() -> tuple[list[dict], dict[str, int], list[dict]]:
    """Get all stations from all M3U files."""
    all_stations = []
    country_counts = defaultdict(int)
    country_files = []
    
    # Get all m3u files and sort for consistent ordering
    m3u_files = sorted(STREAMS_DIR.glob('**/*.m3u'))
    
    for file_path in m3u_files:
        if not file_path.is_file():
            continue
            
        country_code = file_path.parent.name
        country_code_upper = country_code.upper()
        stations = parse_m3u_file(file_path)
        station_count = len(stations)
        
        # Calculate relative path once
        relative_path = str(file_path.relative_to(ROOT_DIR))
        
        for station in stations:
            station['source_file'] = relative_path
        
        all_stations.extend(stations)
        country_counts[country_code_upper] += station_count
        country_files.append({
            'code': country_code_upper,
            'file': relative_path,
            'count': station_count
        })
        logging.info(f"Processed {file_path.name}: {station_count} stations")
    
    return all_stations, country_counts, country_files

def analyze_genres(stations: list[dict]) -> dict:
    """Analyze genres across all stations."""
    # Use generator expression for memory efficiency
    genre_counter = Counter(
        genre.lower()
        for station in stations
        for genre in station['genres']
    )
    
    # Get top genres
    top_genres = genre_counter.most_common(50)
    
    return {
        'total_unique_genres': len(genre_counter),
        'top_genres': [{'name': genre, 'count': count} for genre, count in top_genres]
    }

def generate_metadata_catalog(stations: list[dict], validation_results: dict) -> dict:
    """Generate metadata catalog JSON file with station information."""
    now = datetime.datetime.now(datetime.UTC)
    updated_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Pre-extract validation stations dict for faster lookup
    validation_stations = validation_results.get('stations', {}) if validation_results else {}
    
    # Pre-allocate list with known size
    catalog_stations = []
    
    # Add stations to the catalog
    for station in stations:
        # Determine reliability based on validation results
        url = station['url']
        if url in validation_stations:
            reliability = 0.95 if validation_stations[url] == 'ok' else 0.3
        else:
            reliability = 0.5  # Default reliability
        
        # Extract website from logo URL if possible
        logo = station['logo']
        website = ""
        if logo and logo.startswith('http'):
            parsed_url = urllib.parse.urlparse(logo)
            if parsed_url.netloc:
                website = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        genres = station['genres']
        
        # Create the station entry
        catalog_stations.append({
            "id": station['id'],
            "name": station['name'],
            "country": station['country'],
            "language": station['language'],
            "genres": genres,
            "website": website,
            "streams": [{
                "url": url,
                "format": station['format'],
                "bitrate": station['bitrate'],
                "reliability": reliability
            }],
            "tags": genres[:3] if genres else [],
            "lastChecked": updated_time,
            "logo": logo,
            "source": station['source_file']
        })
    
    # Create the catalog structure
    catalog = {
        "version": "1.0",
        "updated": updated_time,
        "stations": catalog_stations
    }
    
    # Write to JSON file
    catalog_file = METADATA_DIR / 'catalog.json'
    with open(catalog_file, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    logging.info(f"Generated metadata catalog with {len(stations)} stations")
    return catalog

def generate_unified_playlist(stations: list[dict], output_file: Path) -> None:
    """Generate a unified M3U playlist with all stations."""
    # Build content in memory for fewer I/O operations
    lines = ['#EXTM3U']
    for station in stations:
        genres = ','.join(station['genres'])
        lines.append(f'#EXTINF:-1 tvg-logo="{station["logo"]}" group-title="{genres}",{station["name"]}')
        lines.append(station['url'])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.write('\n')
    
    logging.info(f"Generated unified playlist with {len(stations)} stations")

def generate_by_country_playlists(stations: list[dict]) -> int:
    """Generate country-specific M3U playlists for all stations."""
    # Create a directory for country playlists if it doesn't exist
    country_dir = OUTPUT_DIR / 'by_country'
    country_dir.mkdir(exist_ok=True)
    
    # Group stations by country code
    stations_by_country = defaultdict(list)
    for station in stations:
        stations_by_country[station['country_code'].lower()].append(station)
    
    # Generate a playlist for each country
    for country_code, country_stations in stations_by_country.items():
        output_file = country_dir / f"{country_code}.m3u"
        
        # Build content in memory for fewer I/O operations
        lines = ['#EXTM3U']
        for station in country_stations:
            genres = ';'.join(station['genres'])
            lines.append(f'#EXTINF:-1 tvg-logo="{station["logo"]}" group-title="{genres}",{station["name"]}')
            lines.append(station['url'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            f.write('\n')
        
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
    generate_metadata_catalog(all_stations, validation_results)
    
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
