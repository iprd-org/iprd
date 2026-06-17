#!/usr/bin/env python3
import datetime
import hashlib
import json
import logging
import re
import urllib.parse
from collections import Counter
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from typing import Any

import pycountry

"""
Generate site data for the IPRD project using modern Python 3.13+ patterns.
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Project paths
ROOT_DIR = Path(__file__).resolve().parent.parent
STREAMS_DIR = ROOT_DIR / "streams"
METADATA_DIR = ROOT_DIR / "docs" / "site_data" / "metadata"
OUTPUT_DIR = ROOT_DIR / "docs" / "site_data"
VALIDATION_RESULTS_FILE = ROOT_DIR / "validation-results.json"

OUTPUT_DIR.mkdir(exist_ok=True)
METADATA_DIR.mkdir(exist_ok=True)

# Audio format mapping
AUDIO_FORMATS: dict[str, tuple[str, int]] = {
    "mp3": ("MP3", 128),
    "aac": ("AAC", 128),
    "ogg": ("OGG", 128),
    "flac": ("FLAC", 960),
    "m4a": ("AAC", 128),
    "opus": ("OPUS", 96),
    "wav": ("WAV", 1411),
}

FORMAT_IDENTIFIERS: dict[str, tuple[str, ...]] = {
    "mp3": ("mp3", "mpeg"),
    "aac": ("aac", "aacp", "he-aac"),
    "ogg": ("ogg", "vorbis"),
    "flac": ("flac",),
    "opus": ("opus",),
    "wav": ("wav", "pcm"),
}

# Pre-compiled regex
_BITRATE_RE = re.compile(r"[-_/.](\d+)(?:k|kbps|kb)?[-_/.]", re.IGNORECASE)
_EXTINF_RE = re.compile(r'tvg-logo="([^"]*)".*group-title="([^"]*)",(.*)')
_ID_CLEAN_RE = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class Station:
    """Immutable-ish station data container."""
    id: str
    name: str
    logo: str
    genres: tuple[str, ...]
    country_code: str
    country: str
    language: tuple[str, ...]
    url: str
    format: str
    bitrate: int
    source_file: str

    def to_catalog_dict(self, reliability: float, checked: str) -> dict[str, Any]:
        """Convert to the JSON catalog format."""
        website = ""
        if self.logo.startswith("http"):
            parsed = urllib.parse.urlparse(self.logo)
            website = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else ""

        genres = list(self.genres)
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "language": list(self.language),
            "genres": genres,
            "website": website,
            "streams": [{
                "url": self.url,
                "format": self.format,
                "bitrate": self.bitrate,
                "reliability": reliability,
            }],
            "tags": genres[:3],
            "lastChecked": checked,
            "logo": self.logo,
            "source": self.source_file,
        }


@lru_cache(maxsize=256)
def get_country_name(code: str) -> str:
    """Resolve ISO-3166 alpha-2 to country name."""
    try:
        if country := pycountry.countries.get(alpha_2=code.upper()):
            return country.name
    except (KeyError, LookupError):
        pass
    return code.upper()


@lru_cache(maxsize=256)
def get_language_from_country(code: str) -> tuple[str, ...]:
    """
    Heuristic: try to map country code -> language name via pycountry.
    (Replaces babel Locale parsing with a direct lookup.)
    """
    try:
        if lang := pycountry.languages.get(alpha_2=code.lower()):
            if getattr(lang, "name", None):
                return (lang.name,)
    except Exception:
        pass
    return ()


def _extract_bitrate(url: str) -> int:
    """Guess bitrate from URL tokens."""
    if match := _BITRATE_RE.search(url.lower()):
        if 32 <= (b := int(match.group(1))) <= 1411:
            return b
    return 0


def _determine_format(url: str) -> tuple[str, int]:
    """Guess audio format from URL path and query parameters."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()

    # Extension check
    if "." in path:
        ext = path.rsplit(".", 1)[-1]
        if ext in AUDIO_FORMATS:
            return AUDIO_FORMATS[ext]

    # Identifier check in full URL
    url_lower = url.lower()
    for fmt, ids in FORMAT_IDENTIFIERS.items():
        if any(i in url_lower for i in ids):
            return AUDIO_FORMATS[fmt]

    # Query parameter check
    if parsed.query:
        query = urllib.parse.parse_qs(parsed.query)
        for key in ("format", "fmt", "type"):
            for val in query.get(key, []):
                v = val.lower()
                for fmt, ids in FORMAT_IDENTIFIERS.items():
                    if v in ids:
                        return AUDIO_FORMATS[fmt]

    return "Unknown", 0


def _generate_id(station: Station) -> str:
    """URL-friendly unique station ID."""
    base = f"{station.country_code.lower()}-{station.name.lower()}"
    base = _ID_CLEAN_RE.sub("-", base).strip("-")
    h = hashlib.md5(station.url.encode(), usedforsecurity=False).hexdigest()[:8]
    return f"{base}-{h}"


def parse_m3u(file_path: Path) -> Iterator[Station]:
    """Yield Station objects from a single M3U file."""
    cc = file_path.parent.name.upper()
    country = get_country_name(cc)
    language = get_language_from_country(cc)
    rel_path = str(file_path.relative_to(ROOT_DIR))

    current: dict[str, Any] | None = None

    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith(("#EXTM3U", "//")):
                continue

            if line.startswith("#EXTINF:"):
                if m := _EXTINF_RE.search(line):
                    current = {
                        "name": m.group(3).strip(),
                        "logo": m.group(1),
                        "genres": tuple(g.strip() for g in m.group(2).split(";")),
                    }
            elif current and line.startswith(("http://", "https://")):
                fmt, default_bitrate = _determine_format(line)
                bitrate = _extract_bitrate(line) or default_bitrate

                s = Station(
                    id="",  # filled below
                    name=current["name"],
                    logo=current["logo"],
                    genres=current["genres"],
                    country_code=cc,
                    country=country,
                    language=language,
                    url=line,
                    format=fmt,
                    bitrate=bitrate,
                    source_file=rel_path,
                )
                object.__setattr__(s, "id", _generate_id(s))
                yield s
                current = None


def load_validation_results() -> dict[str, str]:
    """Load validation map {url: status}."""
    if VALIDATION_RESULTS_FILE.exists():
        try:
            with open(VALIDATION_RESULTS_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh).get("stations", {})
        except (json.JSONDecodeError, OSError) as exc:
            logging.warning("Failed to load validation results: %s", exc)
    return {}


def build_catalog(
    stations: list[Station],
    validation: dict[str, str],
) -> dict[str, Any]:
    """Write catalog.json and return the in-memory dict."""
    checked = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    catalog = {
        "version": "1.0",
        "updated": checked,
        "stations": [
            s.to_catalog_dict(
                reliability=0.95 if validation.get(s.url) == "ok" else 0.3 if s.url in validation else 0.5,
                checked=checked,
            )
            for s in stations
        ],
    }

    catalog_file = METADATA_DIR / "catalog.json"
    with open(catalog_file, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, ensure_ascii=False)

    logging.info("Generated metadata catalog with %d stations", len(stations))
    return catalog


def write_unified_playlist(stations: list[Station], path: Path) -> None:
    """Write a single M3U with all stations."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("#EXTM3U\n")
        for s in stations:
            fh.write(f'#EXTINF:-1 tvg-logo="{s.logo}" group-title="{",".join(s.genres)}",{s.name}\n')
            fh.write(f"{s.url}\n")
    logging.info("Generated unified playlist (%d stations)", len(stations))


def write_country_playlists(stations: list[Station]) -> int:
    """Write one M3U per country using itertools.groupby."""
    country_dir = OUTPUT_DIR / "by_country"
    country_dir.mkdir(exist_ok=True)

    # groupby requires pre-sorting
    sorted_stations = sorted(stations, key=lambda s: s.country_code)
    count = 0

    for cc, group in groupby(sorted_stations, key=lambda s: s.country_code.lower()):
        path = country_dir / f"{cc}.m3u"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("#EXTM3U\n")
            n = 0
            for s in group:
                fh.write(f'#EXTINF:-1 tvg-logo="{s.logo}" group-title="{";".join(s.genres)}",{s.name}\n')
                fh.write(f"{s.url}\n")
                n += 1
        logging.info("Generated %s playlist (%d stations)", cc, n)
        count += 1

    return count


def analyze_genres(stations: list[Station]) -> dict[str, Any]:
    """Genre statistics using a Counter."""
    counter = Counter(g.lower() for s in stations for g in s.genres)
    return {
        "total_unique_genres": len(counter),
        "top_genres": [{"name": g, "count": c} for g, c in counter.most_common(50)],
    }


def write_summary(
    stations: list[Station],
    genre_data: dict[str, Any],
) -> dict[str, Any]:
    """Write summary.json."""
    country_counts = Counter(s.country_code for s in stations)

    summary = {
        "total_stations": len(stations),
        "total_countries": len(country_counts),
        "countries": [
            {"code": c, "count": n}
            for c, n in country_counts.most_common()
        ],
        "genre_stats": genre_data,
        "updated": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def main() -> None:
    logging.info("Starting metadata catalog generation")

    validation = load_validation_results()
    logging.info("Loaded validation results for %d stations", len(validation))

    # Parse all M3U files
    all_stations: list[Station] = []
    for m3u in sorted(STREAMS_DIR.rglob("*.m3u")):
        if not m3u.is_file():
            continue
        stations = list(parse_m3u(m3u))
        all_stations.extend(stations)
        logging.info("Processed %s: %d stations", m3u.name, len(stations))

    # Generate outputs
    build_catalog(all_stations, validation)
    write_unified_playlist(all_stations, OUTPUT_DIR / "all_stations.m3u")
    country_count = write_country_playlists(all_stations)
    genre_data = analyze_genres(all_stations)
    summary = write_summary(all_stations, genre_data)

    # Log summary
    logging.info(
        "Done: %d stations, %d countries, %d genres",
        summary["total_stations"],
        summary["total_countries"],
        genre_data["total_unique_genres"],
    )
    logging.info(
        "Top 5 countries: %s",
        ", ".join(f"{c['code']} ({c['count']})" for c in summary["countries"][:5]),
    )
    logging.info(
        "Top 5 genres: %s",
        ", ".join(g["name"] for g in genre_data["top_genres"][:5]),
    )


if __name__ == "__main__":
    main()
