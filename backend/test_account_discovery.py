"""Discovery and demo setup regression tests; no real accounts or attached media are changed."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request
import test_server as fixtures
import test_messaging as message_fixtures
import seed_demo
import server


class DiscoveryFlow(unittest.TestCase):
    setUpClass = classmethod(fixtures.BackendFlow.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.BackendFlow.tearDownClass.__func__)
    setUp = fixtures.BackendFlow.setUp
    call = fixtures.BackendFlow.call
    account = message_fixtures.MessagingFlow.account
    send = message_fixtures.MessagingFlow.send

    def publish(self, client, destination):
        feed = next(iter(self.call('/api/feeds', client=client)[1]['feeds']))
        _, clip = self.call('/api/clips', 'POST', b'fixture', 'video/mp4', {'X-Feed': feed, 'X-Filename': 'trip.mp4'}, client=client)
        _, post = self.call('/api/posts', 'POST', {'clip_id': clip['clip']['id'], 'destination': destination, 'caption': 'A public perspective'}, client=client)
        return feed, post['post']['id']

    def test_search_names_usernames_and_only_public_destinations(self):
        viewer, v = self.account('Explorer Directory')
        creator, c = self.account('Camila Coast')
        self.assertEqual(self.call('/api/accounts?q=Camila', client=urllib.request.build_opener())[0], 401)
        found = self.call('/api/accounts?q=Camila', client=viewer)[1]['accounts']
        self.assertEqual(found[0]['public_id'], c['public_id'])
        self.assertNotIn('email', found[0])
        self.assertNotIn('id', found[0])
        self.assertNotIn(c['public_id'], [row['public_id'] for row in self.call('/api/accounts', client=viewer)[1]['accounts']])
        self.assertEqual(self.call('/api/accounts?q=Lisbon', client=viewer)[1]['accounts'], [])
        feed, _ = self.publish(creator, 'Lisbon')
        self.assertEqual(self.call('/api/accounts?q=Lisbon', client=viewer)[1]['accounts'][0]['public_id'], c['public_id'])
        self.assertEqual(self.call('/api/accounts?q=@camila_coast', client=viewer)[1]['accounts'][0]['username'], c['username'])
        self.call(f'/api/feeds/{feed}/visibility', 'PUT', {'visibility': 'private'}, client=creator)
        self.assertEqual(self.call('/api/accounts?q=Lisbon', client=viewer)[1]['accounts'], [])
        self.assertIsNone(self.call('/api/accounts?q=Camila', client=viewer)[1]['accounts'][0]['preview_post_id'])
        self.assertEqual(self.call('/api/accounts?q=%25%25', client=viewer)[1]['accounts'], [])
        self.assertEqual(self.call('/api/accounts?q=a', client=viewer)[0], 400)
        self.assertEqual(self.call('/api/accounts?offset=-1', client=viewer)[0], 400)
        _, sent = self.send(viewer, c)
        self.call(f"/api/messages/{sent['thread']['id']}/block", 'POST', {'blocked': True}, client=viewer)
        self.assertEqual(self.call('/api/accounts?q=Camila', client=viewer)[1]['accounts'], [])

    def test_paginated_accounts_and_exact_username_ranking(self):
        viewer, _ = self.account('Paging Viewer')
        for index in range(14):
            self.account(f'Seed Directory {index}')
        first = self.call('/api/accounts?q=Seed%20Directory', client=viewer)[1]
        self.assertEqual(len(first['accounts']), 12)
        self.assertTrue(first['has_more'])
        second = self.call('/api/accounts?q=Seed%20Directory&offset=12', client=viewer)[1]
        self.assertEqual(len(second['accounts']), 2)
        self.assertFalse(second['has_more'])
        self.assertFalse(set(row['public_id'] for row in first['accounts']) & set(row['public_id'] for row in second['accounts']))
        exact = self.call('/api/accounts?q=seed_directory_1', client=viewer)[1]['accounts']
        self.assertEqual(exact[0]['username'], 'seed_directory_1')

    def test_demo_seed_is_local_labeled_and_rerunnable(self):
        source = server.DATA / 'fixture-originals'
        source.mkdir()
        keys = __import__('json').loads(seed_demo.MANIFEST.read_text())['video_ids']
        for key in keys:
            folder = source / key[0]; folder.mkdir(exist_ok=True)
            (folder / (key+'.mov')).write_bytes(b'original-fixture')
        converted = []
        def fake_convert(command, **kwargs):
            converted.append(command)
            Path(command[command.index('--output')+1]).write_bytes(b'fixture-mp4')
            return SimpleNamespace(returncode=0, stderr='')
        with patch('seed_demo.subprocess.run', side_effect=fake_convert):
            result = seed_demo.apply(source)
            again = seed_demo.apply(source)
        self.assertEqual(result['videos'], 74)
        self.assertEqual(result['accounts'], 6)
        self.assertEqual(result['trips'], 10)
        self.assertEqual(again['new_videos'], 0)
        self.assertEqual(len(converted), 74)
        self.assertTrue(all('--disableMetadataFilter' not in command for command in converted))
        self.assertEqual((source / keys[0][0] / (keys[0]+'.mov')).read_bytes(), b'original-fixture')
        self.assertEqual(Path(result['credentials_file']).stat().st_mode & 0o777, 0o600)
        self.assertTrue(Path(result['backup']).is_file())
        with server.db() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users WHERE is_demo=1').fetchone()[0], 6)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM dm_messages WHERE client_key LIKE ?', ('serenity-demo-chat-v1-%',)).fetchone()[0], 6)
        profile = self.call('/api/profiles/demo_maya')[1]['profile']
        self.assertTrue(profile['is_demo'])
        self.assertEqual(profile['trip_count'], 2)
        self.assertEqual(profile['video_count'], 17)
        with patch.object(server, 'PUBLIC_ORIGIN', 'https://example.test'):
            with self.assertRaisesRegex(ValueError, 'local-only'):
                seed_demo.apply(source)

    def test_chat_entry_points_and_directory_assets(self):
        for path in ('/account-discovery.js', '/account-discovery.css', '/search.html'):
            self.assertEqual(self.call(path)[0], 200)
        self.assertIn(b'id="accountDirectory"', self.call('/search.html')[1])
        self.assertIn(b'id="messageProfile"', self.call('/profile.html')[1])
        self.assertIn(b'messageUrl(post.author_public_id, nextPost.id)', self.call('/social-feed.js')[1])
        hub = self.call('/feed-hub.js')[1]
        self.assertIn(b'messageUrl(context.creator.public_id, context.post_id)', hub)
        self.assertIn(b'postContext(id)', hub)


if __name__ == '__main__':
    unittest.main()
