# IPRD Project

## Overview
Listen to your favorite radio stations in one single place. IPRD is a collection of curated internet radio streams organized by country and broadcasting groups. The project aims to provide an easily accessible library of radio stations from around the world in M3U playlist format.

## Features
- Curated internet radio streams
- Organized by country and broadcasting groups
- Easily accessible library in M3U playlist format

## Documentation
Documentation is available in [our website](https://iprd-org.github.io/iprd).

## Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the [LICENSE](LICENSE) - see the file for details.

## Current state of IPRD

Work in Progress (2026-01-24)

## Usage

1. Choose a playlist from the repository (by country or group)
2. Open it with your favorite media player that supports M3U playlists (VLC, Winamp, etc.)
3. Enjoy your radio stations!

## Playlist Organization

Our radio station playlists follow this organization:

- **country.m3u** - Contains standalone radio stations from a specific country
- **country_group.m3u** - Contains radio stations that belong to a broadcasting group/conglomerate

## How to Contribute

[2026-01-25] While we're constantly improving the IPRD lists & ecosystem, issues are *disabled* (for now) to ensure that we can provide a clean base for everyone to work on.

Contributions are always welcome! To add a new radio station:

1. Create an issue with the radio station you would like to add
2. Include the following information:
    - Station name
    - Stream URL (direct stream link preferred)
    - Country
    - Broadcasting group (if applicable)
    - Stream quality information

The higher the radio quality, the better the listening experience will be (lossless > compressed).

## Technical Details

- All playlists are in standard M3U format
- Stream URLs should be direct links to media streams
- We prioritize higher quality streams when multiple options exist

## Future Plans

- [ ] Properly identify the radios and their groups for easier maintenance
- [ ] Create scripts to generate comprehensive playlists containing all stations
- [ ] Develop a searchable radio station database
- [ ] Add genre categorization
- [ ] Implement regular link validation to ensure all streams remain active
