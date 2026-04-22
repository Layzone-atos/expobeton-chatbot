<?php
/**
 * ExpoBeton RDC - Chatbot Analytics Dashboard Configuration
 * 
 * IMPORTANT: Update the database credentials below after creating
 * the MySQL database on your cPanel.
 */

// ============================================================
// DATABASE CONFIGURATION
// ============================================================
// Update these values after creating the database in cPanel:
//   1. Go to cPanel > MySQL Databases
//   2. Create database: chatbot_analytics
//   3. Create user: chatbot_api (with strong password)
//   4. Add user to database with ALL PRIVILEGES
define('DB_HOST', 'localhost');
define('DB_NAME', 'expobetonrdc_admincb');
define('DB_USER', 'expobetonrdc_admincb');
define('DB_PASS', '5NOLnwx&WPbS');

// ============================================================
// API AUTHENTICATION
// ============================================================
// Must match EXPOBETON_API_KEY in your Railway .env file
define('API_KEY', 'ebx-rasa-2026-kAlEmIe-be96bac9f905b106ed2b941dfe536b07');

// ============================================================
// APPLICATION SETTINGS
// ============================================================
define('APP_NAME', 'ExpoBeton Chatbot Dashboard');
define('APP_VERSION', '1.0.0');
define('ITEMS_PER_PAGE', 25);
define('SESSION_TIMEOUT', 3600); // 1 hour in seconds

// Timezone
date_default_timezone_set('Africa/Lubumbashi');

// ============================================================
// COUNTRY FLAG HELPER (uses flagcdn.com images for Windows compatibility)
// ============================================================
// Maps country names to ISO 3166-1 alpha-2 codes for flag images
function getCountryCode($countryName) {
    static $map = [
        // French names
        'Afrique du Sud' => 'za', 'Afghanistan' => 'af', 'Albanie' => 'al', 'Algérie' => 'dz',
        'Allemagne' => 'de', 'Andorre' => 'ad', 'Angola' => 'ao', 'Arabie Saoudite' => 'sa',
        'Argentine' => 'ar', 'Arménie' => 'am', 'Australie' => 'au', 'Autriche' => 'at',
        'Azerbaïdjan' => 'az', 'Bahamas' => 'bs', 'Bahreïn' => 'bh', 'Bangladesh' => 'bd',
        'Belgique' => 'be', 'Bénin' => 'bj', 'Biélorussie' => 'by', 'Bolivie' => 'bo',
        'Bosnie-Herzégovine' => 'ba', 'Botswana' => 'bw', 'Brésil' => 'br', 'Burkina Faso' => 'bf',
        'Burundi' => 'bi', 'Cambodge' => 'kh', 'Cameroun' => 'cm', 'Canada' => 'ca',
        'Chili' => 'cl', 'Chine' => 'cn', 'Chypre' => 'cy', 'Colombie' => 'co',
        'Comores' => 'km', 'Congo' => 'cg', 'Corée du Nord' => 'kp', 'Corée du Sud' => 'kr',
        'Costa Rica' => 'cr', "Côte d'Ivoire" => 'ci', 'Croatie' => 'hr', 'Cuba' => 'cu',
        'Danemark' => 'dk', 'Djibouti' => 'dj', 'Égypte' => 'eg', 'Émirats arabes unis' => 'ae',
        'Équateur' => 'ec', 'Érythrée' => 'er', 'Espagne' => 'es', 'Estonie' => 'ee',
        'États-Unis' => 'us', 'Éthiopie' => 'et', 'Fidji' => 'fj', 'Finlande' => 'fi',
        'France' => 'fr', 'Gabon' => 'ga', 'Gambie' => 'gm', 'Géorgie' => 'ge',
        'Ghana' => 'gh', 'Grèce' => 'gr', 'Guatemala' => 'gt', 'Guinée' => 'gn',
        'Guinée équatoriale' => 'gq', 'Guinée-Bissau' => 'gw', 'Haïti' => 'ht',
        'Honduras' => 'hn', 'Hongrie' => 'hu', 'Inde' => 'in', 'Indonésie' => 'id',
        'Irak' => 'iq', 'Iran' => 'ir', 'Irlande' => 'ie', 'Islande' => 'is',
        'Israël' => 'il', 'Italie' => 'it', 'Jamaïque' => 'jm', 'Japon' => 'jp',
        'Jordanie' => 'jo', 'Kazakhstan' => 'kz', 'Kenya' => 'ke', 'Kirghizistan' => 'kg',
        'Koweït' => 'kw', 'Laos' => 'la', 'Lesotho' => 'ls', 'Lettonie' => 'lv',
        'Liban' => 'lb', 'Liberia' => 'lr', 'Liechtenstein' => 'li', 'Libye' => 'ly',
        'Lituanie' => 'lt', 'Luxembourg' => 'lu', 'Madagascar' => 'mg', 'Malaisie' => 'my',
        'Malawi' => 'mw', 'Maldives' => 'mv', 'Mali' => 'ml', 'Malte' => 'mt',
        'Maroc' => 'ma', 'Maurice' => 'mu', 'Mauritanie' => 'mr', 'Mexique' => 'mx',
        'Moldavie' => 'md', 'Monaco' => 'mc', 'Mongolie' => 'mn', 'Monténégro' => 'me',
        'Mozambique' => 'mz', 'Myanmar' => 'mm', 'Namibie' => 'na', 'Népal' => 'np',
        'Nicaragua' => 'ni', 'Niger' => 'ne', 'Nigeria' => 'ng', 'Norvège' => 'no',
        'Nouvelle-Zélande' => 'nz', 'Oman' => 'om', 'Ouganda' => 'ug', 'Ouzbékistan' => 'uz',
        'Pakistan' => 'pk', 'Panama' => 'pa', 'Papouasie-Nouvelle-Guinée' => 'pg',
        'Paraguay' => 'py', 'Pays-Bas' => 'nl', 'Pérou' => 'pe', 'Philippines' => 'ph',
        'Pologne' => 'pl', 'Portugal' => 'pt', 'Qatar' => 'qa',
        'République Centrafricaine' => 'cf', 'République Démocratique du Congo' => 'cd',
        'République Dominicaine' => 'do', 'République Tchèque' => 'cz',
        'Roumanie' => 'ro', 'Royaume-Uni' => 'gb', 'Russie' => 'ru', 'Rwanda' => 'rw',
        'Salvador' => 'sv', 'São Tomé-et-Príncipe' => 'st', 'Sénégal' => 'sn',
        'Serbie' => 'rs', 'Seychelles' => 'sc', 'Sierra Leone' => 'sl', 'Singapour' => 'sg',
        'Slovaquie' => 'sk', 'Slovénie' => 'si', 'Somalie' => 'so', 'Soudan' => 'sd',
        'Soudan du Sud' => 'ss', 'Sri Lanka' => 'lk', 'Suède' => 'se', 'Suisse' => 'ch',
        'Suriname' => 'sr', 'Syrie' => 'sy', 'Tadjikistan' => 'tj', 'Taïwan' => 'tw',
        'Tanzanie' => 'tz', 'Tchad' => 'td', 'Thaïlande' => 'th', 'Togo' => 'tg',
        'Trinité-et-Tobago' => 'tt', 'Tunisie' => 'tn', 'Turkménistan' => 'tm',
        'Turquie' => 'tr', 'Ukraine' => 'ua', 'Uruguay' => 'uy', 'Venezuela' => 've',
        'Vietnam' => 'vn', 'Yémen' => 'ye', 'Zambie' => 'zm', 'Zimbabwe' => 'zw',
        // English names from ip-api.com geolocation
        'South Africa' => 'za', 'Algeria' => 'dz', 'Germany' => 'de', 'Saudi Arabia' => 'sa',
        'Australia' => 'au', 'Austria' => 'at', 'Belgium' => 'be', 'Brazil' => 'br',
        'Cameroon' => 'cm', 'China' => 'cn', 'Colombia' => 'co', 'South Korea' => 'kr',
        'Denmark' => 'dk', 'Egypt' => 'eg', 'United Arab Emirates' => 'ae', 'Spain' => 'es',
        'United States' => 'us', 'Ethiopia' => 'et', 'Finland' => 'fi',
        'Ghana' => 'gh', 'Greece' => 'gr', 'Guinea' => 'gn', 'India' => 'in',
        'Indonesia' => 'id', 'Ireland' => 'ie', 'Italy' => 'it', 'Japan' => 'jp',
        'Kenya' => 'ke', 'Morocco' => 'ma', 'Mexico' => 'mx', 'Nigeria' => 'ng',
        'Norway' => 'no', 'Netherlands' => 'nl', 'Pakistan' => 'pk', 'Philippines' => 'ph',
        'Poland' => 'pl', 'Portugal' => 'pt',
        'Democratic Republic of the Congo' => 'cd', 'Congo (DRC)' => 'cd',
        'Republic of the Congo' => 'cg', 'Congo' => 'cg',
        'Romania' => 'ro', 'United Kingdom' => 'gb', 'Russia' => 'ru', 'Rwanda' => 'rw',
        'Senegal' => 'sn', 'Singapore' => 'sg', 'Sweden' => 'se', 'Switzerland' => 'ch',
        'Tunisia' => 'tn', 'Turkey' => 'tr', 'Ukraine' => 'ua',
        'Canada' => 'ca', 'France' => 'fr', 'Japan' => 'jp',
        'Ivory Coast' => 'ci', 'Czech Republic' => 'cz', 'New Zealand' => 'nz',
    ];
    return $map[$countryName] ?? null;
}

// Format country with flag image for display (uses flagcdn.com for Windows compatibility)
function formatCountryWithFlag($countryName) {
    if (!$countryName || $countryName === '-' || $countryName === 'Unknown' || $countryName === 'Local') {
        return '<span class="text-muted">-</span>';
    }
    $code = getCountryCode($countryName);
    $escaped = htmlspecialchars($countryName);
    if ($code) {
        return '<img src="https://flagcdn.com/w20/' . $code . '.png" alt="' . $escaped . '" style="width:20px;height:15px;margin-right:6px;border:1px solid #ddd;border-radius:2px;vertical-align:middle;">' . $escaped;
    }
    return $escaped;
}
