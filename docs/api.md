---
layout: default
title: IPRD API Documentation
nav_order: 3
---

# IPRD API Documentation

The International Public Radio Directory (IPRD) provides several data files that you can use to integrate radio station information into your applications.

## Catalog JSON Structure

The main catalog is available at: `{{ site.baseurl }}/site_data/metadata/catalog.json`

### Catalog Overview

The catalog contains metadata about all radio stations in the IPRD collection. Here's the structure:

```json
{
  "version": "1.0",
  "updated": "2023-06-12T15:30:45Z",
  "stations": [
    {
      "id": "us-wnyc-12ab34cd",
      "name": "WNYC",
      "country": "United States",
      "language": "English",
      "genres": ["News", "Talk", "Public Radio"],
      "website": "https://www.wnyc.org",
      "streams": [
        {
          "url": "https://fm939.wnyc.org/wnycfm",
          "format": "MP3",
          "bitrate": 128,
          "reliability": 0.95
        }
      ],
      "tags": ["News", "Talk", "Public Radio"],
      "lastChecked": "2023-06-12T15:30:45Z",
      "logo": "https://media.wnyc.org/i/300/300/l/80/1/wnyc_logo.png",
      "source": "streams/us/us.m3u"
    }
  ]
}
```

### Station Object Properties

| Property | Type | Description |
|----------|------|-------------|
| id | string | Unique identifier for the station |
| name | string | Station name |
| country | string | Country where the station is based |
| language | string | Primary broadcast language |
| genres | array | List of genres associated with the station |
| website | string | Station website URL |
| streams | array | List of available streams |
| tags | array | Keywords associated with the station |
| lastChecked | string | ISO 8601 timestamp of last validation |
| logo | string | URL to station logo image |
| source | string | Source file path in the IPRD repository |

### Stream Object Properties

| Property | Type | Description |
|----------|------|-------------|
| url | string | Direct URL to the audio stream |
| format | string | Audio format (MP3, AAC, etc.) |
| bitrate | number | Stream bitrate in kbps |
| reliability | number | Reliability score (0-1) based on validation |

## Summary Metadata

Summary statistics are available at: `{{ site.baseurl }}/site_data/summary.json`

This file contains overall statistics about the directory:

```json
{
  "total_stations": 5243,
  "total_countries": 150,
  "countries": [
    {"code": "US", "count": 820},
    {"code": "FR", "count": 452},
    {"code": "DE", "count": 398}
  ],
  "genre_stats": {
    "total_unique_genres": 128,
    "top_genres": [
      {"name": "pop", "count": 1240},
      {"name": "news", "count": 1105},
      {"name": "rock", "count": 980}
    ]
  },
  "updated": "2023-06-12T15:30:45Z"
}
```

## How to Access the Data

You can access the data in several ways:

1. **Direct JSON**: Access the raw JSON files directly from the GitHub Pages URL
   ```
   https://iprd-org.github.io/iprd/site_data/metadata/catalog.json
   https://iprd-org.github.io/iprd/site_data/summary.json
   ```

2. **Playlists**: Access M3U playlists directly
   ```
   https://iprd-org.github.io/iprd/site_data/all_stations.m3u
   https://iprd-org.github.io/iprd/site_data/by_country/us.m3u
   ```

3. **GitHub Repository**: Clone or download the repository to access all files locally
   ```
   git clone https://github.com/iprd-org/iprd.git
   ```

## Examples

### JavaScript Example

```javascript
// Fetch the catalog and display station count
fetch('https://iprd-org.github.io/iprd/site_data/metadata/catalog.json')
  .then(response => response.json())
  .then(data => {
    console.log(`Found ${data.stations.length} radio stations`);
    
    // Filter stations by country
    const frenchStations = data.stations.filter(station => 
      station.country === "France"
    );
    
    console.log(`There are ${frenchStations.length} stations from France`);
  });
```

### Python Example

```python
import requests
import json

# Fetch the catalog
response = requests.get('https://iprd-org.github.io/iprd/site_data/metadata/catalog.json')
catalog = response.json()

# Get all stations with high reliability
reliable_stations = [
    station for station in catalog['stations']
    if any(stream['reliability'] > 0.9 for stream in station['streams'])
]

print(f"Found {len(reliable_stations)} highly reliable stations")
```

## Limitations and Usage Guidelines

- The API is rate-limited through GitHub Pages, please cache results when appropriate
- Station availability is checked periodically but may not reflect real-time status
- Consider adding attribution to IPRD when using this data in your applications
