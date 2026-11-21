"""Shared, standards-compliant byte-range streaming for uploaded videos.

Browsers play video by issuing many HTTP Range requests. Two details matter for
smooth playback:

* Open-ended requests (``bytes=N-``) are answered with a bounded chunk instead of
  the rest of the file. A paused or off-screen <video> otherwise keeps a socket
  busy for the whole file, and browsers only open about six connections per
  host, so the video the person is watching starves and freezes.
* Ranges that run past the end of the file are clamped (RFC 9110 §14.1.2)
  rather than rejected, and suffix ranges (``bytes=-N``) are supported.
"""
from __future__ import annotations

import re
from email.utils import formatdate

# Bounded reply to an open-ended range: about a few seconds of phone video, small
# enough that the connection is released quickly for the next request.
OPEN_RANGE_CHUNK = 2 * 1024 * 1024
WRITE_CHUNK = 256 * 1024
_RANGE = re.compile(r"bytes=(\d*)-(\d*)")
# QuickTime files from phones share the MP4 container. Labelling them video/mp4
# lets Firefox and Chrome play them (both refuse "video/quicktime").
_PLAYABLE_MIME = {"video/quicktime": "video/mp4", "video/x-m4v": "video/mp4"}


def parse_range(header, size):
    """Return (start, end) inclusive, None for a full response, or "invalid" for 416."""
    header = (header or "").strip()
    if not header:
        return None
    if "," in header:  # multipart ranges are not needed for media; serve the full file
        return None
    match = _RANGE.fullmatch(header)
    if not match or size <= 0:
        return "invalid"
    first, last = match.groups()
    if not first:
        if not last or int(last) == 0:
            return "invalid"
        return max(0, size - int(last)), size - 1
    start = int(first)
    if start >= size:
        return "invalid"
    if last:
        end = int(last)
        if end < start:
            return "invalid"
        return start, min(end, size - 1)
    return start, min(size - 1, start + OPEN_RANGE_CHUNK - 1)


def send(handler, path, mime, cache_control):
    """Stream ``path`` honouring Range, If-Range and If-None-Match. Returns True."""
    stat = path.stat()
    size = stat.st_size
    etag = f'"{stat.st_mtime_ns:x}-{size:x}"'
    content_type = _PLAYABLE_MIME.get(mime, mime)
    common = {
        "Content-Type": content_type,
        "Accept-Ranges": "bytes",
        "Cache-Control": cache_control,
        "ETag": etag,
        "Last-Modified": formatdate(stat.st_mtime, usegmt=True),
        "X-Content-Type-Options": "nosniff",
    }
    if "no-store" not in cache_control and etag in [tag.strip() for tag in handler.headers.get("If-None-Match", "").split(",")]:
        handler.send_response(304)
        for name, value in common.items():
            if name != "Content-Type":
                handler.send_header(name, value)
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        return True
    if_range = handler.headers.get("If-Range")
    byte_range = parse_range(handler.headers.get("Range"), size) if not if_range or if_range.strip() == etag else None
    if byte_range == "invalid":
        handler.send_response(416)
        handler.send_header("Content-Range", f"bytes */{size}")
        handler.send_header("Content-Length", "0")
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        return True
    start, end = byte_range or (0, size - 1)
    handler.send_response(206 if byte_range else 200)
    for name, value in common.items():
        handler.send_header(name, value)
    handler.send_header("Content-Length", str(end - start + 1))
    if byte_range:
        handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
    handler.end_headers()
    if handler.command == "HEAD":
        return True
    try:
        with path.open("rb") as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = source.read(min(WRITE_CHUNK, remaining))
                if not chunk:
                    break
                handler.wfile.write(chunk)
                remaining -= len(chunk)
            if remaining:  # file shrank mid-stream; never leave a keep-alive socket out of sync
                handler.close_connection = True
    except (BrokenPipeError, ConnectionResetError):
        # The browser cancelled the request (seek, swipe, or tab closed). Normal.
        handler.close_connection = True
    return True
