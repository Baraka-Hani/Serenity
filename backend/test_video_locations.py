"""Video GPS metadata → Map pins, on an isolated temporary database: python3 backend/test_video_locations.py"""
import io
import json
import shutil
import struct
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import server
import trip_locations
import video_locations


def box(kind, payload=b""):
    kind = kind.encode("latin-1") if isinstance(kind, str) else kind
    return struct.pack(">I", 8 + len(payload)) + kind + payload


def movie(*udta_or_meta, faststart=False):
    """A minimal QuickTime/MP4 file whose moov holds the given location boxes."""
    moov = box("moov", box("mvhd", bytes(100)) + b"".join(udta_or_meta))
    head, media = box("ftyp", b"qt  \0\0\0\0qt  "), box("mdat", b"\x55" * 4096)
    return head + (moov + media if faststart else media + moov)


def xyz(text):  # Android / older cameras: ©xyz in udta
    data = text.encode()
    return box("udta", box(b"\xa9xyz", struct.pack(">HH", len(data), 0x15C7) + data))


def loci(lat, lng):  # 3GPP binary location box
    payload = bytes(4) + b"\x15\xc7" + b"\0" + b"\0" + struct.pack(">iii", round(lng * 65536), round(lat * 65536), 0)
    return box("udta", box("loci", payload))


def apple(text):  # iPhone: QuickTime metadata keys
    key = video_locations.APPLE_KEY.encode()
    keys = box("keys", bytes(4) + struct.pack(">I", 1) + struct.pack(">I", 8 + len(key)) + b"mdta" + key)
    items = box("ilst", box(struct.pack(">I", 1), box("data", struct.pack(">II", 1, 0) + text.encode())))
    return box("meta", box("hdlr", bytes(8) + b"mdta" + bytes(12)) + keys + items)


class VideoLocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.which = shutil.which
        video_locations.shutil.which = lambda *_: None  # prove the pure-Python reader works without ffprobe

    @classmethod
    def tearDownClass(cls):
        video_locations.shutil.which = cls.which

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_iso6709_forms(self):
        parse = video_locations.parse_iso6709
        self.assertEqual(parse("+35.0116+135.7681+045.000/"), (35.0116, 135.7681))
        self.assertEqual(parse("-33.8568+151.2153/"), (-33.8568, 151.2153))
        lat, lng = parse("+3500.696+13546.086/")  # degrees and minutes
        self.assertAlmostEqual(lat, 35.0116, 4); self.assertAlmostEqual(lng, 135.7681, 4)
        self.assertAlmostEqual(parse("+350041.76+1354605.16/")[0], 35.0116, 4)  # degrees, minutes, seconds
        for bad in ("+00.0000+000.0000/", "+95.0+010.0/", "+10.0+190.0/", "Kyoto", "", None):
            self.assertIsNone(parse(bad), bad)

    def test_reads_every_phone_format_without_ffprobe(self):
        cases = {
            "iphone.mov": (movie(apple("+38.7223-009.1393+012.000/")), (38.7223, -9.1393)),
            "android.mp4": (movie(xyz("+48.8584+002.2945/")), (48.8584, 2.2945)),
            "camera.mp4": (movie(loci(-33.8568, 151.2153), faststart=True), (-33.8568, 151.2153)),
        }
        for name, (data, expected) in cases.items():
            point = video_locations.read_location(self.write(name, data))
            self.assertAlmostEqual(point[0], expected[0], 4, name); self.assertAlmostEqual(point[1], expected[1], 4, name)
        self.assertIsNone(video_locations.read_location(self.write("plain.mp4", movie())))
        self.assertIsNone(video_locations.read_location(self.write("broken.mp4", b"\0\0\0\x09moov")))
        self.assertIsNone(video_locations.read_location(self.dir / "missing.mp4"))

    def test_central_point_ignores_a_stray_clip(self):
        kyoto = [(35.0116, 135.7681), (35.0120, 135.7690), (35.0100, 135.7670)]
        point, spread = video_locations.central_point(kyoto + [(51.5, -0.12)])
        self.assertIn(point, kyoto)
        self.assertGreater(spread, 9000)

    def test_dry_run_then_apply_places_published_trips_on_map(self):
        original = server.DATA, server.UPLOADS, server.DB
        try:
            server.DATA = self.dir / "data"; server.UPLOADS = server.DATA / "uploads"; server.DB = server.DATA / "test.sqlite3"
            server.init()
            now = int(time.time())
            with server.db() as connection:
                def user(name):
                    return connection.execute("""INSERT INTO users(email,name,salt,password_hash,created_at,public_id,username,bio)
                        VALUES (?,?,?,?,?,?,?,?)""", (f"{name}@example.test", name, b"s", "h", now, name[:1] * 16, name, "")).lastrowid
                def trip(owner, name):
                    return connection.execute("INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)", (owner, name, now)).lastrowid
                def clip(owner, feed, clip_id, data, public=True):
                    (server.UPLOADS / clip_id).write_bytes(data)
                    connection.execute("INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)",
                                       (clip_id, owner, clip_id + ".mov", "video/quicktime", len(data), now, feed))
                    connection.execute("INSERT INTO posts(id,user_id,clip_id,destination,caption,tip,created_at,is_public) VALUES (?,?,?,?,?,?,?,?)",
                                       (clip_id.ljust(32, "0"), owner, clip_id, "Somewhere", "A caption", "", now, int(public)))
                maya, noor = user("maya"), user("noor")
                kyoto, lisbon, alps, plain = trip(maya, "Kyoto"), trip(maya, "Lisbon"), trip(noor, "Alps"), trip(noor, "No GPS")
                clip(maya, kyoto, "a1", movie(apple("+35.011634+135.768123/")))
                clip(maya, kyoto, "a2", movie(xyz("+35.0120+135.7690/")))
                clip(maya, kyoto, "a3", movie(loci(51.5, -0.12)))  # stray clip, filmed far away
                clip(maya, lisbon, "b1", movie(apple("+38.7223-009.1393/")))
                clip(noor, alps, "c1", movie(apple("+45.9763+007.6586/")))
                clip(noor, plain, "d1", movie())
                trip_locations.save(connection, maya, lisbon, trip_locations.normalize(
                    {"lat": 38.7, "lng": -9.14, "label": "Lisbon, Portugal", "provider": "photon", "source": "place", "place_id": "x"}))
            out = io.StringIO()
            with redirect_stdout(out):
                video_locations.main([])
            dry = json.loads(out.getvalue())
            by_trip = {entry["trip"]: entry for entry in dry["proposals"]}
            self.assertEqual(dry["pins_proposed"], 2)
            self.assertEqual((by_trip["Kyoto"]["lat"], by_trip["Kyoto"]["lng"]), (35.01, 135.77), "Coordinates must be rounded to about 1 km")
            self.assertIn("warning", by_trip["Kyoto"], "Trips spanning far-apart places must be flagged")
            self.assertTrue(by_trip["Lisbon"]["action"].startswith("keep"), "Creator-chosen pins must be kept by default")
            self.assertTrue(by_trip["No GPS"]["action"].startswith("skip"))
            with server.db() as connection:
                self.assertIsNone(trip_locations.location(connection, kyoto), "A dry run must not write anything")

            with redirect_stdout(io.StringIO()):
                video_locations.main(["--apply"])
            with server.db() as connection:
                pinned = trip_locations.location(connection, kyoto)
                self.assertEqual((pinned["lat"], pinned["lng"], pinned["source"]), (35.01, 135.77, "video"))
                self.assertEqual(pinned["label"], "Filmed near 35.01°N, 135.77°E")
                self.assertEqual(trip_locations.location(connection, lisbon)["label"], "Lisbon, Portugal")
                listed = {trip["name"]: trip for trip in trip_locations.public_trips(connection, {})["trips"]}
                self.assertEqual(listed["Alps"]["source"], "video")
                self.assertEqual(set(listed), {"Kyoto", "Lisbon", "Alps"})
                # Clients may resend an unchanged video pin but cannot forge or move one.
                trip_locations.save(connection, maya, kyoto, trip_locations.normalize({**pinned, "label": "Kyoto, Japan"}))
                self.assertEqual(trip_locations.location(connection, kyoto)["source"], "video")
                trip_locations.save(connection, maya, kyoto, trip_locations.normalize({**pinned, "lat": 35.02}))
                self.assertEqual(trip_locations.location(connection, kyoto)["source"], "pin")
                trip_locations.save(connection, noor, plain, trip_locations.normalize({**pinned}))
                self.assertEqual(trip_locations.location(connection, plain)["source"], "pin")
            self.assertTrue(list(server.DATA.glob("before-video-locations-*.sqlite3")), "--apply must back up the database first")
        finally:
            server.DATA, server.UPLOADS, server.DB = original


if __name__ == "__main__":
    unittest.main()
