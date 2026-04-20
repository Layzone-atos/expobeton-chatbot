Here's the complete technical breakdown of the document upload workflow:

---

## Complete Document Upload Workflow

### Overview

The chatbot integration uses two separate API calls to complete a registration:

```
Step 1: Create registration record
POST /api_chatbot_register.php?action=register
    → Returns { reference: "EXPOBETON-2026-XXXXX" }

Step 2: Upload documents (optional, for sponsors/exhibitors)
POST /upload_documents.php?ref=EXPOBETON-2026-XXXXX&type=logo
POST /upload_documents.php?ref=EXPOBETON-2026-XXXXX&type=passport
    → Returns document IDs linked to the registration
```

---

### 1. Authentication

Both endpoints use **identical authentication**:

```php
// Header checked: Authorization: Bearer ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07
function authenticate() {
    // Tries 4 methods to find the Authorization header:
    // 1. $_SERVER['HTTP_AUTHORIZATION']
    // 2. $_SERVER['REDIRECT_HTTP_AUTHORIZATION']  (after .htaccess rewrite)
    // 3. getallheaders()                         (PHP function)
    // 4. apache_request_headers()                (Apache function)
    
    // Then extracts Bearer token and compares with hash_equals (timing-safe)
}
```

The `.htaccess` rewrite rule ensures Apache passes the header:
```apache
RewriteCond %{HTTP:Authorization} ^(.*)
RewriteRule .* - [e=HTTP_AUTHORIZATION:%1]
```

---

### 2. File Upload Parameters

**Endpoint:** `POST /upload_documents.php`

| Parameter | Location | Values | Required |
|-----------|----------|--------|----------|
| `ref` | Query string | Registration reference (e.g. `EXPOBETON-2026-69D53D4`) | ✅ Yes |
| `type` | Query string | `logo` or `passport` | ✅ Yes |
| `file` | `multipart/form-data` body | The actual file | ✅ Yes |

**Example:**
```bash
curl -X POST "https://expobetonrdc.com/upload_documents.php?ref=EXPOBETON-2026-69D53D4&type=logo" \
  -H "Authorization: Bearer ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07" \
  -F "file=@company_logo.png"
```

---

### 3. File Validation Rules

The endpoint enforces strict rules based on document type:

| Rule | Logo | Passport |
|------|------|----------|
| **Allowed extensions** | `jpg`, `jpeg`, `png`, `gif`, `svg` | `pdf` only |
| **Max file size** | 10 MB | 10 MB |
| **Storage path** | `uploads/logo_713_1712534400.png` | `uploads/passport_713_1712534400.pdf` |

```php
if ($type === 'logo') {
    $allowedExt = ['jpg', 'jpeg', 'png', 'gif', 'svg'];
    $maxSize = 10 * 1024 * 1024;  // 10MB
} else {
    $allowedExt = ['pdf'];
    $maxSize = 10 * 1024 * 1024;
}
```

---

### 4. Database Linkage (How Files Connect to Registrations)

The key is the **reference number** passed from Step 1 to Step 2:

```php
// 1. Look up registration by reference
$registration = $registrationModel->getByReference($ref);
$registrationId = $registration['id'];  // e.g., 713

// 2. Save file with unique name
$storedName = $type . '_' . $registrationId . '_' . time() . '.png';
// → e.g., "logo_713_1712534400.png"

// 3. Insert into eb_documents table
$documentModel->create([
    'entity_type'   => 'registration',   // Links to eb_registrations
    'entity_id'     => $registrationId,  // The registration's primary key (713)
    'document_type' => 'logo',           // 'logo' or 'passport'
    'original_name' => 'company_logo.png',
    'stored_name'   => 'logo_713_1712534400.png',
    'file_path'     => 'uploads/logo_713_1712534400.png',
    'mime_type'     => 'image/png',
    'file_size'     => 245678,
]);
```

The `eb_documents` table uses a **polymorphic relationship**:

```sql
entity_type = 'registration'  -- or 'ambassador'
entity_id   = 713             -- links to eb_registrations.id
```

---

### 5. Storage Location and Naming

| Item | Value |
|------|-------|
| **Directory** | `/public_html/uploads/` |
| **Naming pattern** | `{type}_{registration_id}_{unix_timestamp}.{ext}` |
| **Example** | `logo_713_1712534400.png` |
| **DB path stored** | `uploads/logo_713_1712534400.png` |

The name includes the `registration_id` to prevent collisions and allow direct lookups.

---

### 6. Admin Panel Integration

In [/admin/registrations.php](file:///f:/Louison/Layhosting/Clients/Expo%20beton/web/admin/registrations.php#L81-L89), the admin panel fetches linked documents:

```php
// When viewing a registration detail
if (isset($_GET['view'])) {
    $selectedReg = $registrationModel->getById((int)$_GET['view']);
    $selectedDocs = $documentModel->getByEntity('registration', $selectedReg['id']);
    // $selectedDocs contains logo + passport files for that registration
}
```

The admin dashboard shows document indicators in the registration table:

```php
// Each registration row shows document status
(SELECT COUNT(*) FROM eb_documents d 
 WHERE d.entity_type = 'registration' AND d.entity_id = r.id AND d.document_type = 'logo') 
 AS has_logo
```

---

### 7. Complete Chatbot Sequence

```
User: "I want to register as a Gold sponsor"
                    ↓
Chatbot: Collects company, contact, email, phone, country, city
                    ↓
Rasa Action: action_submit_registration()
  POST /api_chatbot_register.php?action=register
  {
    "company": "Acme Corp",
    "contact_name": "Jean Dupont",
    "email": "jean@acme.com",
    "phone": "+243812345678",
    "country": "CD",
    "city": "Kinshasa",
    "category": "Gold",
    "payment": "Veuillez Facturer",
    "visa": "oui",
    "history": "oui"
  }
                    ↓
  API Response:
  {
    "success": true,
    "data": {
      "reference": "EXPOBETON-2026-69D53D4",
      "id": 713,
      "status": "pending"
    }
  }
                    ↓
Chatbot: "Your reference is EXPOBETON-2026-69D53D4. Please upload your company logo."
                    ↓
User: Uploads logo file
                    ↓
Rasa Action: ExpoBetonAPI.upload_document()
  POST /upload_documents.php?ref=EXPOBETON-2026-69D53D4&type=logo
  Body: multipart/form-data with logo file
                    ↓
  API Response:
  {
    "success": true,
    "data": {
      "document_id": 142,
      "reference": "EXPOBETON-2026-69D53D4",
      "type": "logo",
      "original_name": "acme_logo.png"
    }
  }
                    ↓
(If visa=oui) → Repeat for passport with type=passport
                    ↓
Admin panel at /admin/registrations.php?view=713
→ Shows registration details + linked logo + passport
```

---

### 8. Python Action Server Integration

In [actions_expobeton.py](file:///f:/Louison/Layhosting/Clients/Expo%20beton/web/chatbot_integration/actions_expobeton.py), the upload would be handled in a separate action:

```python
class ActionUploadDocument(Action):
    def name(self) -> Text:
        return "action_upload_document"

    def run(self, dispatcher, tracker, domain):
        # After registration, bot prompts for documents
        ref = tracker.get_slot("registration_reference")
        doc_type = tracker.get_slot("doc_type_requested")  # 'logo' or 'passport'
        file_path = tracker.get_slot("uploaded_file_path")
        
        files = {'file': open(file_path, 'rb')}
        data = {'ref': ref, 'type': doc_type}
        headers = {
            "Authorization": f"Bearer {EXPOBETON_API_KEY}",
            "User-Agent": "RasaChatbot/1.0 ExpoBeton"
        }
        
        r = requests.post(
            f"{EXPOBETON_API_URL.replace('register', 'upload')}",
            files=files, data=data, headers=headers
        )
```

The current action server file only handles registration submission — the document upload action would need to be added based on your Rasa chatbot's file handling implementation.