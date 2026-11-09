"""Owner-only, atomic visibility changes; private posts retain their interactions."""
import json
import re
import secrets
import time


def update(handler, db, feed_id):
    user = handler.require_user()
    if not user:
        return
    try:
        data = json.loads(handler.body(32 * 1024))
        if not isinstance(data, dict) or data.get('visibility') not in ('public', 'private'):
            raise ValueError('Choose public or private visibility.')
        selected = data.get('clip_ids')
        if selected is not None and (not isinstance(selected, list) or not 1 <= len(selected) <= 500
                or any(not isinstance(clip, str) or not re.fullmatch(r'[0-9a-f]{32}', clip) for clip in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError('Choose 1 to 500 unique videos from this trip.')
        public = data['visibility'] == 'public'
        with db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            trip = connection.execute('SELECT name FROM user_feeds WHERE id=? AND user_id=?', (feed_id, user['id'])).fetchone()
            if not trip:
                return handler.respond(404, {'error': 'Trip not found.'})
            clips = connection.execute('SELECT id FROM clips WHERE feed_id=? AND user_id=? ORDER BY created_at,rowid', (feed_id, user['id'])).fetchall()
            owned = {clip['id'] for clip in clips}
            if selected is not None and not set(selected).issubset(owned):
                return handler.respond(404, {'error': 'A selected video is not in this trip.'})
            ids = selected if selected is not None else [clip['id'] for clip in clips]
            if not ids:
                return handler.respond(409, {'error': 'Add videos to this trip before posting.'})
            details = connection.execute('SELECT destination,summary FROM feed_details WHERE user_id=? AND feed_id=?', (user['id'], feed_id)).fetchone()
            destination = (details['destination'] if details else '').strip() or 'Location not specified'
            caption = (details['summary'] if details else '').strip() or trip['name']
            tip = ''
            changed = 0
            for clip_id in ids:
                post = connection.execute('SELECT id,is_public FROM posts WHERE clip_id=? AND user_id=?', (clip_id, user['id'])).fetchone()
                if public and not post:
                    connection.execute('INSERT INTO posts(id,user_id,clip_id,destination,caption,tip,created_at,is_public) VALUES (?,?,?,?,?,?,?,1)',
                                       (secrets.token_hex(16), user['id'], clip_id, destination, caption, tip, int(time.time())))
                    changed += 1
                elif post and bool(post['is_public']) != public:
                    connection.execute('UPDATE posts SET is_public=? WHERE id=? AND user_id=?', (int(public), post['id'], user['id']))
                    changed += 1
            published = connection.execute('SELECT COUNT(*) FROM posts p JOIN clips c ON c.id=p.clip_id WHERE c.feed_id=? AND c.user_id=? AND p.is_public=1', (feed_id, user['id'])).fetchone()[0]
            result = {'feed_id': feed_id, 'visibility': 'public' if published == len(clips) else 'private' if not published else 'mixed',
                      'published': published, 'private': len(clips) - published, 'total': len(clips), 'changed': changed}
        return handler.respond(200, result)
    except ValueError as error:
        return handler.respond(400, {'error': str(error)})
