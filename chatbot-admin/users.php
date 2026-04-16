<?php
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

$page = max(1, intval($_GET['page'] ?? 1));
$search = trim($_GET['search'] ?? '');

$where = [];
$params = [];
if ($search) {
    $where[] = "(u.email LIKE ? OR u.name LIKE ?)";
    $params[] = "%$search%";
    $params[] = "%$search%";
}
$whereSQL = $where ? 'WHERE ' . implode(' AND ', $where) : '';

$total = $db->prepare("SELECT COUNT(*) FROM users u $whereSQL");
$total->execute($params);
$totalCount = $total->fetchColumn();
$totalPages = max(1, ceil($totalCount / ITEMS_PER_PAGE));
$offset = ($page - 1) * ITEMS_PER_PAGE;

$stmt = $db->prepare("SELECT u.* FROM users u $whereSQL ORDER BY u.last_seen DESC LIMIT " . ITEMS_PER_PAGE . " OFFSET $offset");
$stmt->execute($params);
$users = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Users - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: #0A2A66;">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="dashboard.php">ExpoBeton Analytics</a>
            <div class="navbar-nav ms-auto d-flex flex-row gap-2">
                <a class="nav-link" href="dashboard.php"><i class="bi bi-speedometer2"></i> Dashboard</a>
                <a class="nav-link" href="conversations.php"><i class="bi bi-chat-dots"></i> Conversations</a>
                <a class="nav-link" href="analytics.php"><i class="bi bi-bar-chart"></i> Analytics</a>
                <a class="nav-link active" href="users.php"><i class="bi bi-people"></i> Users</a>
                <a class="nav-link text-warning" href="logout.php"><i class="bi bi-box-arrow-right"></i> Logout</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <h4 class="mb-3">Users <span class="text-muted fs-6">(<?= number_format($totalCount) ?> total)</span></h4>
        
        <form class="card border-0 shadow-sm mb-4" method="GET">
            <div class="card-body">
                <div class="row g-2 align-items-end">
                    <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm" name="search" value="<?= escape($search) ?>" placeholder="Search by email or name...">
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-sm btn-primary" style="background:#0A2A66; border-color:#0A2A66;">Search</button>
                    </div>
                </div>
            </div>
        </form>

        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Country</th>
                            <th>Sessions</th>
                            <th>First Seen</th>
                            <th>Last Seen</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($users as $u): ?>
                        <tr style="cursor:pointer;" onclick="location.href='conversations.php?search=<?= urlencode($u['email']) ?>'">
                            <td><?= escape($u['email']) ?></td>
                            <td><?= escape($u['name'] ?: '-') ?></td>
                            <td><?= escape($u['country'] ?? '-') ?></td>
                            <td><?= $u['session_count'] ?></td>
                            <td><?= date('M j, Y', strtotime($u['first_seen'])) ?></td>
                            <td><?= date('M j, Y H:i', strtotime($u['last_seen'])) ?></td>
                        </tr>
                        <?php endforeach; ?>
                        <?php if (empty($users)): ?>
                        <tr><td colspan="6" class="text-center text-muted py-4">No users found</td></tr>
                        <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <?php if ($totalPages > 1): ?>
        <nav class="mt-3">
            <ul class="pagination justify-content-center">
                <?php for ($i = max(1, $page-2); $i <= min($totalPages, $page+2); $i++): ?>
                    <li class="page-item <?= $i === $page ? 'active' : '' ?>">
                        <a class="page-link" href="?<?= http_build_query(array_merge($_GET, ['page' => $i])) ?>"><?= $i ?></a>
                    </li>
                <?php endfor; ?>
            </ul>
        </nav>
        <?php endif; ?>
    </div>
</body>
</html>
