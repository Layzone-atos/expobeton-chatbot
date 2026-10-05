<?php
/**
 * ExpoBeton RDC — Live Chat : file d'attente et fil de discussion opérateur.
 *
 * Les sessions ouvertes par le widget public (mode « live ») arrivent ici ;
 * un opérateur répond en temps réel, le widget les récupérant par poll.
 * À la clôture, le transcript part par email au format du chatbot.
 */
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/api_livechat.php'; /* fonctions seules : dispatch gardé */
requireLogin();
livechat_ensure_tables();
$db = getDB();

/* Actions opérateur soumises par formulaire (réponse / clôture). */
if ($_SERVER['REQUEST_METHOD'] === 'POST' && canEditData()) {
    $act = isset($_POST['act']) ? $_POST['act'] : '';
    $sid = (int)(isset($_POST['session_id']) ? $_POST['session_id'] : 0);
    if ($act === 'reply') {
        $msg = livechat_str(isset($_POST['message']) ? $_POST['message'] : '', 2000);
        $sess = livechat_session_by_id($sid);
        if ($sess && $sess['statut'] === 'open' && $msg !== '') {
            livechat_add_message($sid, 'operator', $msg);
            $db->prepare("UPDATE livechat_sessions SET operator_id = COALESCE(operator_id, ?) WHERE id = ?")
               ->execute([(int)$_SESSION['admin_id'], $sid]);
        }
    } elseif ($act === 'close') {
        livechat_close_session($sid);
    }
    header('Location: livechat.php?session=' . $sid);
    exit;
}

/** Bulle de message ; $forThread indique le rendu fil (sinon aperçu inutile). */
function livechat_page_message($m)
{
    $cls = 'livechat-msg-' . $m['sender'];
    $label = livechat_sender_label($m['sender']);
    $heure = date('H:i', strtotime($m['created_at']));
    ?>
    <div class="livechat-msg <?= $cls ?> mb-2">
        <div class="small text-muted mb-1"><?= escape($label) ?> · <?= escape($heure) ?></div>
        <div class="livechat-bubble"><?= nl2br(escape($m['body'])) ?></div>
    </div>
    <?php
}

$sessionId = (int)(isset($_GET['session']) ? $_GET['session'] : 0);
$session = $sessionId ? livechat_session_by_id($sessionId) : null;

if ($session) {
    $messages = livechat_all_messages($session['id']);
    $lastId = count($messages) ? (int)$messages[count($messages) - 1]['id'] : 0;
} else {
    $openCount = (int)$db->query("SELECT COUNT(*) FROM livechat_sessions WHERE statut = 'open'")->fetchColumn();
    $sessions = $db->query(
        "SELECT s.*, (SELECT COUNT(*) FROM livechat_messages m WHERE m.session_id = s.id) AS nb_msg
           FROM livechat_sessions s
          ORDER BY (s.statut = 'open') DESC, s.created_at DESC
          LIMIT 100"
    )->fetchAll();
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Chat - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
    <?php if (!$session): ?>
    <!-- File d'attente : rafraîchissement automatique léger. -->
    <meta http-equiv="refresh" content="15">
    <?php endif; ?>
    <style>
        .livechat-thread { max-height: 60vh; overflow-y: auto; background: #f8f9fa; border-radius: 8px; padding: 16px; }
        .livechat-bubble { display: inline-block; padding: 8px 12px; border-radius: 10px; background: #fff; border: 1px solid #dee2e6; max-width: 80%; }
        .livechat-msg-visitor .livechat-bubble { background: #e7f1ff; border-color: #b6d4fe; }
        .livechat-msg-operator { text-align: right; }
        .livechat-msg-operator .livechat-bubble { background: #0A2A66; color: #fff; border-color: #0A2A66; text-align: left; }
        .livechat-msg-system { text-align: center; }
        .livechat-msg-system .livechat-bubble { background: transparent; border: 0; color: #6c757d; font-size: 12px; }
    </style>
</head>
<body>
    <?php renderNavbar('livechat'); ?>

    <div class="container-fluid mt-4">
    <?php if ($session): ?>
        <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <h4 class="mb-0">
                <i class="bi bi-headset"></i> <?= escape($session['nom']) ?>
                <?php if ($session['statut'] === 'open'): ?>
                    <span class="badge text-bg-success">open</span>
                <?php else: ?>
                    <span class="badge text-bg-secondary">closed</span>
                <?php endif; ?>
            </h4>
            <a href="livechat.php" class="btn btn-sm btn-outline-secondary"><i class="bi bi-arrow-left"></i> Toutes les sessions</a>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm">
                    <div class="card-body">
                        <div class="livechat-thread" id="livechat-thread">
                            <?php foreach ($messages as $m): ?>
                                <?php livechat_page_message($m); ?>
                            <?php endforeach; ?>
                        </div>

                        <?php if ($session['statut'] === 'open' && canEditData()): ?>
                        <form method="POST" class="mt-3">
                            <input type="hidden" name="act" value="reply">
                            <input type="hidden" name="session_id" value="<?= (int)$session['id'] ?>">
                            <div class="input-group">
                                <input type="text" name="message" class="form-control" placeholder="Répondre au visiteur…" required maxlength="2000">
                                <button class="btn btn-primary" type="submit"><i class="bi bi-send"></i> Envoyer</button>
                            </div>
                        </form>
                        <form method="POST" class="mt-2 text-end">
                            <input type="hidden" name="act" value="close">
                            <input type="hidden" name="session_id" value="<?= (int)$session['id'] ?>">
                            <button class="btn btn-sm btn-outline-danger" type="submit" onclick="return confirm('Clôturer la conversation et envoyer le transcript par email ?');">
                                <i class="bi bi-check2-circle"></i> Clôturer la conversation
                            </button>
                        </form>
                        <?php elseif ($session['statut'] === 'open'): ?>
                        <p class="text-muted small mt-3 mb-0">Lecture seule : votre rôle ne permet pas de répondre.</p>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card border-0 shadow-sm">
                    <div class="card-body small">
                        <h6 class="card-title">Coordonnées visiteur</h6>
                        <p class="mb-1"><i class="bi bi-telephone"></i> <?= escape($session['telephone']) ?></p>
                        <p class="mb-1"><i class="bi bi-envelope"></i> <?= escape($session['email'] !== null && $session['email'] !== '' ? $session['email'] : '-') ?></p>
                        <p class="mb-1"><i class="bi bi-clock-history"></i> Ouverte le <?= escape(date('d/m/Y H:i', strtotime($session['created_at']))) ?></p>
                        <?php if ($session['closed_at']): ?>
                        <p class="mb-1"><i class="bi bi-check2-circle"></i> Close le <?= escape(date('d/m/Y H:i', strtotime($session['closed_at']))) ?></p>
                        <?php endif; ?>
                        <?php if ($session['bot_transcript']): ?>
                        <hr>
                        <h6 class="card-title">Conversation bot précédente</h6>
                        <pre class="small text-muted" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;"><?= escape($session['bot_transcript']) ?></pre>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
        </div>

        <?php if ($session['statut'] === 'open'): ?>
        <script>
        /* Poll des nouveaux messages : le fil reste vivant sans recharger
           (le brouillon de réponse n'est pas perdu). */
        (function () {
            var lastId = <?= (int)$lastId ?>;
            var thread = document.getElementById('livechat-thread');
            var labels = { visitor: 'Visiteur', operator: 'Opérateur', system: 'Système' };
            setInterval(function () {
                fetch('api_livechat.php?action=operator_poll&session_id=<?= (int)$session['id'] ?>&after=' + lastId,
                      { credentials: 'same-origin', cache: 'no-store' })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (!data.ok || !data.messages || !data.messages.length) return;
                        data.messages.forEach(function (m) {
                            lastId = Math.max(lastId, m.id);
                            var wrap = document.createElement('div');
                            wrap.className = 'livechat-msg livechat-msg-' + m.sender + ' mb-2';
                            var meta = document.createElement('div');
                            meta.className = 'small text-muted mb-1';
                            meta.textContent = (labels[m.sender] || m.sender) + ' · ' + (m.created_at || '').substr(11, 5);
                            var bubble = document.createElement('div');
                            bubble.className = 'livechat-bubble';
                            bubble.textContent = m.body;
                            wrap.appendChild(meta);
                            wrap.appendChild(bubble);
                            thread.appendChild(wrap);
                        });
                        thread.scrollTop = thread.scrollHeight;
                    })
                    .catch(function () {});
            }, 8000);
        })();
        </script>
        <?php endif; ?>

    <?php else: ?>
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h4 class="mb-0">Live Chat
                <?php if (!empty($openCount)): ?>
                    <span class="badge text-bg-success"><?= (int)$openCount ?> ouverte(s)</span>
                <?php endif; ?>
            </h4>
            <span class="text-muted small">Actualisation automatique toutes les 15 s</span>
        </div>

        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Visiteur</th>
                            <th>Téléphone</th>
                            <th>Email</th>
                            <th>Statut</th>
                            <th class="text-center">Msgs</th>
                            <th>Ouverte le</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php if (!$sessions): ?>
                        <tr><td colspan="7" class="text-center text-muted py-4">Aucune session live pour le moment. Dès qu'un opérateur est connecté, le widget du site passe en mode live et les conversations arrivent ici.</td></tr>
                    <?php endif; ?>
                    <?php foreach ($sessions as $s): ?>
                        <tr>
                            <td><?= escape($s['nom']) ?></td>
                            <td><?= escape($s['telephone']) ?></td>
                            <td><?= escape($s['email'] !== null && $s['email'] !== '' ? $s['email'] : '-') ?></td>
                            <td>
                                <?php if ($s['statut'] === 'open'): ?>
                                    <span class="badge text-bg-success">open</span>
                                <?php else: ?>
                                    <span class="badge text-bg-secondary">closed</span>
                                <?php endif; ?>
                            </td>
                            <td class="text-center"><?= (int)$s['nb_msg'] ?></td>
                            <td><?= escape(date('d/m/Y H:i', strtotime($s['created_at']))) ?></td>
                            <td class="text-end"><a class="btn btn-sm btn-outline-primary" href="?session=<?= (int)$s['id'] ?>">Ouvrir</a></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    <?php endif; ?>
    </div>
</body>
</html>
