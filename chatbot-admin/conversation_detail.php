<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

$sessionId = $_GET['id'] ?? '';
if (!$sessionId) { header('Location: conversations.php'); exit; }

// Get session info
$stmt = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
$stmt->execute([$sessionId]);
$session = $stmt->fetch();

if (!$session) { header('Location: conversations.php'); exit; }

// Get registration info (if user submitted the registration form)
$regStmt = $db->prepare("SELECT reference_number, category, company, contact_name, email, phone, country, registered_at
                        FROM registrations WHERE session_id = ? ORDER BY registered_at DESC LIMIT 1");
$regStmt->execute([$sessionId]);
$registration = $regStmt->fetch();

// ============================================================
// POST handler: admin email reply OR mark-resolved
// ============================================================
$flashMsg = null;
$flashType = 'success';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!canEditData()) {
        $flashMsg  = "You don't have permission to perform this action.";
        $flashType = 'danger';
    } else {
    $action = $_POST['action'] ?? '';

    if ($action === 'send_reply') {
        $to    = trim($_POST['to'] ?? '');
        $subj  = trim($_POST['subject'] ?? '');
        $body  = trim($_POST['body'] ?? '');

        if (!filter_var($to, FILTER_VALIDATE_EMAIL)) {
            $flashMsg = "Invalid recipient email address.";
            $flashType = 'danger';
        } elseif ($subj === '' || $body === '') {
            $flashMsg = "Subject and message are required.";
            $flashType = 'danger';
        } else {
            $sent = sendAdminReplyEmail($to, $subj, $body, $session['user_name'] ?? null);

            $ins = $db->prepare("INSERT INTO admin_replies
                (session_id, admin_username, recipient_email, recipient_name, subject, message_text, sent_at, email_status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, ?)");
            $ins->execute([
                $sessionId,
                $_SESSION['admin_user'] ?? null,
                $to,
                $session['user_name'] ?? null,
                $subj,
                $body,
                $sent['ok'] ? 'sent' : 'failed',
                $sent['ok'] ? null : ($sent['error'] ?? 'unknown')
            ]);

            if ($sent['ok']) {
                $db->prepare("UPDATE sessions SET resolved_at = NOW(), resolved_by = ? WHERE session_id = ?")
                   ->execute([$_SESSION['admin_user'] ?? 'admin', $sessionId]);
                $flashMsg = "Email sent to {$to} and conversation marked as resolved.";
            } else {
                $flashMsg = "Email failed to send: " . ($sent['error'] ?? 'unknown error') . ". The attempt has been logged.";
                $flashType = 'danger';
            }

            // Refresh session data
            $stmt = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
            $stmt->execute([$sessionId]);
            $session = $stmt->fetch();
        }
    } elseif ($action === 'send_reply_with_transcript') {
        $to    = trim($_POST['to'] ?? '');
        $subj  = trim($_POST['subject'] ?? '');
        $body  = trim($_POST['body'] ?? '');

        if (!filter_var($to, FILTER_VALIDATE_EMAIL)) {
            $flashMsg = "Invalid recipient email address.";
            $flashType = 'danger';
        } elseif ($subj === '' || $body === '') {
            $flashMsg = "Subject and message are required.";
            $flashType = 'danger';
        } else {
            // Fetch the chat transcript (bot + user messages, not admin email replies)
            $tStmt = $db->prepare("SELECT sender, message_text, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp ASC");
            $tStmt->execute([$sessionId]);
            $transcriptRows = $tStmt->fetchAll();

            $sent = sendAdminReplyEmail($to, $subj, $body, $session['user_name'] ?? null, $transcriptRows);

            $logged = $body;
            if (!empty($transcriptRows)) {
                $logged .= "\n\n[Transcript included: " . count($transcriptRows) . " messages]";
            }

            $ins = $db->prepare("INSERT INTO admin_replies
                (session_id, admin_username, recipient_email, recipient_name, subject, message_text, sent_at, email_status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, NOW(), ?, ?)");
            $ins->execute([
                $sessionId,
                $_SESSION['admin_user'] ?? null,
                $to,
                $session['user_name'] ?? null,
                $subj,
                $logged,
                $sent['ok'] ? 'sent' : 'failed',
                $sent['ok'] ? null : ($sent['error'] ?? 'unknown')
            ]);

            if ($sent['ok']) {
                $db->prepare("UPDATE sessions SET resolved_at = NOW(), resolved_by = ? WHERE session_id = ?")
                   ->execute([$_SESSION['admin_user'] ?? 'admin', $sessionId]);
                $flashMsg = "Email with conversation transcript sent to {$to} and conversation marked as resolved.";
            } else {
                $flashMsg = "Email failed to send: " . ($sent['error'] ?? 'unknown error') . ". The attempt has been logged.";
                $flashType = 'danger';
            }

            // Refresh session data
            $stmt = $db->prepare("SELECT * FROM sessions WHERE session_id = ?");
            $stmt->execute([$sessionId]);
            $session = $stmt->fetch();
        }
    } elseif ($action === 'mark_resolved') {
        $db->prepare("UPDATE sessions SET resolved_at = NOW(), resolved_by = ? WHERE session_id = ?")
           ->execute([$_SESSION['admin_user'] ?? 'admin', $sessionId]);
        $flashMsg = "Conversation marked as resolved.";
        $session['resolved_at'] = date('Y-m-d H:i:s');
        $session['resolved_by'] = $_SESSION['admin_user'] ?? 'admin';
    } elseif ($action === 'mark_unresolved') {
        $db->prepare("UPDATE sessions SET is_unresolved = 1, resolved_at = NULL, resolved_by = NULL WHERE session_id = ?")
           ->execute([$sessionId]);
        $flashMsg = "Conversation re-opened as unresolved.";
        $session['is_unresolved'] = 1;
        $session['resolved_at'] = null;
    }
    } // end canEditData
}

/**
 * Render a conversation transcript as plain-text and HTML.
 * Expects rows with keys: sender ('user'|'bot'|'admin'), message_text, timestamp.
 * Returns ['text' => string, 'html' => string].
 */
function renderTranscriptForEmail(array $transcript) {
    if (empty($transcript)) {
        return ['text' => '', 'html' => ''];
    }
    $textLines = [];
    $htmlRows  = [];
    foreach ($transcript as $row) {
        $sender = strtolower($row['sender'] ?? 'bot');
        $ts     = !empty($row['timestamp']) ? date('d/m/Y H:i', strtotime($row['timestamp'])) : '';
        $txt    = trim((string)($row['message_text'] ?? ''));
        if ($txt === '') continue;

        if ($sender === 'user') {
            $label = 'Vous';
            $bg    = '#0A2A66';
            $color = '#ffffff';
            $align = 'right';
        } elseif ($sender === 'admin') {
            $label = 'Equipe ExpoBeton RDC';
            $bg    = '#e8f5e9';
            $color = '#1b5e20';
            $align = 'left';
        } else {
            $label = 'Assistant ExpoBeton';
            $bg    = '#f1f3f5';
            $color = '#212529';
            $align = 'left';
        }

        // Plain-text line
        $textLines[] = '[' . $ts . '] ' . ($sender === 'user' ? 'Vous' : ($sender === 'admin' ? 'Admin' : 'Assistant')) . ' : ' . $txt;

        // HTML bubble
        $htmlRows[] = '<tr><td align="' . $align . '" style="padding:6px 0;">'
            . '<div style="display:inline-block;max-width:80%;padding:10px 14px;border-radius:10px;'
            . 'background:' . $bg . ';color:' . $color . ';font-family:Arial,sans-serif;font-size:13px;line-height:1.5;text-align:left;">'
            . '<div style="font-size:10px;opacity:.8;margin-bottom:4px;text-transform:uppercase;letter-spacing:.3px;">'
            . htmlspecialchars($label) . ($ts ? ' &middot; ' . htmlspecialchars($ts) : '')
            . '</div>'
            . '<div style="white-space:pre-wrap;">' . nl2br(htmlspecialchars($txt)) . '</div>'
            . '</div></td></tr>';
    }

    $plain = implode("\r\n", $textLines);
    $html  = '<table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;">'
           . implode('', $htmlRows)
           . '</table>';

    return ['text' => $plain, 'html' => $html];
}

/**
 * Send an admin reply email via PHP mail() using local cPanel MTA.
 * If $transcript is provided (array of messages), it is appended below the
 * admin's custom message, so the user can see the full conversation context.
 * Returns ['ok' => bool, 'error' => string|null].
 */
function sendAdminReplyEmail($to, $subject, $plainBody, $recipientName = null, array $transcript = []) {
    $fromAddr = defined('EMAIL_FROM_ADDRESS') ? EMAIL_FROM_ADDRESS : 'no-reply@expobetonrdc.com';
    $fromName = defined('EMAIL_FROM_NAME')    ? EMAIL_FROM_NAME    : 'ExpoBeton RDC';
    $replyTo  = defined('EMAIL_REPLY_TO')     ? EMAIL_REPLY_TO     : $fromAddr;
    $sigHtml  = defined('EMAIL_SIGNATURE_HTML') ? EMAIL_SIGNATURE_HTML : '';

    $greeting = $recipientName ? "Bonjour " . htmlspecialchars($recipientName) . "," : "Bonjour,";

    // Optional transcript block
    $rendered = renderTranscriptForEmail($transcript);
    $hasTranscript = $rendered['text'] !== '';

    $introHtml = $hasTranscript
        ? '<p style="font-family:Arial,sans-serif;font-size:14px;color:#444;margin:18px 0 6px;">'
        . 'Suite &agrave; votre conversation avec notre assistant ExpoBeton RDC, voici la r&eacute;ponse de notre &eacute;quipe :'
        . '</p>'
        : '';

    $transcriptHtml = $hasTranscript
        ? '<hr style="border:0;border-top:1px solid #e0e0e0;margin:24px 0 16px;">'
        . '<p style="font-family:Arial,sans-serif;font-size:13px;color:#666;margin:0 0 10px;">'
        . '<strong>Rappel de votre conversation</strong> (pour votre r&eacute;f&eacute;rence) :'
        . '</p>'
        . $rendered['html']
        : '';

    $bodyHtml = '<div style="max-width:680px;margin:0 auto;font-family:Arial,sans-serif;color:#222;">'
              . '<p style="font-size:14px;">' . $greeting . '</p>'
              . $introHtml
              . '<div style="white-space:pre-wrap;font-family:Arial,sans-serif;font-size:14px;color:#222;line-height:1.55;background:#ffffff;padding:12px 14px;border-left:3px solid #0A2A66;border-radius:4px;">'
              . nl2br(htmlspecialchars($plainBody))
              . '</div>'
              . $sigHtml
              . $transcriptHtml
              . '</div>';

    // Plain-text body
    $plainParts = [];
    $plainParts[] = $recipientName ? "Bonjour {$recipientName}," : "Bonjour,";
    if ($hasTranscript) {
        $plainParts[] = "";
        $plainParts[] = "Suite a votre conversation avec notre assistant ExpoBeton RDC, voici la reponse de notre equipe :";
    }
    $plainParts[] = "";
    $plainParts[] = $plainBody;
    $plainParts[] = "";
    $plainParts[] = "--";
    $plainParts[] = "Equipe ExpoBeton RDC";
    $plainParts[] = "www.expobetonrdc.com";
    if ($hasTranscript) {
        $plainParts[] = "";
        $plainParts[] = "===========================================";
        $plainParts[] = "Rappel de votre conversation (pour reference)";
        $plainParts[] = "===========================================";
        $plainParts[] = "";
        $plainParts[] = $rendered['text'];
    }
    $plainFull = implode("\r\n", $plainParts) . "\r\n";

    $boundary = md5(uniqid('', true));
    $headers  = "From: " . mb_encode_mimeheader($fromName, 'UTF-8', 'B') . " <{$fromAddr}>\r\n";
    $headers .= "Reply-To: {$replyTo}\r\n";
    $headers .= "MIME-Version: 1.0\r\n";
    $headers .= "Content-Type: multipart/alternative; boundary=\"{$boundary}\"\r\n";
    $headers .= "X-Mailer: ExpoBetonAdminDashboard\r\n";

    $msg  = "--{$boundary}\r\n";
    $msg .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $msg .= "Content-Transfer-Encoding: 8bit\r\n\r\n";
    $msg .= $plainFull . "\r\n";
    $msg .= "--{$boundary}\r\n";
    $msg .= "Content-Type: text/html; charset=UTF-8\r\n";
    $msg .= "Content-Transfer-Encoding: 8bit\r\n\r\n";
    $msg .= "<!DOCTYPE html><html><body style=\"margin:0;padding:16px;background:#f8f9fa;\">{$bodyHtml}</body></html>\r\n\r\n";
    $msg .= "--{$boundary}--";

    $encodedSubject = mb_encode_mimeheader($subject, 'UTF-8', 'B');

    try {
        $ok = @mail($to, $encodedSubject, $msg, $headers, "-f{$fromAddr}");
        if ($ok) return ['ok' => true, 'error' => null];
        $err = error_get_last();
        return ['ok' => false, 'error' => $err['message'] ?? 'mail() returned false'];
    } catch (Exception $e) {
        return ['ok' => false, 'error' => $e->getMessage()];
    }
}

// Get messages
$stmt = $db->prepare("SELECT 'chat' AS kind, id, sender, message_text, intent, confidence, timestamp FROM messages WHERE session_id = ?
                      UNION ALL
                      SELECT 'email' AS kind, id, 'admin' AS sender, CONCAT('[Email: ', subject, ']\n\n', message_text) AS message_text,
                             NULL AS intent, NULL AS confidence, sent_at AS timestamp
                      FROM admin_replies WHERE session_id = ?
                      ORDER BY timestamp ASC");
$stmt->execute([$sessionId, $sessionId]);
$timeline = $stmt->fetchAll();

$isUnresolved = !empty($session['is_unresolved']) && empty($session['resolved_at']);
$isResolved   = !empty($session['resolved_at']);
$userEmail    = $session['user_email'] ?? '';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversation Detail - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
    <style>
        .chat-admin { background:#e8f5e9; border:1px solid #c8e6c9; border-radius:10px; padding:10px 14px; max-width: 80%; }
        .chat-admin .email-head { font-size:0.75rem; color:#2e7d32; font-weight:700; text-transform:uppercase; letter-spacing:.3px; }
    </style>
</head>
<body>
    <?php renderNavbar('conversations'); ?>

    <div class="container-fluid mt-4">
        <a href="conversations.php" class="btn btn-outline-secondary btn-sm mb-3"><i class="bi bi-arrow-left"></i> Back</a>
        <?php if (!empty($userEmail) && canEditData()): ?>
            <button type="button" class="btn btn-primary btn-sm mb-3 ms-2" data-bs-toggle="modal" data-bs-target="#replyWithTranscriptModal" style="background:#0A2A66;border-color:#0A2A66;">
                <i class="bi bi-envelope-paper-fill"></i> Reply with conversation transcript
            </button>
        <?php endif; ?>
        <!-- Export this conversation -->
        <div class="btn-group btn-group-sm mb-3 ms-2" role="group" aria-label="Export this conversation">
            <button type="button" class="btn btn-outline-primary dropdown-toggle" data-bs-toggle="dropdown">
                <i class="bi bi-download"></i> Export transcript
            </button>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" target="_blank" href="export_conversations.php?format=csv&amp;id=<?= urlencode($sessionId) ?>"><i class="bi bi-filetype-csv"></i> CSV (Excel)</a></li>
                <li><a class="dropdown-item" target="_blank" href="export_conversations.php?format=json&amp;id=<?= urlencode($sessionId) ?>"><i class="bi bi-filetype-json"></i> JSON</a></li>
                <li><a class="dropdown-item" target="_blank" href="export_conversations.php?format=pdf&amp;id=<?= urlencode($sessionId) ?>"><i class="bi bi-filetype-pdf"></i> PDF (print-friendly)</a></li>
            </ul>
        </div>

        <?php if ($flashMsg): ?>
            <div class="alert alert-<?= $flashType ?> alert-dismissible fade show" role="alert">
                <?= escape($flashMsg) ?>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        <?php endif; ?>

        <!-- Resolution status banner -->
        <?php if ($isUnresolved): ?>
            <div class="alert alert-warning d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>Unresolved conversation</strong> &mdash; the user left without getting a satisfactory answer.
                </div>
                <?php if (canEditData()): ?>
                <form method="POST" class="m-0">
                    <input type="hidden" name="action" value="mark_resolved">
                    <button class="btn btn-sm btn-outline-secondary"><i class="bi bi-check2-circle"></i> Mark as resolved</button>
                </form>
                <?php endif; ?>
            </div>
        <?php elseif ($isResolved): ?>
            <div class="alert alert-success d-flex justify-content-between align-items-center">
                <div>
                    <i class="bi bi-envelope-check"></i>
                    <strong>Resolved</strong> by <?= escape($session['resolved_by'] ?? 'admin') ?> on <?= date('M j, Y H:i', strtotime($session['resolved_at'])) ?>.
                </div>
                <?php if (canEditData()): ?>
                <form method="POST" class="m-0">
                    <input type="hidden" name="action" value="mark_unresolved">
                    <button class="btn btn-sm btn-outline-warning"><i class="bi bi-arrow-counterclockwise"></i> Re-open as unresolved</button>
                </form>
                <?php endif; ?>
            </div>
        <?php endif; ?>

        <div class="row g-4">
            <!-- Sidebar: Session Info + Admin Reply -->
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm mb-3">
                    <div class="card-header bg-white fw-bold">Session Info</div>
                    <div class="card-body">
                        <table class="table table-sm table-borderless mb-0">
                            <tr><td class="text-muted">Session ID</td><td class="text-break" style="font-size:0.8rem;"><?= escape($session['session_id']) ?></td></tr>
                            <tr><td class="text-muted">User</td><td><?= escape($session['user_name'] ?: '-') ?></td></tr>
                            <tr><td class="text-muted">Email</td><td><?= escape($session['user_email'] ?: '-') ?></td></tr>
                            <tr><td class="text-muted">Phone</td><td>
                              <?php
                                // Phone comes from the registration form (registrations table),
                                // falling back to the phone collected by the chat widget entry form
                                // (sessions.user_phone). '-' when neither is available.
                                $phoneVal = '';
                                if ($registration && !empty($registration['phone']) && strtolower(trim($registration['phone'])) !== 'non fourni') {
                                    $phoneVal = $registration['phone'];
                                } elseif (!empty($session['user_phone'])) {
                                    $phoneVal = $session['user_phone'];
                                }
                                if ($phoneVal !== '') {
                                    echo '<a href="tel:' . escape(preg_replace('/\s+/', '', $phoneVal)) . '">' . escape($phoneVal) . '</a>';
                                } else {
                                    echo '<span class="text-muted">-</span>';
                                }
                              ?>
                            </td></tr>
                            <tr><td class="text-muted">Country</td><td><?= formatCountryWithFlag($session['country'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">City</td><td><?= escape($session['city'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">IP</td><td><?= escape($session['ip_address'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Device</td><td><span class="badge bg-primary"><?= escape($session['device_type'] ?? '-') ?></span></td></tr>
                            <tr><td class="text-muted">Browser</td><td><?= escape($session['browser'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">OS</td><td><?= escape($session['os'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Screen</td><td><?= ($session['screen_width'] && $session['screen_height']) ? escape($session['screen_width'] . 'x' . $session['screen_height']) : '-' ?></td></tr>
                            <tr><td class="text-muted">Language</td><td><?= escape($session['language'] ?? '-') ?></td></tr>
                            <tr><td class="text-muted">Started</td><td><?= date('M j, Y H:i:s', strtotime($session['started_at'])) ?></td></tr>
                            <tr><td class="text-muted">Ended</td><td><?= $session['ended_at'] ? date('M j, Y H:i:s', strtotime($session['ended_at'])) : '<span class="text-warning">Active</span>' ?></td></tr>
                            <tr><td class="text-muted">Duration</td><td><?= formatDuration($session['duration_seconds']) ?></td></tr>
                            <tr><td class="text-muted">Messages</td><td><?= count($timeline) ?></td></tr>
                            <?php if ($session['referrer_url']): ?>
                            <tr><td class="text-muted">Referrer</td><td class="text-break" style="font-size:0.8rem;"><?= escape($session['referrer_url']) ?></td></tr>
                            <?php endif; ?>
                        </table>
                    </div>
                </div>

                <!-- Admin reply form -->
                <?php if (canEditData()): ?>
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">
                        <i class="bi bi-envelope-fill text-primary"></i> Reply by email
                    </div>
                    <div class="card-body">
                        <?php if (!$userEmail): ?>
                            <div class="alert alert-light small mb-0">
                                <i class="bi bi-info-circle"></i>
                                No user email on file. Cannot send a reply for this session.
                            </div>
                        <?php else: ?>
                            <form method="POST">
                                <input type="hidden" name="action" value="send_reply">
                                <div class="mb-2">
                                    <label class="form-label small mb-1">To</label>
                                    <input type="email" class="form-control form-control-sm" name="to" value="<?= escape($userEmail) ?>" required>
                                </div>
                                <div class="mb-2">
                                    <label class="form-label small mb-1">Subject</label>
                                    <input type="text" class="form-control form-control-sm" name="subject" value="ExpoBeton RDC — réponse à votre question" required>
                                </div>
                                <div class="mb-2">
                                    <label class="form-label small mb-1">Message</label>
                                    <textarea class="form-control form-control-sm" name="body" rows="8" required placeholder="Bonjour,&#10;&#10;Suite à votre question dans le chat, voici la réponse que je peux vous apporter..."></textarea>
                                </div>
                                <button type="submit" class="btn btn-primary btn-sm w-100" style="background:#0A2A66;border-color:#0A2A66;">
                                    <i class="bi bi-send-fill"></i> Send email &amp; mark resolved
                                </button>
                                <div class="text-muted small mt-2">
                                    From: <?= escape(defined('EMAIL_FROM_ADDRESS') ? EMAIL_FROM_ADDRESS : 'info@expobetonrdc.com') ?>
                                </div>
                            </form>
                        <?php endif; ?>
                    </div>
                </div>
                <?php else: ?>
                <div class="card border-0 shadow-sm">
                    <div class="card-body small text-muted">
                        <i class="bi bi-info-circle"></i> You are signed in as <strong>viewer</strong> &mdash; email replies and mark-resolved actions are disabled.
                    </div>
                </div>
                <?php endif; ?>
            </div>

            <!-- Chat Messages + Admin Email Replies Timeline -->
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm">
                    <div class="card-header bg-white fw-bold">Conversation (<?= count($timeline) ?> items)</div>
                    <div class="card-body chat-history" style="max-height: 70vh; overflow-y: auto; background: #f8f9fa;">
                        <?php if (empty($timeline)): ?>
                            <p class="text-center text-muted py-5">No messages recorded</p>
                        <?php else: ?>
                            <?php foreach ($timeline as $msg): ?>
                                <?php
                                    $isUser  = $msg['sender'] === 'user';
                                    $isAdmin = $msg['sender'] === 'admin';
                                    $align   = $isUser ? 'justify-content-end' : 'justify-content-start';
                                    $cls     = $isUser ? 'chat-user' : ($isAdmin ? 'chat-admin' : 'chat-bot');
                                ?>
                                <div class="d-flex mb-3 <?= $align ?>">
                                    <div class="chat-bubble <?= $cls ?>">
                                        <div class="small fw-bold mb-1">
                                            <?php if ($isAdmin): ?>
                                                <span class="email-head"><i class="bi bi-envelope-fill"></i> Admin email reply</span>
                                            <?php else: ?>
                                                <?= $isUser ? 'User' : 'Bot' ?>
                                            <?php endif; ?>
                                        </div>
                                        <div><?= nl2br(escape($msg['message_text'])) ?></div>
                                        <div class="text-end mt-1" style="font-size: 0.7rem; opacity: 0.7;">
                                            <?= date('M j H:i:s', strtotime($msg['timestamp'])) ?>
                                            <?php if (!empty($msg['intent'])): ?>
                                                <span class="ms-1 badge bg-secondary" style="font-size:0.6rem;"><?= escape($msg['intent']) ?> (<?= round(($msg['confidence'] ?? 0) * 100) ?>%)</span>
                                            <?php endif; ?>
                                        </div>
                                    </div>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <?php if (!empty($userEmail) && canEditData()): ?>
    <!-- Reply with conversation transcript modal -->
    <div class="modal fade" id="replyWithTranscriptModal" tabindex="-1" aria-labelledby="replyWithTranscriptLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
            <div class="modal-content">
                <form method="POST">
                    <input type="hidden" name="action" value="send_reply_with_transcript">
                    <div class="modal-header" style="background:#0A2A66;color:#fff;">
                        <h5 class="modal-title" id="replyWithTranscriptLabel">
                            <i class="bi bi-envelope-paper-fill"></i> Reply to user with conversation transcript
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info small">
                            <i class="bi bi-info-circle"></i>
                            Your message will be sent to the user and the <strong>complete conversation transcript</strong>
                            (<?= count($timeline) ?> item<?= count($timeline) > 1 ? 's' : '' ?>) will be appended below your reply so the user
                            understands the context.
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold small">To</label>
                            <input type="email" class="form-control" name="to" value="<?= escape($userEmail) ?>" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold small">Subject</label>
                            <input type="text" class="form-control" name="subject" value="ExpoBeton RDC — réponse à votre question" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold small">Your message to the user</label>
                            <textarea class="form-control" name="body" rows="9" required
                                placeholder="Bonjour,&#10;&#10;Suite à votre échange avec notre assistant, voici la réponse à votre question...&#10;&#10;Cordialement,"></textarea>
                            <div class="form-text">This text will appear at the top of the email, followed by the full conversation history.</div>
                        </div>
                        <div class="border rounded p-2" style="background:#f8f9fa;max-height:260px;overflow-y:auto;">
                            <div class="small text-muted fw-bold mb-2"><i class="bi bi-chat-left-text"></i> Preview of the transcript that will be included:</div>
                            <?php if (empty($timeline)): ?>
                                <div class="text-muted small">No messages in this conversation.</div>
                            <?php else: ?>
                                <?php foreach ($timeline as $msg): ?>
                                    <?php
                                        $s = $msg['sender'];
                                        $who = $s === 'user' ? 'User' : ($s === 'admin' ? 'Admin' : 'Bot');
                                        $badge = $s === 'user' ? 'bg-primary' : ($s === 'admin' ? 'bg-success' : 'bg-secondary');
                                    ?>
                                    <div class="small mb-2">
                                        <span class="badge <?= $badge ?>"><?= $who ?></span>
                                        <span class="text-muted" style="font-size:.7rem;"><?= date('M j H:i', strtotime($msg['timestamp'])) ?></span>
                                        <div class="ps-1" style="white-space:pre-wrap;"><?= escape(mb_substr($msg['message_text'], 0, 280)) ?><?= mb_strlen($msg['message_text']) > 280 ? '...' : '' ?></div>
                                    </div>
                                <?php endforeach; ?>
                            <?php endif; ?>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" class="btn btn-primary" style="background:#0A2A66;border-color:#0A2A66;">
                            <i class="bi bi-send-fill"></i> Send email with transcript &amp; mark resolved
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <?php endif; ?>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
