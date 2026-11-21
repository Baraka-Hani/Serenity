"""Place trips on the Map from the GPS metadata recorded inside their videos.

LOCAL, OPT-IN tool for the app owner. Dry run by default; nothing is written
without --apply.

    python3 backend/video_locations.py                       # propose pins from uploaded clips
    python3 backend/video_locations.py --source-root '/path/to/Photos Library.photoslibrary/originals'
                                                            # also read the seeded demo originals
    python3 backend/video_locations.py --apply               # save pins for trips that have none

Phones store where a video was filmed as an ISO 6709 string, e.g. "+35.0116+135.7681+045.000/":
iPhones in the QuickTime key com.apple.quicktime.location.ISO6709, Android and older
cameras in the ©xyz user-data atom. Both are read here without extra dependencies;
ffprobe is used as a fallback when it is installed.

Privacy: a pin on a published trip is public on Map. Coordinates are rounded to
--precision decimal places (default 2, about 1 km) so an exact filming spot, such as a
home, is never published. Existing creator-chosen pins are kept unless --replace.
Nothing leaves this computer unless --reverse-geocode is given, which sends the
rounded coordinates to the configured Photon server to name each place.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import server
import trip_locations

APPLE_KEY = "com.apple.quicktime.location.ISO6709"
_CONTAINERS = {b"moov", b"udta", b"trak", b"meta"}
_MAX_MOOV = 64 * 1024 * 1024
_ISO6709 = re.compile(r"^\s*([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)(?:[+-]\d+(?:\.\d+)?)?(?:CRS[^/]*)?/?\s*$")


def _to_degrees(text, degree_digits):
    """ISO 6709 allows ±DD.D, ±DDMM.M and ±DDMMSS.S (latitude; longitude has 3 degree digits)."""
    sign = -1 if text[0] == "-" else 1
    whole, _, fraction = text[1:].partition(".")
    fraction = float("0." + fraction) if fraction else 0.0
    if len(whole) == degree_digits:
        value = int(whole) + fraction
    elif len(whole) == degree_digits + 2:
        value = int(whole[:degree_digits]) + (int(whole[degree_digits:]) + fraction) / 60
    elif len(whole) == degree_digits + 4:
        value = int(whole[:degree_digits]) + int(whole[degree_digits:degree_digits + 2]) / 60 + (int(whole[degree_digits + 2:]) + fraction) / 3600
    else:
        # Some writers drop leading zeros ("+5.6-0.12"); treat short forms as decimal degrees.
        if len(whole) > degree_digits:
            raise ValueError("Unrecognised ISO 6709 coordinate.")
        value = int(whole or 0) + fraction
    return sign * value


def parse_iso6709(text):
    """Return (lat, lng) or None for an ISO 6709 location string."""
    if not isinstance(text, str):
        return None
    match = _ISO6709.match(text)
    if not match:
        return None
    try:
        lat, lng = _to_degrees(match.group(1), 2), _to_degrees(match.group(2), 3)
    except ValueError:
        return None
    return valid_point(lat, lng)


def valid_point(lat, lng):
    if not (math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
        return None  # 0,0 is the classic "no fix" value, not a place
    return lat, lng


def _boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    offset = start
    while offset + 8 <= end:
        size, kind = struct.unpack(">I4s", data[offset:offset + 8])
        header = 8
        if size == 1:
            if offset + 16 > end:
                return
            size = struct.unpack(">Q", data[offset + 8:offset + 16])[0]
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            return
        yield kind, offset + header, offset + size
        offset += size


def _location_strings(data, start, end, found):
    for kind, body, stop in _boxes(data, start, end):
        if kind == b"loci" and stop - body >= 20:
            # 3GPP location box: version/flags, language, name (null-terminated), role, then
            # longitude, latitude and altitude as signed 16.16 fixed-point numbers.
            cursor = body + 6
            if data[cursor:cursor + 2] in (b"\xfe\xff", b"\xff\xfe"):
                while cursor + 1 < stop and data[cursor:cursor + 2] != b"\0\0":
                    cursor += 2
                cursor += 2
            else:
                cursor = data.index(b"\0", cursor, stop) + 1
            cursor += 1  # role
            if cursor + 8 <= stop:
                lng, lat = struct.unpack(">ii", data[cursor:cursor + 8])
                found.append((lat / 65536, lng / 65536))
        elif kind == b"\xa9xyz" and stop - body > 4:
            length = struct.unpack(">H", data[body:body + 2])[0]
            found.append(data[body + 4:body + 4 + length].decode("utf-8", "replace"))
        elif kind == b"meta":
            # ISO 'meta' is a full box (4 bytes version/flags); QuickTime's is not.
            if data[body + 4:body + 8] == b"hdlr":
                inner = body
            elif data[body + 8:body + 12] == b"hdlr":
                inner = body + 4
            else:
                inner = body + 4 if data[body:body + 4] == b"\0\0\0\0" else body
            keys, items = [], {}
            for child, child_body, child_stop in _boxes(data, inner, stop):
                if child == b"keys":
                    count = struct.unpack(">I", data[child_body + 4:child_body + 8])[0]
                    cursor = child_body + 8
                    for _ in range(count):
                        if cursor + 8 > child_stop:
                            break
                        size = struct.unpack(">I", data[cursor:cursor + 4])[0]
                        keys.append(data[cursor + 8:cursor + size].decode("utf-8", "replace"))
                        cursor += max(size, 8)
                elif child == b"ilst":
                    for item, item_body, item_stop in _boxes(data, child_body, child_stop):
                        index = struct.unpack(">I", item)[0]
                        for value_kind, value_body, value_stop in _boxes(data, item_body, item_stop):
                            if value_kind == b"data":
                                items[index] = data[value_body + 8:value_stop].decode("utf-8", "replace")
                elif child in _CONTAINERS:
                    _location_strings(data, child_body, child_stop, found)
            for index, key in enumerate(keys, 1):
                if key == APPLE_KEY and index in items:
                    found.insert(0, items[index])  # prefer Apple's precise key
        elif kind in _CONTAINERS:
            _location_strings(data, body, stop, found)


def _moov(path):
    with open(path, "rb") as source:
        size_total = os.fstat(source.fileno()).st_size
        offset = 0
        while offset + 8 <= size_total:
            source.seek(offset)
            header = source.read(16)
            size, kind = struct.unpack(">I4s", header[:8])
            if size == 1:
                size = struct.unpack(">Q", header[8:16])[0]
            elif size == 0:
                size = size_total - offset
            if size < 8:
                return None
            if kind == b"moov":
                if size > _MAX_MOOV:
                    return None
                source.seek(offset)
                return source.read(size)
            offset += size
    return None


def read_location(path):
    """Return (lat, lng) recorded in a video file, or None. Never raises for bad files."""
    try:
        moov = _moov(path)
        if moov:
            found = []
            _location_strings(moov, 8, len(moov), found)
            for text in found:
                point = parse_iso6709(text) if isinstance(text, str) else valid_point(*text)
                if point:
                    return point
    except (OSError, struct.error, ValueError):
        pass
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(path)],
                                capture_output=True, text=True, timeout=30)
        tags = {}
        payload = json.loads(result.stdout or "{}")
        for block in [payload.get("format", {})] + payload.get("streams", []):
            tags.update({key.lower(): value for key, value in (block.get("tags") or {}).items()})
        for key in (APPLE_KEY, "location", "location-eng"):
            point = parse_iso6709(tags.get(key))
            if point:
                return point
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return None


def distance_km(a, b):
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def central_point(points):
    """The clip location closest to all the others (a medoid): robust to a stray clip."""
    best = min(points, key=lambda point: sum(distance_km(point, other) for other in points))
    return best, max(distance_km(best, other) for other in points)


def coordinate_label(lat, lng):
    return f"Filmed near {abs(lat):.2f}°{'N' if lat >= 0 else 'S'}, {abs(lng):.2f}°{'E' if lng >= 0 else 'W'}"


def reverse_geocode(lat, lng):
    endpoint = trip_locations.SEARCH_URL.rstrip("/").removesuffix("/api") + "/reverse"
    request = Request(endpoint + "?" + urlencode({"lat": lat, "lon": lng, "lang": "en", "limit": 1}),
                      headers={"User-Agent": "SerenityTravelLocal/1.0 (local travel discovery prototype)", "Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        payload = json.loads(response.read(256 * 1024))
    props = (payload.get("features") or [{}])[0].get("properties", {})
    parts = [props.get(key) for key in ("city", "county", "state", "country")]
    label = ", ".join(dict.fromkeys(str(part) for part in parts if part))
    return label[:240] or None


def plan(connection, uploads, source_root=None, precision=2, replace=False):
    """Read every trip's clips and propose one pin per trip. Read-only."""
    demo_sources = {}
    if source_root and connection.execute("SELECT 1 FROM sqlite_master WHERE name='demo_seed_clips'").fetchone():
        demo_sources = {row["clip_id"]: row["source_id"] for row in connection.execute("SELECT source_id, clip_id FROM demo_seed_clips")}
    trips = connection.execute("""SELECT f.id, f.name, f.user_id, u.username, l.source AS pin_source, l.label AS pin_label
        FROM user_feeds f JOIN users u ON u.id=f.user_id LEFT JOIN trip_locations l ON l.feed_id=f.id ORDER BY f.id""").fetchall()
    proposals = []
    for trip in trips:
        clips = connection.execute("SELECT id FROM clips WHERE feed_id=? AND user_id=? ORDER BY created_at, rowid", (trip["id"], trip["user_id"])).fetchall()
        if not clips:
            continue
        points, read_from = [], {"upload": 0, "original": 0}
        for clip in clips:
            point = read_location(uploads / clip["id"])
            if point:
                read_from["upload"] += 1
            elif clip["id"] in demo_sources:
                source_id = demo_sources[clip["id"]]
                point = read_location(Path(source_root) / source_id[0] / f"{source_id}.mov")
                read_from["original"] += bool(point)
            if point:
                points.append(point)
        entry = {"trip_id": trip["id"], "trip": trip["name"], "owner": trip["username"], "clips": len(clips),
                 "clips_with_gps": len(points), "read_from": read_from, "existing_pin": trip["pin_label"]}
        if not points:
            entry["action"] = "skip: no GPS in these videos"
        elif trip["pin_source"] and not replace:
            entry["action"] = "keep: trip already has a pin (use --replace to override)"
        else:
            (lat, lng), spread = central_point(points)
            lat, lng = round(lat, precision), round(lng, precision)
            entry.update({"lat": lat, "lng": lng, "spread_km": round(spread, 1), "action": "pin"})
            if spread > 50:
                entry["warning"] = f"Clips were filmed up to {spread:.0f} km apart; the pin uses the most central clip."
        proposals.append(entry)
    return proposals


def apply(connection, proposals, reverse=False):
    saved = 0
    for entry in proposals:
        if entry["action"] != "pin":
            continue
        label = None
        if reverse:
            try:
                label = reverse_geocode(entry["lat"], entry["lng"])
                time.sleep(1.1)  # stay within the public Photon server's fair-use rate
            except (OSError, ValueError, KeyError, IndexError, TypeError):
                label = None
        entry["label"] = label or coordinate_label(entry["lat"], entry["lng"])
        value = trip_locations.normalize({"lat": entry["lat"], "lng": entry["lng"], "label": entry["label"],
                                          "provider": "manual", "source": "pin", "place_id": ""})
        value["source"] = "video"  # set only here: the API cannot claim a pin came from video GPS
        owner = connection.execute("SELECT user_id FROM user_feeds WHERE id=?", (entry["trip_id"],)).fetchone()["user_id"]
        trip_locations.save(connection, owner, entry["trip_id"], value, trusted=True)
        saved += 1
    return saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-root", help="Photos originals folder used by seed_demo.py, for demo clips whose uploads lack GPS")
    parser.add_argument("--apply", action="store_true", help="Save the proposed pins (default: only print them)")
    parser.add_argument("--replace", action="store_true", help="Also replace pins that creators already chose")
    parser.add_argument("--precision", type=int, default=2, choices=range(1, 5), metavar="1-4",
                        help="Decimal places kept (2 ≈ 1 km, 3 ≈ 110 m, 4 ≈ 11 m). Default 2.")
    parser.add_argument("--reverse-geocode", action="store_true", help="Name places via the Photon server (sends rounded coordinates)")
    args = parser.parse_args(argv)
    if server.PUBLIC_ORIGIN or server.HOST not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Run this on the local Serenity data only, not on a shared or public server.")
    if args.source_root and not Path(args.source_root).is_dir():
        raise SystemExit(f"Source folder not found: {args.source_root}")
    if not server.DB.exists():
        raise SystemExit(f"No Serenity database at {server.DB}. Start the app once or set ROAM_DATA_DIR.")
    server.init()
    with server.db() as connection:
        proposals = plan(connection, server.UPLOADS, args.source_root, args.precision, args.replace)
    result = {"trips_checked": len(proposals), "pins_proposed": sum(entry["action"] == "pin" for entry in proposals), "proposals": proposals}
    if args.apply:
        backup = server.DATA / f"before-video-locations-{int(time.time())}.sqlite3"
        with server.db() as current, sqlite3.connect(backup) as target:
            current.backup(target)
        os.chmod(backup, 0o600)
        with server.db() as connection:
            result["pins_saved"] = apply(connection, proposals, args.reverse_geocode)
        result["backup"] = str(backup)
    else:
        result["changes"] = "none; add --apply to save these pins"
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
