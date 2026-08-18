<?php
/**
 * Registrations Directory - users who completed the chatbot registration form.
 * Presents a beautiful card grid with search, filters, date range, CSV export
 * and a switchable table view.
 */
require_once __DIR__ . '/auth.php';
requireLogin();
$db = getDB();

/* ------------------------------------------------------------------
 * Inputs / filters
 * ----------------------------------------------------------------*/
$search    = trim($_GET['search'] ?? '');
$category  = trim($_GET['category'] ?? '');
$country   = trim($_GET['country'] ?? '');
$dateFrom  = trim($_GET['from'] ?? '');
$dateTo    = trim($_GET['to'] ?? '');
$hasPhone  = isset($_GET['has_phone']) && $_GET['has_phone'] === '1';
$view      = ($_GET['view'] ?? 'cards') === 'table' ? 'table' : 'cards';
$page      = max(1, intval($_GET['page'] ?? 1));
$perPage   = 24;
$exportCsv = isset($_GET['export']) && $_GET['export'] === 'csv';

$where  = [];
$params = [];

if ($search !== '') {
    $where[] = "(r.contact_name LIKE ? OR r.email LIKE ? OR r.company LIKE ? OR r.phone LIKE ? OR r.reference_number LIKE ?)";
    $q = "%{$search}%";
    $params[] = $q; $params[] = $q; $params[] = $q; $params[] = $q; $params[] = $q;
}
if ($category !== '') { $where[] = "r.category = ?"; $params[] = $category; }
if ($country !== '')  { $where[] = "r.country  = ?"; $params[] = $country; }
if ($dateFrom !== '') { $where[] = "DATE(r.registered_at) >= ?"; $params[] = $dateFrom; }
if ($dateTo !== '')   { $where[] = "DATE(r.registered_at) <= ?"; $params[] = $dateTo; }
if ($hasPhone) {
    $where[] = "(r.phone IS NOT NULL AND r.phone <> '' AND LOWER(r.phone) <> 'non fourni')";
}
$whereSQL = $where ? 'WHERE ' . implode(' AND ', $where) : '';

/* ------------------------------------------------------------------
 * KPIs
 * ----------------------------------------------------------------*/
$totalAll      = (int)$db->query("SELECT COUNT(*) FROM registrations")->fetchColumn();
$totalMonth    = (int)$db->query("SELECT COUNT(*) FROM registrations WHERE registered_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")->fetchColumn();
$totalWeek     = (int)$db->query("SELECT COUNT(*) FROM registrations WHERE registered_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")->fetchColumn();
$totalWithPhone = (int)$db->query("SELECT COUNT(*) FROM registrations WHERE phone IS NOT NULL AND phone <> '' AND LOWER(phone) <> 'non fourni'")->fetchColumn();

/* ------------------------------------------------------------------
 * Filter options
 * ----------------------------------------------------------------*/
$categoryOptions = $db->query("SELECT DISTINCT category FROM registrations WHERE category IS NOT NULL AND category <> '' ORDER BY category")->fetchAll(PDO::FETCH_COLUMN);
$countryOptions  = $db->query("SELECT DISTINCT country  FROM registrations WHERE country  IS NOT NULL AND country  <> '' ORDER BY country")->fetchAll(PDO::FETCH_COLUMN);

/* ------------------------------------------------------------------
 * CSV export (all filtered rows)
 * ----------------------------------------------------------------*/
if ($exportCsv) {
    $stmt = $db->prepare("SELECT r.*, s.city FROM registrations r LEFT JOIN sessions s ON s.session_id = r.session_id $whereSQL ORDER BY r.registered_at DESC");
    $stmt->execute($params);

    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="registrations-' . date('Y-m-d') . '.csv"');
    $out = fopen('php://output', 'w');
    // BOM for Excel UTF-8
    fwrite($out, chr(0xEF).chr(0xBB).chr(0xBF));
    fputcsv($out, ['Reference', 'Registered at', 'Contact name', 'Email', 'Phone', 'Company', 'Category', 'Country', 'City', 'Session ID']);
    while ($row = $stmt->fetch()) {
        fputcsv($out, [
            $row['reference_number'], $row['registered_at'],
            $row['contact_name'], $row['email'], $row['phone'],
            $row['company'], $row['category'], $row['country'],
            $row['city'] ?? '', $row['session_id'],
        ]);
    }
    fclose($out);
    exit;
}

/* ------------------------------------------------------------------
 * List + pagination
 * ----------------------------------------------------------------*/
$countStmt = $db->prepare("SELECT COUNT(*) FROM registrations r $whereSQL");
$countStmt->execute($params);
$totalFiltered = (int)$countStmt->fetchColumn();
$totalPages    = max(1, (int)ceil($totalFiltered / $perPage));
$page          = min($page, $totalPages);
$offset        = ($page - 1) * $perPage;

$stmt = $db->prepare("
    SELECT r.*, s.city, s.country AS session_country
    FROM registrations r
    LEFT JOIN sessions s ON s.session_id = r.session_id
    $whereSQL
    ORDER BY r.registered_at DESC
    LIMIT $perPage OFFSET $offset
");
$stmt->execute($params);
$rows = $stmt->fetchAll();

/* ------------------------------------------------------------------
 * Helpers
 * ----------------------------------------------------------------*/
function getInitials($name, $fallback = '?') {
    $name = trim((string)$name);
    if ($name === '') return $fallback;
    $parts = preg_split('/\s+/', $name);
    $out = '';
    foreach ($parts as $p) {
        if ($p !== '') $out .= mb_strtoupper(mb_substr($p, 0, 1, 'UTF-8'), 'UTF-8');
        if (mb_strlen($out) >= 2) break;
    }
    return $out === '' ? $fallback : $out;
}

function categoryBadgeClass($category) {
    $c = mb_strtolower((string)$category, 'UTF-8');
    if (strpos($c, 'platinum') !== false) return 'cat-platinum';
    if (strpos($c, 'gold')     !== false || strpos($c, 'or') !== false)     return 'cat-gold';
    if (strpos($c, 'silver')   !== false || strpos($c, 'argent') !== false) return 'cat-silver';
    if (strpos($c, 'bronze')   !== false) return 'cat-bronze';
    if (strpos($c, 'expos')    !== false) return 'cat-exposant';
    if (strpos($c, 'partic')   !== false || strpos($c, 'visit') !== false)  return 'cat-participant';
    return 'cat-default';
}

function displayPhone($phone) {
    $p = trim((string)$phone);
    if ($p === '' || mb_strtolower($p, 'UTF-8') === 'non fourni') return null;
    return $p;
}

function qsWith($overrides = []) {
    $q = array_merge($_GET, $overrides);
    unset($q['export']);
    return http_build_query($q);
}

$hasFilter = ($search !== '' || $category !== '' || $country !== '' || $dateFrom !== '' || $dateTo !== '' || $hasPhone);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registrations - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body>
<?php renderNavbar('registrations'); ?>

<div class="container-fluid mt-4">

    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <div>
            <h4 class="mb-0"><i class="bi bi-person-vcard"></i> Registrations</h4>
            <p class="text-muted mb-0 small">Users who filled out the registration form in the chatbot.</p>
        </div>
        <div class="d-flex gap-2">
            <div class="btn-group btn-group-sm" role="group" aria-label="View">
                <a href="?<?= qsWith(['view' => 'cards']) ?>" class="btn btn-outline-secondary <?= $view==='cards'?'active':'' ?>"><i class="bi bi-grid-3x3-gap"></i> Cards</a>
                <a href="?<?= qsWith(['view' => 'table']) ?>" class="btn btn-outline-secondary <?= $view==='table'?'active':'' ?>"><i class="bi bi-table"></i> Table</a>
            </div>
            <a href="?<?= qsWith(['export' => 'csv']) ?>" class="btn btn-sm btn-outline-success"><i class="bi bi-download"></i> Export CSV</a>
        </div>
    </div>

    <!-- KPI strip -->
    <div class="row g-3 mb-4">
        <div class="col-md-3 col-sm-6">
            <div class="kpi-card"><div class="kpi-icon bg-primary-soft"><i class="bi bi-people-fill"></i></div>
                <div><div class="kpi-value"><?= number_format($totalAll) ?></div><div class="kpi-label">Total registrations</div></div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="kpi-card"><div class="kpi-icon bg-success-soft"><i class="bi bi-calendar-month"></i></div>
                <div><div class="kpi-value"><?= number_format($totalMonth) ?></div><div class="kpi-label">Last 30 days</div></div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="kpi-card"><div class="kpi-icon bg-warning-soft"><i class="bi bi-calendar-week"></i></div>
                <div><div class="kpi-value"><?= number_format($totalWeek) ?></div><div class="kpi-label">Last 7 days</div></div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="kpi-card"><div class="kpi-icon bg-info-soft"><i class="bi bi-telephone-fill"></i></div>
                <div><div class="kpi-value"><?= number_format($totalWithPhone) ?></div><div class="kpi-label">With phone number</div></div>
            </div>
        </div>
    </div>

    <!-- Filters -->
    <form class="card border-0 shadow-sm mb-4" method="GET">
        <input type="hidden" name="view" value="<?= escape($view) ?>">
        <div class="card-body">
            <div class="row g-2 align-items-end">
                <div class="col-lg-3 col-md-6"><label class="form-label small mb-1">Search</label>
                    <input type="text" class="form-control form-control-sm" name="search" value="<?= escape($search) ?>" placeholder="Name, email, phone, company, ref#">
                </div>
                <div class="col-lg-2 col-md-4"><label class="form-label small mb-1">Category</label>
                    <select class="form-select form-select-sm" name="category">
                        <option value="">All</option>
                        <?php foreach ($categoryOptions as $c): ?>
                            <option value="<?= escape($c) ?>" <?= $category === $c ? 'selected' : '' ?>><?= escape($c) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-lg-2 col-md-4"><label class="form-label small mb-1">Country</label>
                    <select class="form-select form-select-sm" name="country">
                        <option value="">All</option>
                        <?php foreach ($countryOptions as $c): ?>
                            <option value="<?= escape($c) ?>" <?= $country === $c ? 'selected' : '' ?>><?= escape($c) ?></option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-lg-2 col-md-4"><label class="form-label small mb-1">From</label>
                    <input type="date" class="form-control form-control-sm" name="from" value="<?= escape($dateFrom) ?>">
                </div>
                <div class="col-lg-2 col-md-4"><label class="form-label small mb-1">To</label>
                    <input type="date" class="form-control form-control-sm" name="to" value="<?= escape($dateTo) ?>">
                </div>
                <div class="col-lg-1 col-md-4">
                    <div class="form-check mt-3">
                        <input class="form-check-input" type="checkbox" name="has_phone" id="hasPhone" value="1" <?= $hasPhone ? 'checked' : '' ?>>
                        <label class="form-check-label small" for="hasPhone">Has phone</label>
                    </div>
                </div>
                <div class="col-12 d-flex gap-2 mt-2">
                    <button type="submit" class="btn btn-sm btn-primary" style="background:#0A2A66;border-color:#0A2A66;"><i class="bi bi-funnel-fill"></i> Apply filters</button>
                    <?php if ($hasFilter): ?>
                        <a href="registrations.php?view=<?= escape($view) ?>" class="btn btn-sm btn-outline-secondary"><i class="bi bi-x-circle"></i> Reset</a>
                    <?php endif; ?>
                    <span class="ms-auto text-muted small align-self-center">
                        <strong><?= number_format($totalFiltered) ?></strong> result<?= $totalFiltered === 1 ? '' : 's' ?>
                    </span>
                </div>
            </div>
        </div>
    </form>

    <?php if (empty($rows)): ?>
        <div class="card border-0 shadow-sm">
            <div class="card-body text-center py-5">
                <i class="bi bi-inbox display-3 text-muted"></i>
                <h5 class="mt-3 mb-1">No registrations match</h5>
                <p class="text-muted">Try adjusting your filters or clear them to see everyone.</p>
            </div>
        </div>
    <?php elseif ($view === 'cards'): ?>
        <div class="row g-3">
            <?php foreach ($rows as $r):
                $phone    = displayPhone($r['phone']);
                $catClass = categoryBadgeClass($r['category']);
                $initials = getInitials($r['contact_name'] ?: $r['email']);
                $country  = $r['country'] ?: ($r['session_country'] ?? '');
            ?>
                <div class="col-xl-4 col-md-6">
                    <div class="reg-card card border-0 shadow-sm h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-start mb-3">
                                <div class="reg-avatar me-3"><?= escape($initials) ?></div>
                                <div class="flex-grow-1 min-w-0">
                                    <div class="fw-bold text-truncate" title="<?= escape($r['contact_name']) ?>">
                                        <?= escape($r['contact_name'] ?: '(no name)') ?>
                                    </div>
                                    <div class="text-muted small text-truncate" title="<?= escape($r['company']) ?>">
                                        <?= $r['company'] ? '<i class="bi bi-building"></i> ' . escape($r['company']) : '<span class="fst-italic">No company</span>' ?>
                                    </div>
                                </div>
                                <?php if ($r['category']): ?>
                                    <span class="reg-category-badge <?= $catClass ?>" title="Category"><?= escape($r['category']) ?></span>
                                <?php endif; ?>
                            </div>

                            <ul class="list-unstyled mb-3 small">
                                <li class="mb-1 text-truncate">
                                    <i class="bi bi-envelope text-muted"></i>
                                    <?= $r['email'] ? '<a href="mailto:' . escape($r['email']) . '">' . escape($r['email']) . '</a>' : '<span class="text-muted">-</span>' ?>
                                </li>
                                <li class="mb-1">
                                    <i class="bi bi-telephone text-muted"></i>
                                    <?php if ($phone): ?>
                                        <a href="tel:<?= escape(preg_replace('/\s+/', '', $phone)) ?>"><?= escape($phone) ?></a>
                                    <?php else: ?>
                                        <span class="text-muted">Non fourni</span>
                                    <?php endif; ?>
                                </li>
                                <li class="mb-1">
                                    <i class="bi bi-geo-alt text-muted"></i>
                                    <?= formatCountryWithFlag($country ?: '-') ?>
                                    <?php if (!empty($r['city'])): ?>
                                        <span class="text-muted">&middot; <?= escape($r['city']) ?></span>
                                    <?php endif; ?>
                                </li>
                                <?php if ($r['reference_number']): ?>
                                <li class="mb-1">
                                    <i class="bi bi-hash text-muted"></i>
                                    <code class="small"><?= escape($r['reference_number']) ?></code>
                                </li>
                                <?php endif; ?>
                            </ul>

                            <div class="d-flex justify-content-between align-items-center pt-2 border-top">
                                <div class="text-muted small">
                                    <i class="bi bi-clock"></i>
                                    <?= date('M j, Y', strtotime($r['registered_at'])) ?>
                                    <span class="text-muted-2"><?= date('H:i', strtotime($r['registered_at'])) ?></span>
                                </div>
                                <?php if (!empty($r['session_id'])): ?>
                                    <a href="conversation_detail.php?id=<?= urlencode($r['session_id']) ?>" class="btn btn-sm btn-outline-primary"><i class="bi bi-chat-dots"></i> Conversation</a>
                                <?php endif; ?>
                            </div>
                        </div>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
    <?php else: /* Table view */ ?>
        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Name</th><th>Company</th><th>Email</th><th>Phone</th>
                            <th>Category</th><th>Country</th><th>Reference</th><th>Registered</th><th></th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php foreach ($rows as $r):
                        $phone    = displayPhone($r['phone']);
                        $catClass = categoryBadgeClass($r['category']);
                        $country  = $r['country'] ?: ($r['session_country'] ?? '');
                    ?>
                        <tr>
                            <td>
                                <div class="d-flex align-items-center">
                                    <div class="reg-avatar reg-avatar-sm me-2"><?= escape(getInitials($r['contact_name'] ?: $r['email'])) ?></div>
                                    <div><?= escape($r['contact_name'] ?: '-') ?></div>
                                </div>
                            </td>
                            <td><?= escape($r['company'] ?: '-') ?></td>
                            <td><?= $r['email'] ? '<a href="mailto:' . escape($r['email']) . '">' . escape($r['email']) . '</a>' : '-' ?></td>
                            <td><?= $phone ? escape($phone) : '<span class="text-muted">-</span>' ?></td>
                            <td><?= $r['category'] ? '<span class="reg-category-badge ' . $catClass . '">' . escape($r['category']) . '</span>' : '-' ?></td>
                            <td><?= formatCountryWithFlag($country ?: '-') ?></td>
                            <td><?= $r['reference_number'] ? '<code class="small">' . escape($r['reference_number']) . '</code>' : '-' ?></td>
                            <td class="small text-muted"><?= date('M j, Y H:i', strtotime($r['registered_at'])) ?></td>
                            <td class="text-end">
                                <?php if (!empty($r['session_id'])): ?>
                                    <a href="conversation_detail.php?id=<?= urlencode($r['session_id']) ?>" class="btn btn-sm btn-outline-primary"><i class="bi bi-chat-dots"></i></a>
                                <?php endif; ?>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    <?php endif; ?>

    <?php if ($totalPages > 1): ?>
        <nav class="mt-4">
            <ul class="pagination justify-content-center">
                <?php for ($i = max(1, $page - 2); $i <= min($totalPages, $page + 2); $i++): ?>
                    <li class="page-item <?= $i === $page ? 'active' : '' ?>">
                        <a class="page-link" href="?<?= qsWith(['page' => $i]) ?>"><?= $i ?></a>
                    </li>
                <?php endfor; ?>
            </ul>
            <div class="text-center text-muted small">Page <?= $page ?> of <?= $totalPages ?></div>
        </nav>
    <?php endif; ?>

</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
