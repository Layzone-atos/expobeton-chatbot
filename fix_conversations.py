#!/usr/bin/env python3
"""Fix conversations.php to count messages dynamically instead of using stored message_count"""

with open('chatbot-admin/conversations.php', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace the query to count messages dynamically
old_q = 'SELECT s.* FROM sessions s'
new_q = 'SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) AS real_message_count FROM sessions s'
if old_q in content:
    content = content.replace(old_q, new_q, 1)
    print('Fix 1 OK: Query updated to count messages dynamically')
else:
    print('Fix 1 SKIP: Already updated or not found')

# Fix 2: Use real_message_count in the display
old_d = "<?= $s['message_count'] ?>"
new_d = "<?= $s['real_message_count'] ?: $s['message_count'] ?>"
if old_d in content:
    content = content.replace(old_d, new_d, 1)
    print('Fix 2 OK: Display uses real_message_count')
else:
    print('Fix 2 SKIP: Already updated or not found')

with open('chatbot-admin/conversations.php', 'w', encoding='utf-8') as f:
    f.write(content)
print('File saved!')
