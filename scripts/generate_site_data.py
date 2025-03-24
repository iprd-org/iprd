import os
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
import logging

#!/usr/bin/env python3
"""
Generate site data for the IPRD project, including:
- Metadata file
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
OUTPUT_DIR = ROOT_DIR / "site_data"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)

def parse_m3u_file(file_path):
    """Parse an M3U file and extract station information."""
    stations = []
    current_station = None
    
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
                    genres = [genre.strip() for genre in group_title.split(',')]
                    
                    current_station = {
                        'name': station_name,
                        'logo': logo_url,
                        'genres': genres,
                        'country': os.path.basename(file_path).split('.')[0].upper()
                    }
            elif current_station and line.startswith(('http://', 'https://')):
                # This is a URL line
                current_station['url'] = line
                stations.append(current_station)
                current_station = None
                
    return stations

def get_all_stations():
    """Get all stations from all M3U files."""
    all_stations = []
    country_counts = defaultdict(int)
    country_files = []
    
    for file_path in STREAMS_DIR.glob('**/*.m3u'):
        if file_path.is_file():
            country_code = file_path.stem
            stations = parse_m3u_file(file_path)
            all_stations.extend(stations)
            country_counts[country_code.upper()] = len(stations)
            country_files.append({
                'code': country_code.upper(),
                'file': file_path.relative_to(ROOT_DIR).as_posix(),
                'count': len(stations)
            })
            logging.info(f"Processed {file_path.name}: {len(stations)} stations")
    
    return all_stations, country_counts, country_files

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

def generate_metadata(stations, country_counts, country_files, genre_data):
    """Generate metadata JSON file with project statistics."""
    metadata = {
        'total_stations': len(stations),
        'total_countries': len(country_counts),
        'countries': [
            {'code': code, 'count': count}
            for code, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        'country_files': country_files,
        'genre_stats': genre_data
    }
    
    # Write metadata to JSON file
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logging.info(f"Generated metadata with {len(stations)} stations from {len(country_counts)} countries")
    return metadata

def generate_station_json(stations, output_file):
    """Generate a JSON file with all stations in the specified format."""
    import datetime
    
    # Create a unique ID for each station based on country and name
    for i, station in enumerate(stations):
        country_code = station["country"].lower()
        station_name = re.sub(r'[^a-zA-Z0-9]', '-', station["name"].lower())
        station["id"] = f"{country_code}-{station_name}-{i}"
    
    # Convert to the required JSON structure
    stations_json = {
        "version": "1.0",
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stations": [
            {
                "id": station["id"],
                "name": station["name"],
                "country": station["country"],
                "language": "",  # We don't have language data
                "genres": station["genres"],
                "website": "",  # We don't have website data
                "streams": [
                    {
                        "url": station["url"],
                        "format": station["url"].split(".")[-1].upper() if "." in station["url"] else "Unknown",
                        "bitrate": 0,  # We don't have bitrate data
                        "reliability": 0.9  # Default reliability
                    }
                ],
                "tags": station["genres"][:2] if station["genres"] else [],  # Use first 2 genres as tags
                "lastChecked": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            for station in stations
        ]
    }
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stations_json, f, indent=2)
    
    logging.info(f"Generated JSON playlist with {len(stations)} stations")
    return stations_json

def main():
    logging.info("Starting site data generation")
    
    # Get all stations and country statistics
    all_stations, country_counts, country_files = get_all_stations()
    
    # Generate stations JSON file
    unified_json_path = OUTPUT_DIR / 'all_stations.json'
    generate_station_json(all_stations, unified_json_path)
    
    # Analyze genres
    genre_data = analyze_genres(all_stations)
    
    # Generate metadata
    metadata = generate_metadata(all_stations, country_counts, country_files, genre_data)
    
    # Print summary
    logging.info(f"Generated data for {metadata['total_stations']} stations from {metadata['total_countries']} countries")
    logging.info(f"Found {genre_data['total_unique_genres']} unique genres")
    logging.info(f"Top 5 genres: {', '.join([g['name'] for g in genre_data['top_genres'][:5]])}")
    logging.info(f"Top 5 countries by station count: {', '.join([f'{c['code']} ({c['count']})' for c in metadata['countries'][:5]])}")
    
    logging.info("Site data generation complete")