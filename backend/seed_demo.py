"""Explicit, rerunnable LOCAL demo setup. Never changes originals or existing real accounts.

python3 backend/seed_demo.py --source-root '/path/to/Photos Library.photoslibrary/originals'
Add --apply to create six labeled demo accounts, posts, and example conversations.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

import server

MANIFEST = Path(__file__).with_name('demo_videos.json')
ACCOUNTS = [
    ('demo_maya', 'Maya · Demo', 'Coastal journeys and days on the water.'),
    ('demo_jules', 'Jules · Demo', 'Dunes, old streets, and slower detours.'),
    ('demo_rio', 'Rio · Demo', 'Travel after dark, through a different lens.'),
    ('demo_avery', 'Avery · Demo', 'Wildlife, wide-open landscapes, and road journeys.'),
    ('demo_noor', 'Noor · Demo', 'Green hills and scenic viewpoints.'),
    ('demo_kai', 'Kai · Demo', 'Quiet water, shoreline walks, and little escapes.'),
]
# These are visual collections, not verified geographical trips. No GPS is read or published.
GROUPS = [
    ('wildlife-park', 'demo_avery', 'Wildlife encounters', 'Wildlife setting · destination unconfirmed', list(range(1, 8))),
    ('shore', 'demo_maya', 'Ocean-side moments', 'Coast · destination unconfirmed', [8, 9]),
    ('dunes', 'demo_jules', 'Dunes and sea views', 'Dunes and coast · destination unconfirmed', list(range(10, 14))),
    ('after-dark', 'demo_rio', 'After dark', 'Night-time travel · destination unconfirmed', list(range(14, 18))),
    ('sailing', 'demo_maya', 'Out on the water', 'Sailing and waterfront · destination unconfirmed', list(range(18, 31)) + [37, 38]),
    ('old-streets', 'demo_jules', 'Streets worth wandering', 'Old-town streets · destination unconfirmed', list(range(31, 37))),
    ('road', 'demo_avery', 'Through the window', 'Road journey · destination unconfirmed', list(range(39, 44))),
    ('open-landscapes', 'demo_avery', 'Open landscapes', 'Wildlife landscapes · destination unconfirmed', list(range(44, 54))),
    ('hills', 'demo_noor', 'A greener perspective', 'Hills and viewpoints · destination unconfirmed', list(range(54, 68))),
    ('waterside', 'demo_kai', 'By the water', 'Waterside walks · destination unconfirmed', list(range(68, 75))),
]


def init(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS demo_seed_accounts (
      username TEXT PRIMARY KEY, user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS demo_seed_feeds (
      seed_key TEXT PRIMARY KEY, feed_id INTEGER NOT NULL UNIQUE REFERENCES user_feeds(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS demo_seed_clips (
      source_id TEXT PRIMARY KEY, clip_id TEXT NOT NULL UNIQUE REFERENCES clips(id) ON DELETE CASCADE
    );
    """)


def sources(source_root):
    manifest = json.loads(MANIFEST.read_text())
    ids = manifest['video_ids']
    if len(set(ids)) != len(ids) or sorted(index for group in GROUPS for index in group[4]) != list(range(1, len(ids)+1)):
        raise ValueError('Demo manifest contains duplicate or unassigned videos.')
    root = Path(source_root).resolve(strict=True)
    result = [(index+1, key, root / key[0] / (key+'.mov')) for index, key in enumerate(ids)]
    missing = [str(path) for _, _, path in result if not path.is_file()]
    if missing:
        raise ValueError('Missing attached files: ' + ', '.join(missing))
    return result


def ensure_accounts(connection, password):
    users = {}
    for username, name, description in ACCOUNTS:
        existing = connection.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE OR email=?', (username, username+'@demo.serenity.test')).fetchall()
        receipt = connection.execute('SELECT user_id FROM demo_seed_accounts WHERE username=?', (username,)).fetchone()
        if existing:
            if len(existing) != 1 or not receipt or existing[0]['id'] != receipt['user_id'] or not existing[0]['is_demo']:
                raise ValueError(f'{username} conflicts with an existing account. No real accounts will be changed.')
            users[username] = existing[0]['id']
            continue
        salt = secrets.token_bytes(16)
        cursor = connection.execute('''INSERT INTO users(email,name,salt,password_hash,created_at,public_id,username,bio,is_demo)
            VALUES (?,?,?,?,?,?,?,?,1)''', (username+'@demo.serenity.test', name, salt, server.hash_password(password, salt),
            int(time.time()), secrets.token_hex(8), username, description+' Test account; all sample videos were supplied by the app owner.'))
        connection.execute('INSERT INTO demo_seed_accounts VALUES (?,?)', (username, cursor.lastrowid))
        users[username] = cursor.lastrowid
    return users


def seed_conversations(connection, users):
    samples = [
        ('demo_jules', 'demo_maya', 'sailing', 'Demo question: how would I find the place in this sailing video?',
         'Demo reply: this is a test post from the owner’s video collection. The exact destination is not confirmed; ask for a public destination pin before planning a visit.'),
        ('demo_noor', 'demo_avery', 'open-landscapes', 'Demo question: what should I check before visiting a wildlife location?',
         'Demo reply: confirm the location, current access rules, and a responsible local guide. This sample account cannot confirm details about the video.'),
        ('demo_kai', 'demo_jules', 'old-streets', 'Demo question: can you share more about this street-walk video?',
         'Demo reply: open the attached trip to see the other clips. This is a sample conversation for testing Chat, not verified travel advice.'),
    ]
    for index, (sender, recipient, group, question, reply) in enumerate(samples):
        low, high = sorted((users[sender], users[recipient]))
        row = connection.execute('SELECT id FROM dm_threads WHERE user_low=? AND user_high=?', (low, high)).fetchone()
        thread_id = row['id'] if row else secrets.token_hex(16)
        if not row:
            connection.execute('INSERT INTO dm_threads(id,user_low,user_high) VALUES (?,?,?)', (thread_id, low, high))
        post = connection.execute('''SELECT p.id FROM demo_seed_feeds f JOIN clips c ON c.feed_id=f.feed_id
            JOIN posts p ON p.clip_id=c.id WHERE f.seed_key=? AND p.is_public=1 ORDER BY p.created_at LIMIT 1''', (group,)).fetchone()
        for turn, (username, body) in enumerate(((sender, question), (recipient, reply))):
            key = f'serenity-demo-chat-v1-{index}-{turn}'
            if connection.execute('SELECT 1 FROM dm_messages WHERE sender_id=? AND client_key=?', (users[username], key)).fetchone():
                continue
            result = connection.execute('''INSERT INTO dm_messages(thread_id,sender_id,body,client_key,post_id,has_context,created_at)
                VALUES (?,?,?,?,?,?,?)''', (thread_id, users[username], body, key, post['id'] if post and not turn else None,
                bool(post and not turn), int(time.time())-600+index*60+turn*20))
            connection.execute('UPDATE dm_threads SET last_message_id=? WHERE id=?', (result.lastrowid, thread_id))


def apply(source_root, converter='/usr/bin/avconvert'):
    if server.PUBLIC_ORIGIN or server.HOST not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Demo setup is local-only. Do not seed shared or publicly hosted servers.')
    inputs = sources(source_root)
    server.init()
    # A restorable SQLite snapshot includes existing real-user data and is never served by HTTP.
    backup = server.DATA / f'before-demo-{int(time.time())}-{secrets.token_hex(3)}.sqlite3'
    import sqlite3
    with server.db() as current, sqlite3.connect(backup) as target:
        current.backup(target)
    os.chmod(backup, 0o600)
    access_file = server.DATA / 'demo-access.json'
    access = json.loads(access_file.read_text()) if access_file.exists() else {'password': secrets.token_urlsafe(9), 'accounts': []}
    password = access['password']
    with server.db() as connection:
        init(connection)
        # Complete all collision checks in one transaction before creating demo accounts.
        users = ensure_accounts(connection, password)
        existing = {row['source_id']: row['clip_id'] for row in connection.execute('SELECT * FROM demo_seed_clips')}
        for key, username, name, destination, _ in GROUPS:
            receipt = connection.execute('SELECT feed_id FROM demo_seed_feeds WHERE seed_key=?', (key,)).fetchone()
            if not receipt:
                result = connection.execute('INSERT INTO user_feeds(user_id,name,created_at) VALUES (?,?,?)', (users[username], name+' · Demo', int(time.time())))
                connection.execute('INSERT INTO demo_seed_feeds VALUES (?,?)', (key, result.lastrowid))
    access['accounts'] = [{'username': username, 'email': username+'@demo.serenity.test'} for username, _, _ in ACCOUNTS]
    access['note'] = 'Local test accounts only. These share the generated test password. Do not use for real data or expose them on a public server.'
    # Write credentials privately and atomically, never in frontend assets or console logs.
    with tempfile.NamedTemporaryFile(mode='w', dir=server.DATA, prefix='.demo-access-', delete=False) as output:
        os.chmod(output.name, 0o600)
        json.dump(access, output, indent=2)
        temporary_access = Path(output.name)
    temporary_access.replace(access_file)
    metadata = {index: group for group in GROUPS for index in group[4]}
    pending = [item for item in inputs if item[1] not in existing or not (server.UPLOADS / existing[item[1]]).is_file()]
    added = 0
    with tempfile.TemporaryDirectory(prefix='demo-media-', dir=server.DATA) as folder:
        def convert(item):
            index, source_id, source = item
            output = Path(folder) / (source_id+'.mp4')
            result = subprocess.run([converter, '--source', str(source), '--preset', 'Preset1280x720', '--output', str(output), '--duration', '20'],
                                    capture_output=True, text=True, timeout=180)
            if result.returncode or not output.is_file() or not 1 <= output.stat().st_size <= server.MAX_VIDEO:
                raise ValueError(f'Could not prepare demo clip {index}: {result.stderr[-600:]}')
            return item, output
        with ThreadPoolExecutor(max_workers=2) as pool:
            for (index, source_id, _), output in pool.map(convert, pending):
                key, username, title, destination, _ = metadata[index]
                clip_id = existing.get(source_id) or secrets.token_hex(16)
                target = server.UPLOADS / clip_id
                output.replace(target); os.chmod(target, 0o600)
                created = int(time.time())-3600+index*5
                with server.db() as connection:
                    feed_id = connection.execute('SELECT feed_id FROM demo_seed_feeds WHERE seed_key=?', (key,)).fetchone()['feed_id']
                    if source_id not in existing:
                        connection.execute('INSERT INTO clips(id,user_id,original_name,mime,size,created_at,feed_id) VALUES (?,?,?,?,?,?,?)',
                            (clip_id, users[username], f'{title} {index:02d} · Demo.mp4', 'video/mp4', target.stat().st_size, created, feed_id))
                        connection.execute('INSERT INTO demo_seed_clips VALUES (?,?)', (source_id, clip_id))
                        connection.execute('INSERT INTO posts(id,user_id,clip_id,destination,caption,tip,created_at,is_public) VALUES (?,?,?,?,?,?,?,1)',
                            (secrets.token_hex(16), users[username], clip_id, destination,
                             f'{title}. Sample post using an owner-provided video; exact place unconfirmed. Use Ask creator to try a private, video-linked question.', '', created))
                    else:
                        connection.execute('UPDATE clips SET size=?,mime=? WHERE id=? AND user_id=?', (target.stat().st_size, 'video/mp4', clip_id, users[username]))
                added += 1
                print(f'Prepared demo video {added}/{len(pending)} (source {index:02d})', flush=True)
    with server.db() as connection:
        seed_conversations(connection, users)
        count = connection.execute('SELECT COUNT(*) FROM demo_seed_clips').fetchone()[0]
    return {'accounts': len(users), 'trips': len(GROUPS), 'videos': count, 'new_videos': added, 'credentials_file': str(access_file), 'backup': str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--apply', action='store_true', help='Create demo data explicitly; default only checks inputs.')
    args = parser.parse_args()
    try:
        if args.apply:
            print(json.dumps(apply(args.source_root), indent=2))
        else:
            files = sources(args.source_root)
            print(json.dumps({'attached_videos': len(files), 'original_bytes': sum(path.stat().st_size for _, _, path in files),
                              'converter_available': Path('/usr/bin/avconvert').is_file(), 'changes': 'none; add --apply to seed local demo accounts'}, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))


if __name__ == '__main__':
    main()
