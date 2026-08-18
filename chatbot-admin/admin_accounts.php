<?php
/**
 * Admin Accounts Management (super_admin only).
 * Create / edit / reset-password / deactivate / delete dashboard admins.
 */
require_once __DIR__ . '/auth.php';
requireLogin();
requireRole(['super_admin']);

$db    = getDB();
$me    = (int)$_SESSION['admin_id'];
$flash = null; $flashType = 'success'; $tempPassword = null;

/* ------------------------------------------------------------------
 * Helpers
 * ----------------------------------------------------------------*/
function validRole($r) {
    return in_array($r, ['super_admin', 'admin', 'viewer'], true);
}

function countActiveSuperAdmins($db, $excludeId = 0) {
    $sql = "SELECT COUNT(*) FROM admin_users WHERE role='super_admin' AND is_active=1";
    $p = [];
    if ($excludeId > 0) { $sql .= " AND id <> ?"; $p[] = $excludeId; }
    $stmt = $db->prepare($sql);
    $stmt->execute($p);
    return (int)$stmt->fetchColumn();
}

function generateTempPassword($len = 10) {
    $chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789';
    $n = strlen($chars);
    $out = '';
    for ($i = 0; $i < $len; $i++) $out .= $chars[random_int(0, $n - 1)];
    return $out;
}

/* ------------------------------------------------------------------
 * POST actions
 * ----------------------------------------------------------------*/
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    try {
        if ($action === 'create') {
            $username = trim($_POST['username'] ?? '');
            $fullName = trim($_POST['full_name'] ?? '');
            $email    = trim($_POST['email'] ?? '');
            $role     = $_POST['role'] ?? 'viewer';
            $password = $_POST['password'] ?? '';

            if (strlen($username) < 3)          throw new Exception('Username must be at least 3 characters.');
            if (strlen($password) < 8)          throw new Exception('Password must be at least 8 characters.');
            if (!validRole($role))              throw new Exception('Invalid role.');
            if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) throw new Exception('Invalid email address.');

            $exists = $db->prepare("SELECT COUNT(*) FROM admin_users WHERE username = ?");
            $exists->execute([$username]);
            if ((int)$exists->fetchColumn() > 0) throw new Exception('Username already exists.');

            $hash = password_hash($password, PASSWORD_BCRYPT);
            $ins  = $db->prepare("INSERT INTO admin_users (username, password_hash, role, full_name, email, is_active, created_at, created_by)
                                  VALUES (?, ?, ?, ?, ?, 1, NOW(), ?)");
            $ins->execute([$username, $hash, $role, $fullName ?: null, $email ?: null, $me]);
            $flash = 'Admin account "' . $username . '" created.';
        }

        elseif ($action === 'update') {
            $id       = (int)($_POST['id'] ?? 0);
            $fullName = trim($_POST['full_name'] ?? '');
            $email    = trim($_POST['email'] ?? '');
            $role     = $_POST['role'] ?? 'viewer';
            $isActive = isset($_POST['is_active']) ? 1 : 0;

            if ($id <= 0)                       throw new Exception('Invalid account id.');
            if (!validRole($role))              throw new Exception('Invalid role.');
            if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) throw new Exception('Invalid email address.');

            // Guard: don't lock yourself out
            if ($id === $me) {
                if ($role !== 'super_admin') throw new Exception('You cannot demote yourself from super_admin.');
                if ($isActive !== 1)         throw new Exception('You cannot deactivate your own account.');
            }
            // Guard: never leave zero active super_admins
            $target = $db->prepare("SELECT role, is_active FROM admin_users WHERE id = ?");
            $target->execute([$id]);
            $cur = $target->fetch();
            if (!$cur) throw new Exception('Account not found.');

            $wasSuper   = ($cur['role'] === 'super_admin' && (int)$cur['is_active'] === 1);
            $stillSuper = ($role === 'super_admin' && $isActive === 1);
            if ($wasSuper && !$stillSuper && countActiveSuperAdmins($db, $id) === 0) {
                throw new Exception('At least one active super_admin must remain.');
            }

            $upd = $db->prepare("UPDATE admin_users SET full_name = ?, email = ?, role = ?, is_active = ? WHERE id = ?");
            $upd->execute([$fullName ?: null, $email ?: null, $role, $isActive, $id]);
            $flash = 'Account updated.';
        }

        elseif ($action === 'reset_password') {
            $id = (int)($_POST['id'] ?? 0);
            if ($id <= 0) throw new Exception('Invalid account id.');
            $newPw = generateTempPassword(12);
            $hash  = password_hash($newPw, PASSWORD_BCRYPT);
            $upd   = $db->prepare("UPDATE admin_users SET password_hash = ? WHERE id = ?");
            $upd->execute([$hash, $id]);
            $tempPassword = ['id' => $id, 'password' => $newPw];
            $flash = 'Password reset. Share the temporary password with the user securely.';
        }

        elseif ($action === 'toggle_active') {
            $id = (int)($_POST['id'] ?? 0);
            if ($id <= 0)   throw new Exception('Invalid account id.');
            if ($id === $me) throw new Exception('You cannot deactivate your own account.');

            $target = $db->prepare("SELECT role, is_active FROM admin_users WHERE id = ?");
            $target->execute([$id]);
            $cur = $target->fetch();
            if (!$cur) throw new Exception('Account not found.');

            $newActive = (int)$cur['is_active'] === 1 ? 0 : 1;
            if ($newActive === 0 && $cur['role'] === 'super_admin' && countActiveSuperAdmins($db, $id) === 0) {
                throw new Exception('At least one active super_admin must remain.');
            }
            $upd = $db->prepare("UPDATE admin_users SET is_active = ? WHERE id = ?");
            $upd->execute([$newActive, $id]);
            $flash = $newActive === 1 ? 'Account activated.' : 'Account deactivated.';
        }

        elseif ($action === 'delete') {
            $id = (int)($_POST['id'] ?? 0);
            if ($id <= 0)   throw new Exception('Invalid account id.');
            if ($id === $me) throw new Exception('You cannot delete your own account.');

            $target = $db->prepare("SELECT role, is_active FROM admin_users WHERE id = ?");
            $target->execute([$id]);
            $cur = $target->fetch();
            if (!$cur) throw new Exception('Account not found.');

            if ($cur['role'] === 'super_admin' && (int)$cur['is_active'] === 1 && countActiveSuperAdmins($db, $id) === 0) {
                throw new Exception('At least one active super_admin must remain. Deactivate or promote someone first.');
            }

            $del = $db->prepare("DELETE FROM admin_users WHERE id = ?");
            $del->execute([$id]);
            $flash = 'Account deleted.';
        }
    } catch (Exception $e) {
        $flash     = $e->getMessage();
        $flashType = 'danger';
    }
}

/* ------------------------------------------------------------------
 * List
 * ----------------------------------------------------------------*/
$admins = $db->query("
    SELECT a.*, c.username AS creator_name
    FROM admin_users a
    LEFT JOIN admin_users c ON c.id = a.created_by
    ORDER BY (a.role='super_admin') DESC, (a.role='admin') DESC, a.username ASC
")->fetchAll();

$totalAdmins = count($admins);
$totalActive = 0; $totalSuper = 0;
foreach ($admins as $a) {
    if ((int)$a['is_active'] === 1) $totalActive++;
    if ($a['role'] === 'super_admin' && (int)$a['is_active'] === 1) $totalSuper++;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Accounts - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
<?php renderNavbar('admin_accounts'); ?>

<div class="container-fluid mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <h4 class="mb-0"><i class="bi bi-shield-lock"></i> Admin Accounts</h4>
            <p class="text-muted mb-0 small">Manage who can sign in to this dashboard and what they can do.</p>
        </div>
        <button class="btn btn-primary btn-sm" style="background:#0A2A66;border-color:#0A2A66;" data-bs-toggle="modal" data-bs-target="#createAdminModal">
            <i class="bi bi-person-plus-fill"></i> New admin account
        </button>
    </div>

    <?php if ($flash): ?>
        <div class="alert alert-<?= $flashType ?> alert-dismissible fade show"><?= escape($flash) ?>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    <?php endif; ?>

    <?php if ($tempPassword): ?>
        <div class="alert alert-warning">
            <strong><i class="bi bi-key-fill"></i> Temporary password:</strong>
            <code class="fs-5"><?= escape($tempPassword['password']) ?></code>
            <div class="small text-muted">Copy this now &mdash; it will NOT be shown again.</div>
        </div>
    <?php endif; ?>

    <!-- KPI strip -->
    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="kpi-card"><div class="kpi-icon bg-primary-soft"><i class="bi bi-people-fill"></i></div>
                <div><div class="kpi-value"><?= $totalAdmins ?></div><div class="kpi-label">Total accounts</div></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="kpi-card"><div class="kpi-icon bg-success-soft"><i class="bi bi-check2-circle"></i></div>
                <div><div class="kpi-value"><?= $totalActive ?></div><div class="kpi-label">Active</div></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="kpi-card"><div class="kpi-icon bg-danger-soft"><i class="bi bi-shield-fill-check"></i></div>
                <div><div class="kpi-value"><?= $totalSuper ?></div><div class="kpi-label">Super admins</div></div>
            </div>
        </div>
    </div>

    <div class="card border-0 shadow-sm">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Username</th>
                        <th>Full name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Last login</th>
                        <th>Created</th>
                        <th class="text-end">Actions</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($admins as $a): $isSelf = ((int)$a['id'] === $me); ?>
                    <tr>
                        <td>
                            <i class="bi bi-person-circle text-muted me-1"></i>
                            <strong><?= escape($a['username']) ?></strong>
                            <?php if ($isSelf): ?><span class="badge bg-info ms-1">you</span><?php endif; ?>
                        </td>
                        <td><?= escape($a['full_name'] ?: '-') ?></td>
                        <td><?= $a['email'] ? '<a href="mailto:' . escape($a['email']) . '">' . escape($a['email']) . '</a>' : '<span class="text-muted">-</span>' ?></td>
                        <td><span class="badge role-badge role-<?= escape($a['role']) ?>"><?= escape($a['role']) ?></span></td>
                        <td>
                            <?php if ((int)$a['is_active'] === 1): ?>
                                <span class="badge bg-success"><i class="bi bi-check-circle"></i> Active</span>
                            <?php else: ?>
                                <span class="badge bg-secondary"><i class="bi bi-slash-circle"></i> Disabled</span>
                            <?php endif; ?>
                        </td>
                        <td class="small text-muted"><?= $a['last_login_at'] ? date('M j, Y H:i', strtotime($a['last_login_at'])) : 'Never' ?></td>
                        <td class="small text-muted">
                            <?= $a['created_at'] ? date('M j, Y', strtotime($a['created_at'])) : '-' ?>
                            <?php if (!empty($a['creator_name'])): ?><br><span>by <?= escape($a['creator_name']) ?></span><?php endif; ?>
                        </td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#editAdminModal<?= $a['id'] ?>"><i class="bi bi-pencil"></i></button>
                            <form method="POST" class="d-inline" onsubmit="return confirm('Generate a new temporary password for <?= escape($a['username']) ?>?');">
                                <input type="hidden" name="action" value="reset_password">
                                <input type="hidden" name="id" value="<?= $a['id'] ?>">
                                <button class="btn btn-sm btn-outline-warning" title="Reset password"><i class="bi bi-key"></i></button>
                            </form>
                            <?php if (!$isSelf): ?>
                                <form method="POST" class="d-inline" onsubmit="return confirm('<?= (int)$a['is_active'] === 1 ? 'Deactivate' : 'Activate' ?> <?= escape($a['username']) ?>?');">
                                    <input type="hidden" name="action" value="toggle_active">
                                    <input type="hidden" name="id" value="<?= $a['id'] ?>">
                                    <button class="btn btn-sm btn-outline-secondary" title="<?= (int)$a['is_active'] === 1 ? 'Deactivate' : 'Activate' ?>">
                                        <i class="bi bi-<?= (int)$a['is_active'] === 1 ? 'slash-circle' : 'check-circle' ?>"></i>
                                    </button>
                                </form>
                                <form method="POST" class="d-inline" onsubmit="return confirm('Permanently DELETE <?= escape($a['username']) ?>? This cannot be undone.');">
                                    <input type="hidden" name="action" value="delete">
                                    <input type="hidden" name="id" value="<?= $a['id'] ?>">
                                    <button class="btn btn-sm btn-outline-danger" title="Delete"><i class="bi bi-trash"></i></button>
                                </form>
                            <?php endif; ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>

    <div class="text-muted small mt-3">
        <strong>Role capabilities:</strong>
        <span class="badge role-badge role-super_admin ms-1">super_admin</span> full control, manage accounts.
        <span class="badge role-badge role-admin ms-2">admin</span> view everything, reply by email, mark resolved.
        <span class="badge role-badge role-viewer ms-2">viewer</span> read-only.
    </div>
</div>

<!-- Create modal -->
<div class="modal fade" id="createAdminModal" tabindex="-1">
    <div class="modal-dialog">
        <form class="modal-content" method="POST">
            <input type="hidden" name="action" value="create">
            <div class="modal-header" style="background:#0A2A66;color:#fff;">
                <h5 class="modal-title"><i class="bi bi-person-plus-fill"></i> New admin account</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6"><label class="form-label small">Username *</label><input type="text" class="form-control" name="username" required minlength="3" pattern="[A-Za-z0-9_.-]+"></div>
                    <div class="col-md-6"><label class="form-label small">Role *</label>
                        <select class="form-select" name="role" required>
                            <option value="viewer">viewer (read-only)</option>
                            <option value="admin" selected>admin (reply &amp; resolve)</option>
                            <option value="super_admin">super_admin (full control)</option>
                        </select>
                    </div>
                    <div class="col-md-6"><label class="form-label small">Full name</label><input type="text" class="form-control" name="full_name" maxlength="128"></div>
                    <div class="col-md-6"><label class="form-label small">Email</label><input type="email" class="form-control" name="email" maxlength="191"></div>
                    <div class="col-12"><label class="form-label small">Password *</label><input type="password" class="form-control" name="password" required minlength="8"><div class="form-text">Share the password with the user through a secure channel.</div></div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                <button class="btn btn-primary btn-sm" style="background:#0A2A66;border-color:#0A2A66;">Create account</button>
            </div>
        </form>
    </div>
</div>

<!-- Edit modals -->
<?php foreach ($admins as $a): $isSelf = ((int)$a['id'] === $me); ?>
<div class="modal fade" id="editAdminModal<?= $a['id'] ?>" tabindex="-1">
    <div class="modal-dialog">
        <form class="modal-content" method="POST">
            <input type="hidden" name="action" value="update">
            <input type="hidden" name="id" value="<?= $a['id'] ?>">
            <div class="modal-header" style="background:#0A2A66;color:#fff;">
                <h5 class="modal-title"><i class="bi bi-pencil-square"></i> Edit <?= escape($a['username']) ?></h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="row g-3">
                    <div class="col-md-6"><label class="form-label small">Username</label><input type="text" class="form-control" value="<?= escape($a['username']) ?>" disabled></div>
                    <div class="col-md-6"><label class="form-label small">Role</label>
                        <select class="form-select" name="role" <?= $isSelf ? 'data-self="1"' : '' ?>>
                            <option value="viewer"      <?= $a['role']==='viewer'?'selected':'' ?>>viewer (read-only)</option>
                            <option value="admin"       <?= $a['role']==='admin'?'selected':'' ?>>admin (reply &amp; resolve)</option>
                            <option value="super_admin" <?= $a['role']==='super_admin'?'selected':'' ?>>super_admin (full control)</option>
                        </select>
                        <?php if ($isSelf): ?><div class="form-text text-warning">You cannot demote yourself.</div><?php endif; ?>
                    </div>
                    <div class="col-md-6"><label class="form-label small">Full name</label><input type="text" class="form-control" name="full_name" value="<?= escape($a['full_name']) ?>" maxlength="128"></div>
                    <div class="col-md-6"><label class="form-label small">Email</label><input type="email" class="form-control" name="email" value="<?= escape($a['email']) ?>" maxlength="191"></div>
                    <div class="col-12">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" name="is_active" id="active<?= $a['id'] ?>" <?= (int)$a['is_active']===1?'checked':'' ?> <?= $isSelf?'disabled':'' ?>>
                            <label class="form-check-label" for="active<?= $a['id'] ?>">Account is active (user can log in)</label>
                            <?php if ($isSelf): ?><input type="hidden" name="is_active" value="1"><?php endif; ?>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                <button class="btn btn-primary btn-sm" style="background:#0A2A66;border-color:#0A2A66;">Save changes</button>
            </div>
        </form>
    </div>
</div>
<?php endforeach; ?>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
