<?php
/**
 * Bulk / single conversation transcript exporter.
 *
 * Accepted parameters (GET or POST):
 *   - format : 'csv' | 'json' | 'pdf'   (required)
 *   - ids[]  : array of session_id strings (preferred)
 *   - ids    : comma-separated string (fallback)
 *   - id     : single session_id (alternative shortcut)
 *
 * The output bundles every available datapoint per session:
 *   - session metadata (device, browser, IP, country, city, screen, ...)
 *   - registration record (if any)
 *   - full message timeline (user + bot)
 *   - all admin email replies
 *
 * PDF format produces a print-friendly HTML document that auto-triggers the
 * browser print dialog ("Save as PDF") so we don't depend on any external PHP
 * library (compatible with the PHP 7.0.33 production host).
 */

require_once __DIR__ . '/auth.php';
requireLogin();

$db = getDB();

// ------------------------------------------------------------------
// Inputs
// ------------------------------------------------------------------
$format = strtolower(trim($_REQUEST['format'] ?? 'csv'));
if (!in_array($format, ['csv', 'json', 'pdf'], true)) {
    http_response_code(400);
    echo "Invalid format. Use csv, json or pdf.";
    exit;
}

$sessionIds = [];
if (!empty($_REQUEST['ids']) && is_array($_REQUEST['ids'])) {
    $sessionIds = $_REQUEST['ids'];
} elseif (!empty($_REQUEST['ids']) && is_string($_REQUEST['ids'])) {
    $sessionIds = array_filter(array_map('trim', explode(',', $_REQUEST['ids'])));
} elseif (!empty($_REQUEST['id'])) {
    $sessionIds = [trim($_REQUEST['id'])];
}

$sessionIds = array_values(array_unique(array_filter($sessionIds, function ($v) {
    return is_string($v) && $v !== '';
})));

if (empty($sessionIds)) {
    http_response_code(400);
    echo "No conversation selected. Please pick at least one conversation.";
    exit;
}

// Cap to a sane number to avoid timeouts / oversized downloads.
if (count($sessionIds) > 500) {
    $sessionIds = array_slice($sessionIds, 0, 500);
}

// ------------------------------------------------------------------
// Fetch helper
// ------------------------------------------------------------------
function fetchConversationBundle(PDO $db, $sessionId) {
    $bundle = [
        'session'      => null,
        'registration' => null,
        'messages'     => [],
        'admin_replies'=> [],
    ];

    $s = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
    $s->execute([$sessionId]);
    $bundle['session'] = $s->fetch(PDO::FETCH_ASSOC) ?: null;
    if (!$bundle['session']) return null;

    $r = $db->prepare("SELECT * FROM registrations WHERE session_id = ? ORDER BY registered_at DESC LIMIT 1");
    $r->execute([$sessionId]);
    $bundle['registration'] = $r->fetch(PDO::FETCH_ASSOC) ?: null;

    $m = $db->prepare("SELECT id, sender, message_text, intent, confidence, timestamp
                       FROM messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC");
    $m->execute([$sessionId]);
    $bundle['messages'] = $m->fetchAll(PDO::FETCH_ASSOC);

    $a = $db->prepare("SELECT id, admin_username, recipient_email, recipient_name, subject,
                              message_text, sent_at, email_status, error_message
                       FROM admin_replies WHERE session_id = ? ORDER BY sent_at ASC");
    $a->execute([$sessionId]);
    $bundle['admin_replies'] = $a->fetchAll(PDO::FETCH_ASSOC);

    return $bundle;
}

// Resolve all bundles up-front (single transaction-friendly read pass).
$bundles = [];
foreach ($sessionIds as $sid) {
    $b = fetchConversationBundle($db, $sid);
    if ($b) $bundles[] = $b;
}

if (empty($bundles)) {
    http_response_code(404);
    echo "None of the selected sessions could be found.";
    exit;
}

$datestamp  = date('Y-m-d_His');
$baseName   = count($bundles) === 1
    ? 'conversation_' . preg_replace('/[^A-Za-z0-9_\-]/', '_', $bundles[0]['session']['session_id'])
    : 'conversations_bulk_' . count($bundles);
$exportName = $baseName . '_' . $datestamp;

// ------------------------------------------------------------------
// Output: CSV
// ------------------------------------------------------------------
if ($format === 'csv') {
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $exportName . '.csv"');
    $out = fopen('php://output', 'w');
    // BOM for Excel UTF-8
    fwrite($out, chr(0xEF) . chr(0xBB) . chr(0xBF));

    fputcsv($out, [
        'Session ID', 'Started At', 'Ended At', 'Duration (s)',
        'User Name', 'User Email', 'Phone (registration)', 'Company (registration)',
        'Reference #', 'Category',
        'Country', 'City', 'IP', 'Device', 'Browser', 'OS', 'Screen', 'Language',
        'Referrer', 'Status',
        'Message #', 'Sender', 'Timestamp', 'Intent', 'Confidence', 'Message Text',
    ]);

    foreach ($bundles as $b) {
        $s = $b['session'];
        $reg = $b['registration'];

        $status = !empty($s['is_unresolved']) && empty($s['resolved_at'])
            ? 'unresolved'
            : (!empty($s['resolved_at']) ? 'resolved' : 'ok');

        $screen = ($s['screen_width'] && $s['screen_height'])
            ? ($s['screen_width'] . 'x' . $s['screen_height']) : '';

        // Combined timeline: chat + admin emails
        $timeline = $b['messages'];
        foreach ($b['admin_replies'] as $ar) {
            $timeline[] = [
                'sender'       => 'admin',
                'message_text' => '[Email: ' . $ar['subject'] . "]\n\n" . $ar['message_text'],
                'intent'       => null,
                'confidence'   => null,
                'timestamp'    => $ar['sent_at'],
            ];
        }
        usort($timeline, function ($a, $b) {
            return strcmp((string)$a['timestamp'], (string)$b['timestamp']);
        });

        if (empty($timeline)) {
            // Still emit one row so the session shows up in the export.
            fputcsv($out, [
                $s['session_id'], $s['started_at'], $s['ended_at'], $s['duration_seconds'],
                $s['user_name'], $s['user_email'],
                $reg['phone'] ?? '', $reg['company'] ?? '',
                $reg['reference_number'] ?? '', $reg['category'] ?? '',
                $s['country'], $s['city'], $s['ip_address'],
                $s['device_type'], $s['browser'], $s['os'], $screen, $s['language'],
                $s['referrer_url'], $status,
                '', '', '', '', '', '(no messages)',
            ]);
            continue;
        }

        $i = 0;
        foreach ($timeline as $msg) {
            $i++;
            fputcsv($out, [
                $s['session_id'], $s['started_at'], $s['ended_at'], $s['duration_seconds'],
                $s['user_name'], $s['user_email'],
                $reg['phone'] ?? '', $reg['company'] ?? '',
                $reg['reference_number'] ?? '', $reg['category'] ?? '',
                $s['country'], $s['city'], $s['ip_address'],
                $s['device_type'], $s['browser'], $s['os'], $screen, $s['language'],
                $s['referrer_url'], $status,
                $i, $msg['sender'], $msg['timestamp'],
                $msg['intent'] ?? '',
                isset($msg['confidence']) && $msg['confidence'] !== null ? number_format((float)$msg['confidence'], 4) : '',
                $msg['message_text'],
            ]);
        }
    }
    fclose($out);
    exit;
}

// ------------------------------------------------------------------
// Output: JSON
// ------------------------------------------------------------------
if ($format === 'json') {
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $exportName . '.json"');

    $payload = [
        'exported_at'    => date('c'),
        'exported_by'    => $_SESSION['admin_user'] ?? null,
        'session_count'  => count($bundles),
        'app'            => APP_NAME,
        'conversations'  => array_map(function ($b) {
            $s = $b['session'];
            return [
                'session_id' => $s['session_id'],
                'session'    => $s,
                'registration' => $b['registration'],
                'messages'   => $b['messages'],
                'admin_replies' => $b['admin_replies'],
            ];
        }, $bundles),
    ];

    echo json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// ------------------------------------------------------------------
// Output: PDF (print-friendly HTML page that auto-prints)
// ------------------------------------------------------------------
// We deliberately serve HTML and let the browser produce the PDF via the
// native print dialog. This keeps the dashboard dependency-free on PHP 7.0.33.
header('Content-Type: text/html; charset=utf-8');

$adminUser = $_SESSION['admin_user'] ?? '';
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Conversation Export — <?= htmlspecialchars($exportName) ?></title>
<style>
    *, *::before, *::after { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
        font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        color: #1f2937;
        background: #f8f9fa;
        font-size: 12px;
        line-height: 1.5;
    }
    .page { max-width: 960px; margin: 0 auto; padding: 24px; }
    .doc-header {
        background: #0A2A66; color: #fff; padding: 18px 22px; border-radius: 8px;
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;
    }
    .doc-header h1 { font-size: 18px; margin: 0; }
    .doc-header small { opacity: 0.85; }
    .toolbar {
        position: sticky; top: 0; z-index: 10; background: #fff; border: 1px solid #e5e7eb;
        padding: 10px 14px; border-radius: 8px; margin-bottom: 14px;
        display: flex; gap: 10px; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,.06);
    }
    .toolbar button {
        background: #0A2A66; color: #fff; border: 0; padding: 8px 14px;
        border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
    }
    .toolbar a { color: #0A2A66; text-decoration: none; font-weight: 600; font-size: 12px; }

    .conv-card {
        background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
        padding: 18px 22px; margin-bottom: 22px; page-break-inside: avoid;
    }
    .conv-card + .conv-card { page-break-before: always; }
    .conv-title {
        font-size: 15px; font-weight: 700; color: #0A2A66;
        border-bottom: 2px solid #0A2A66; padding-bottom: 6px; margin: 0 0 12px;
    }
    .meta-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 4px 18px; margin-bottom: 14px;
    }
    .meta-grid div { font-size: 11.5px; }
    .meta-grid strong { color: #475569; font-weight: 600; min-width: 110px; display: inline-block; }
    .pill {
        display: inline-block; padding: 2px 8px; border-radius: 999px;
        font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .3px;
    }
    .pill-ok { background: #e7f5ee; color: #166534; }
    .pill-unresolved { background: #fef3c7; color: #92400e; }
    .pill-resolved { background: #dbeafe; color: #1e40af; }

    .reg-block {
        background: #f1f5f9; border-left: 3px solid #0A2A66;
        padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 11.5px;
    }
    .reg-block h3 { margin: 0 0 6px; font-size: 12px; color: #0A2A66; }

    .timeline { margin-top: 8px; }
    .msg-row { display: flex; margin: 8px 0; }
    .msg-row.user { justify-content: flex-end; }
    .bubble {
        max-width: 78%; padding: 8px 12px; border-radius: 10px; font-size: 11.5px;
        white-space: pre-wrap; word-wrap: break-word;
    }
    .bubble .who { font-size: 9.5px; font-weight: 700; text-transform: uppercase;
                   letter-spacing: .4px; margin-bottom: 3px; opacity: .85; }
    .bubble .ts { display: block; font-size: 9.5px; opacity: .7; margin-top: 4px; }
    .bubble .intent { display: inline-block; background: rgba(0,0,0,.08); padding: 1px 6px;
                      border-radius: 999px; font-size: 9.5px; margin-left: 6px; }

    .b-user  { background: #0A2A66; color: #fff; }
    .b-bot   { background: #f1f3f5; color: #1f2937; }
    .b-admin { background: #e8f5e9; color: #1b5e20; border: 1px solid #c8e6c9; }

    .no-msg { color: #6b7280; font-style: italic; padding: 8px 0; }

    @media print {
        body { background: #fff; }
        .toolbar { display: none; }
        .doc-header { background: #0A2A66 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        .conv-card { border-color: #d1d5db; box-shadow: none; }
        .b-user, .b-bot, .b-admin { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
</style>
</head>
<body>
<div class="page">
    <div class="toolbar">
        <button type="button" onclick="window.print()">🖨️ Save as PDF / Print</button>
        <span style="color:#6b7280;font-size:11px;">Use the browser dialog &rarr; choose <strong>Save as PDF</strong>.</span>
        <a href="conversations.php" style="margin-left:auto;">&larr; Back to conversations</a>
    </div>

    <div class="doc-header">
        <div>
            <h1>ExpoBeton RDC — Conversation Export</h1>
            <small>
                <?= count($bundles) ?> conversation<?= count($bundles) > 1 ? 's' : '' ?>
                · generated on <?= date('M j, Y H:i') ?>
                <?= $adminUser ? ' · by ' . htmlspecialchars($adminUser) : '' ?>
            </small>
        </div>
        <div style="font-size:11px;text-align:right;opacity:.9;">
            <div>Reference: <?= htmlspecialchars($exportName) ?></div>
        </div>
    </div>

<?php
foreach ($bundles as $b):
    $s = $b['session'];
    $reg = $b['registration'];

    $status = !empty($s['is_unresolved']) && empty($s['resolved_at'])
        ? 'unresolved'
        : (!empty($s['resolved_at']) ? 'resolved' : 'ok');
    $statusLabel = ['ok' => 'OK', 'unresolved' => 'Unresolved', 'resolved' => 'Replied / Resolved'][$status];

    // Merged timeline
    $timeline = $b['messages'];
    foreach ($b['admin_replies'] as $ar) {
        $timeline[] = [
            'sender'       => 'admin',
            'message_text' => '[Email: ' . $ar['subject'] . "]\n\n" . $ar['message_text'],
            'intent'       => null,
            'confidence'   => null,
            'timestamp'    => $ar['sent_at'],
        ];
    }
    usort($timeline, function ($a, $b) {
        return strcmp((string)$a['timestamp'], (string)$b['timestamp']);
    });

    $screen = ($s['screen_width'] && $s['screen_height'])
        ? ($s['screen_width'] . 'x' . $s['screen_height']) : '-';
?>
    <div class="conv-card">
        <h2 class="conv-title">
            <?= htmlspecialchars($s['user_name'] ?: ($s['user_email'] ?: 'Anonymous user')) ?>
            <span class="pill pill-<?= $status ?>" style="margin-left:8px;font-size:10px;"><?= $statusLabel ?></span>
        </h2>

        <div class="meta-grid">
            <div><strong>Session ID:</strong> <code style="font-size:10.5px;"><?= htmlspecialchars($s['session_id']) ?></code></div>
            <div><strong>Started:</strong> <?= htmlspecialchars($s['started_at'] ?: '-') ?></div>
            <div><strong>Ended:</strong> <?= htmlspecialchars($s['ended_at'] ?: '(active)') ?></div>
            <div><strong>Duration:</strong> <?= htmlspecialchars(formatDuration($s['duration_seconds'])) ?></div>
            <div><strong>User name:</strong> <?= htmlspecialchars($s['user_name'] ?: '-') ?></div>
            <div><strong>User email:</strong> <?= htmlspecialchars($s['user_email'] ?: '-') ?></div>
            <div><strong>Country:</strong> <?= htmlspecialchars($s['country'] ?: '-') ?></div>
            <div><strong>City:</strong> <?= htmlspecialchars($s['city'] ?: '-') ?></div>
            <div><strong>IP address:</strong> <?= htmlspecialchars($s['ip_address'] ?: '-') ?></div>
            <div><strong>Device:</strong> <?= htmlspecialchars($s['device_type'] ?: '-') ?></div>
            <div><strong>Browser:</strong> <?= htmlspecialchars($s['browser'] ?: '-') ?></div>
            <div><strong>OS:</strong> <?= htmlspecialchars($s['os'] ?: '-') ?></div>
            <div><strong>Screen:</strong> <?= htmlspecialchars($screen) ?></div>
            <div><strong>Language:</strong> <?= htmlspecialchars($s['language'] ?: '-') ?></div>
            <?php if (!empty($s['referrer_url'])): ?>
                <div style="grid-column: 1 / -1;"><strong>Referrer:</strong> <?= htmlspecialchars($s['referrer_url']) ?></div>
            <?php endif; ?>
        </div>

        <?php if ($reg): ?>
            <div class="reg-block">
                <h3>📋 Registration record</h3>
                <div class="meta-grid" style="margin-bottom:0;">
                    <div><strong>Reference #:</strong> <?= htmlspecialchars($reg['reference_number'] ?: '-') ?></div>
                    <div><strong>Category:</strong> <?= htmlspecialchars($reg['category'] ?: '-') ?></div>
                    <div><strong>Contact name:</strong> <?= htmlspecialchars($reg['contact_name'] ?: '-') ?></div>
                    <div><strong>Company:</strong> <?= htmlspecialchars($reg['company'] ?: '-') ?></div>
                    <div><strong>Email:</strong> <?= htmlspecialchars($reg['email'] ?: '-') ?></div>
                    <div><strong>Phone:</strong> <?= htmlspecialchars($reg['phone'] ?: '-') ?></div>
                    <div><strong>Country:</strong> <?= htmlspecialchars($reg['country'] ?: '-') ?></div>
                    <div><strong>Registered at:</strong> <?= htmlspecialchars($reg['registered_at'] ?: '-') ?></div>
                </div>
            </div>
        <?php endif; ?>

        <h3 style="font-size:12px;color:#0A2A66;margin:16px 0 4px;">
            💬 Conversation timeline (<?= count($timeline) ?> entries)
        </h3>
        <div class="timeline">
            <?php if (empty($timeline)): ?>
                <div class="no-msg">No messages recorded for this session.</div>
            <?php else: ?>
                <?php foreach ($timeline as $msg):
                    $sender = $msg['sender'];
                    $rowCls = $sender === 'user' ? 'msg-row user' : 'msg-row';
                    $bubCls = $sender === 'user' ? 'bubble b-user'
                            : ($sender === 'admin' ? 'bubble b-admin' : 'bubble b-bot');
                    $whoLabel = $sender === 'user' ? 'User'
                              : ($sender === 'admin' ? 'Admin (email)' : 'Bot');
                ?>
                    <div class="<?= $rowCls ?>">
                        <div class="<?= $bubCls ?>">
                            <div class="who">
                                <?= $whoLabel ?>
                                <?php if (!empty($msg['intent'])): ?>
                                    <span class="intent"><?= htmlspecialchars($msg['intent']) ?>
                                        <?= isset($msg['confidence']) && $msg['confidence'] !== null
                                                ? '· ' . round(((float)$msg['confidence']) * 100) . '%' : '' ?></span>
                                <?php endif; ?>
                            </div>
                            <div><?= nl2br(htmlspecialchars($msg['message_text'] ?? '')) ?></div>
                            <span class="ts"><?= htmlspecialchars($msg['timestamp'] ?: '') ?></span>
                        </div>
                    </div>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>
    </div>
<?php endforeach; ?>

</div>

<script>
    // Open the print dialog automatically so the user can simply pick
    // "Save as PDF" from the browser print menu.
    window.addEventListener('load', function () {
        setTimeout(function () { window.print(); }, 350);
    });
</script>
</body>
</html>
