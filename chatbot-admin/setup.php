<?php
require_once __DIR__ . '/auth.php';

// Prevent access if admin already exists
if (hasAdminUsers()) {
    header('Location: login.php');
    exit;
}

$error = '';
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';
    $confirm = $_POST['confirm_password'] ?? '';
    
    if (strlen($username) < 3) {
        $error = 'Username must be at least 3 characters.';
    } elseif (strlen($password) < 6) {
        $error = 'Password must be at least 6 characters.';
    } elseif ($password !== $confirm) {
        $error = 'Passwords do not match.';
    } else {
        $db = getDB();
        $hash = password_hash($password, PASSWORD_BCRYPT);
        $stmt = $db->prepare("INSERT INTO admin_users (username, password_hash, created_at) VALUES (?, ?, NOW())");
        $stmt->execute([$username, $hash]);
        $success = true;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Setup - <?= APP_NAME ?></title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="assets/style.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center" style="min-height: 100vh;">
    <div class="card shadow-lg" style="width: 100%; max-width: 480px;">
        <div class="card-body p-5">
            <div class="text-center mb-4">
                <h3 class="fw-bold" style="color: #0A2A66;">Initial Setup</h3>
                <p class="text-muted">Create the first admin account for the dashboard.</p>
            </div>
            
            <?php if ($success): ?>
                <div class="alert alert-success">
                    Admin account created successfully!
                    <br><a href="login.php" class="fw-bold">Go to Login</a>
                </div>
            <?php else: ?>
                <?php if ($error): ?>
                    <div class="alert alert-danger"><?= escape($error) ?></div>
                <?php endif; ?>
                
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required minlength="3" value="<?= escape($_POST['username'] ?? '') ?>">
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required minlength="6">
                    </div>
                    <div class="mb-3">
                        <label for="confirm_password" class="form-label">Confirm Password</label>
                        <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100" style="background: #0A2A66; border-color: #0A2A66;">
                        Create Admin Account
                    </button>
                </form>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
