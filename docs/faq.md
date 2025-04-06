---
layout: default
title: Frequently Asked Questions
nav_order: 6
---

# Frequently Asked Questions (FAQ)

## About IPRD

### What is IPRD?
The International Public Radio Directory (IPRD) is an open, collaborative directory of public radio stations from around the world, providing direct links to their streaming feeds.

### Who maintains IPRD?
IPRD is maintained by a community of volunteer contributors. The project is hosted on GitHub, allowing anyone to contribute.

### Is IPRD free?
Yes, IPRD is completely free and open source under the MIT License.

## Usage

### How do I listen to a station?
Download one of the M3U playlists available on our [catalog page](./catalog.md) and open it in your preferred media player like VLC or Winamp. For detailed instructions, see our [usage guide](./usage.md).

### What stream formats are supported?
IPRD lists streams in various formats including MP3, AAC, OGG, and FLAC. Compatibility depends on your media player.

### Can I use IPRD on my mobile device?
Yes, you can use any mobile app that supports the M3U format, such as VLC for mobile.

### Are the links always up-to-date?
We regularly check links, but some may temporarily or permanently stop working. If you find a dead link, please report it through our GitHub issue system.

## Technical

### What is an M3U file?
M3U is a standard playlist file format that contains links to audio streams and metadata such as station names and genres.

### How do I know what bitrate is available?
Bitrate information is included in the JSON catalog. In the M3U files, bitrate can often be inferred from the stream URL or station name.

### Do all streams work in every country?
Some stations may apply geo-restrictions, limiting access to certain countries or regions.

## Contributing

### How can I add a station?
You can contribute by creating an issue on our GitHub repository with the station details, or by directly submitting a pull request. See our [contribution guide](https://github.com/iprd-org/IPRD/blob/main/CONTRIBUTING.md) for more information.

### What information is needed to add a new station?
You'll need to provide:
- Station name
- Direct stream URL
- Country of origin
- Genre(s)
- Logo URL (optional)

### How do I report an issue?
Please create an issue on our GitHub repository describing the problem in detail, including steps to reproduce.

## Data and API

### Can I programmatically access IPRD data?
Yes, all our data is available in JSON format. See our [API documentation](./api.md) for more information.

### Can I integrate IPRD into my application?
Yes, you're free to use IPRD data in your application according to our MIT license. We appreciate attribution to the IPRD project.

### How many stations are available?
The number of stations varies as we add new content. Check our [summary page](https://iprd-org.github.io/IPRD/site_data/summary.json) for up-to-date statistics.
