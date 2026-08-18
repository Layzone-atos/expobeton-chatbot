import re

# Comprehensive country list with full French names, ISO codes, and flag codes
# Sorted alphabetically by French name
countries = [
    ('ZA', 'Afrique du Sud', 'za'),
    ('AF', 'Afghanistan', 'af'),
    ('AL', 'Albanie', 'al'),
    ('DZ', 'Algérie', 'dz'),
    ('DE', 'Allemagne', 'de'),
    ('AD', 'Andorre', 'ad'),
    ('AO', 'Angola', 'ao'),
    ('SA', 'Arabie Saoudite', 'sa'),
    ('AR', 'Argentine', 'ar'),
    ('AM', 'Arménie', 'am'),
    ('AU', 'Australie', 'au'),
    ('AT', 'Autriche', 'at'),
    ('AZ', 'Azerbaïdjan', 'az'),
    ('BS', 'Bahamas', 'bs'),
    ('BH', 'Bahreïn', 'bh'),
    ('BD', 'Bangladesh', 'bd'),
    ('BE', 'Belgique', 'be'),
    ('BJ', 'Bénin', 'bj'),
    ('BY', 'Biélorussie', 'by'),
    ('BO', 'Bolivie', 'bo'),
    ('BA', 'Bosnie-Herzégovine', 'ba'),
    ('BW', 'Botswana', 'bw'),
    ('BR', 'Brésil', 'br'),
    ('BF', 'Burkina Faso', 'bf'),
    ('BI', 'Burundi', 'bi'),
    ('KH', 'Cambodge', 'kh'),
    ('CM', 'Cameroun', 'cm'),
    ('CA', 'Canada', 'ca'),
    ('CL', 'Chili', 'cl'),
    ('CN', 'Chine', 'cn'),
    ('CY', 'Chypre', 'cy'),
    ('CO', 'Colombie', 'co'),
    ('KM', 'Comores', 'km'),
    ('CG', 'Congo', 'cg'),
    ('KP', 'Corée du Nord', 'kp'),
    ('KR', 'Corée du Sud', 'kr'),
    ('CR', 'Costa Rica', 'cr'),
    ('CI', "Côte d'Ivoire", 'ci'),
    ('HR', 'Croatie', 'hr'),
    ('CU', 'Cuba', 'cu'),
    ('DK', 'Danemark', 'dk'),
    ('DJ', 'Djibouti', 'dj'),
    ('EG', 'Égypte', 'eg'),
    ('AE', 'Émirats arabes unis', 'ae'),
    ('EC', 'Équateur', 'ec'),
    ('ER', 'Érythrée', 'er'),
    ('ES', 'Espagne', 'es'),
    ('EE', 'Estonie', 'ee'),
    ('US', 'États-Unis', 'us'),
    ('ET', 'Éthiopie', 'et'),
    ('FJ', 'Fidji', 'fj'),
    ('FI', 'Finlande', 'fi'),
    ('FR', 'France', 'fr'),
    ('GA', 'Gabon', 'ga'),
    ('GM', 'Gambie', 'gm'),
    ('GE', 'Géorgie', 'ge'),
    ('GH', 'Ghana', 'gh'),
    ('GR', 'Grèce', 'gr'),
    ('GT', 'Guatemala', 'gt'),
    ('GN', 'Guinée', 'gn'),
    ('GQ', 'Guinée équatoriale', 'gq'),
    ('GW', 'Guinée-Bissau', 'gw'),
    ('HT', 'Haïti', 'ht'),
    ('HN', 'Honduras', 'hn'),
    ('HU', 'Hongrie', 'hu'),
    ('IN', 'Inde', 'in'),
    ('ID', 'Indonésie', 'id'),
    ('IQ', 'Irak', 'iq'),
    ('IR', 'Iran', 'ir'),
    ('IE', 'Irlande', 'ie'),
    ('IS', 'Islande', 'is'),
    ('IL', 'Israël', 'il'),
    ('IT', 'Italie', 'it'),
    ('JM', 'Jamaïque', 'jm'),
    ('JP', 'Japon', 'jp'),
    ('JO', 'Jordanie', 'jo'),
    ('KZ', 'Kazakhstan', 'kz'),
    ('KE', 'Kenya', 'ke'),
    ('KG', 'Kirghizistan', 'kg'),
    ('KW', 'Koweït', 'kw'),
    ('LA', 'Laos', 'la'),
    ('LS', 'Lesotho', 'ls'),
    ('LV', 'Lettonie', 'lv'),
    ('LB', 'Liban', 'lb'),
    ('LR', 'Liberia', 'lr'),
    ('LI', 'Liechtenstein', 'li'),
    ('LY', 'Libye', 'ly'),
    ('LT', 'Lituanie', 'lt'),
    ('LU', 'Luxembourg', 'lu'),
    ('MG', 'Madagascar', 'mg'),
    ('MY', 'Malaisie', 'my'),
    ('MW', 'Malawi', 'mw'),
    ('MV', 'Maldives', 'mv'),
    ('ML', 'Mali', 'ml'),
    ('MT', 'Malte', 'mt'),
    ('MA', 'Maroc', 'ma'),
    ('MU', 'Maurice', 'mu'),
    ('MR', 'Mauritanie', 'mr'),
    ('MX', 'Mexique', 'mx'),
    ('MD', 'Moldavie', 'md'),
    ('MC', 'Monaco', 'mc'),
    ('MN', 'Mongolie', 'mn'),
    ('ME', 'Monténégro', 'me'),
    ('MZ', 'Mozambique', 'mz'),
    ('MM', 'Myanmar', 'mm'),
    ('NA', 'Namibie', 'na'),
    ('NP', 'Népal', 'np'),
    ('NI', 'Nicaragua', 'ni'),
    ('NE', 'Niger', 'ne'),
    ('NG', 'Nigeria', 'ng'),
    ('NO', 'Norvège', 'no'),
    ('NZ', 'Nouvelle-Zélande', 'nz'),
    ('OM', 'Oman', 'om'),
    ('UG', 'Ouganda', 'ug'),
    ('UZ', 'Ouzbékistan', 'uz'),
    ('PK', 'Pakistan', 'pk'),
    ('PA', 'Panama', 'pa'),
    ('PG', 'Papouasie-Nouvelle-Guinée', 'pg'),
    ('PY', 'Paraguay', 'py'),
    ('NL', 'Pays-Bas', 'nl'),
    ('PE', 'Pérou', 'pe'),
    ('PH', 'Philippines', 'ph'),
    ('PL', 'Pologne', 'pl'),
    ('PT', 'Portugal', 'pt'),
    ('QA', 'Qatar', 'qa'),
    ('CD', 'République Démocratique du Congo', 'cd'),
    ('CF', 'République Centrafricaine', 'cf'),
    ('DO', 'République Dominicaine', 'do'),
    ('CZ', 'République Tchèque', 'cz'),
    ('RO', 'Roumanie', 'ro'),
    ('GB', 'Royaume-Uni', 'gb'),
    ('RU', 'Russie', 'ru'),
    ('RW', 'Rwanda', 'rw'),
    ('SV', 'Salvador', 'sv'),
    ('ST', 'São Tomé-et-Príncipe', 'st'),
    ('SN', 'Sénégal', 'sn'),
    ('RS', 'Serbie', 'rs'),
    ('SC', 'Seychelles', 'sc'),
    ('SL', 'Sierra Leone', 'sl'),
    ('SG', 'Singapour', 'sg'),
    ('SK', 'Slovaquie', 'sk'),
    ('SI', 'Slovénie', 'si'),
    ('SO', 'Somalie', 'so'),
    ('SD', 'Soudan', 'sd'),
    ('SS', 'Soudan du Sud', 'ss'),
    ('LK', 'Sri Lanka', 'lk'),
    ('SE', 'Suède', 'se'),
    ('CH', 'Suisse', 'ch'),
    ('SR', 'Suriname', 'sr'),
    ('SY', 'Syrie', 'sy'),
    ('TJ', 'Tadjikistan', 'tj'),
    ('TW', 'Taïwan', 'tw'),
    ('TZ', 'Tanzanie', 'tz'),
    ('TD', 'Tchad', 'td'),
    ('TH', 'Thaïlande', 'th'),
    ('TG', 'Togo', 'tg'),
    ('TT', 'Trinité-et-Tobago', 'tt'),
    ('TN', 'Tunisie', 'tn'),
    ('TM', 'Turkménistan', 'tm'),
    ('TR', 'Turquie', 'tr'),
    ('UA', 'Ukraine', 'ua'),
    ('UY', 'Uruguay', 'uy'),
    ('VE', 'Venezuela', 've'),
    ('VN', 'Vietnam', 'vn'),
    ('YE', 'Yémen', 'ye'),
    ('ZM', 'Zambie', 'zm'),
    ('ZW', 'Zimbabwe', 'zw'),
]

# Phone prefixes (with FULL country names in French)
phone_prefixes = [
    ('CD', 'République Démocratique du Congo', '+243', 'cd'),
    ('FR', 'France', '+33', 'fr'),
    ('BE', 'Belgique', '+32', 'be'),
    ('US', 'États-Unis', '+1', 'us'),
    ('CA', 'Canada', '+1', 'ca'),
    ('CH', 'Suisse', '+41', 'ch'),
    ('GB', 'Royaume-Uni', '+44', 'gb'),
    ('DE', 'Allemagne', '+49', 'de'),
    ('ZA', 'Afrique du Sud', '+27', 'za'),
    ('SN', 'Sénégal', '+221', 'sn'),
    ('CI', "Côte d'Ivoire", '+225', 'ci'),
    ('CM', 'Cameroun', '+237', 'cm'),
    ('TG', 'Togo', '+228', 'tg'),
    ('BJ', 'Bénin', '+229', 'bj'),
    ('ML', 'Mali', '+223', 'ml'),
    ('BF', 'Burkina Faso', '+226', 'bf'),
    ('GN', 'Guinée', '+224', 'gn'),
    ('NE', 'Niger', '+227', 'ne'),
    ('TN', 'Tunisie', '+216', 'tn'),
    ('MA', 'Maroc', '+212', 'ma'),
    ('DZ', 'Algérie', '+213', 'dz'),
    ('EG', 'Égypte', '+20', 'eg'),
    ('KE', 'Kenya', '+254', 'ke'),
    ('NG', 'Nigeria', '+234', 'ng'),
    ('GH', 'Ghana', '+233', 'gh'),
    ('ET', 'Éthiopie', '+251', 'et'),
    ('RW', 'Rwanda', '+250', 'rw'),
    ('TZ', 'Tanzanie', '+255', 'tz'),
    ('UG', 'Ouganda', '+256', 'ug'),
    ('AO', 'Angola', '+244', 'ao'),
    ('CG', 'Congo', '+242', 'cg'),
    ('GA', 'Gabon', '+241', 'ga'),
    ('IT', 'Italie', '+39', 'it'),
    ('ES', 'Espagne', '+34', 'es'),
    ('PT', 'Portugal', '+351', 'pt'),
    ('NL', 'Pays-Bas', '+31', 'nl'),
    ('RU', 'Russie', '+7', 'ru'),
    ('CN', 'Chine', '+86', 'cn'),
    ('IN', 'Inde', '+91', 'in'),
    ('JP', 'Japon', '+81', 'jp'),
    ('BR', 'Brésil', '+55', 'br'),
    ('MX', 'Mexique', '+52', 'mx'),
    ('AU', 'Australie', '+61', 'au'),
    ('AE', 'Émirats arabes unis', '+971', 'ae'),
    ('SA', 'Arabie Saoudite', '+966', 'sa'),
    ('TR', 'Turquie', '+90', 'tr'),
    ('ZM', 'Zambie', '+260', 'zm'),
    ('ZW', 'Zimbabwe', '+263', 'zw'),
    ('MG', 'Madagascar', '+261', 'mg'),
    ('MZ', 'Mozambique', '+258', 'mz'),
]
phone_prefixes.sort(key=lambda x: x[1])

# Read the file
with open('chatbot_integration/form_mstep.js', encoding='utf-8') as f:
    content = f.read()

# Build new countries array content
lines = []
lines.append("  function loadCountriesWithFlags() {")
lines.append("    var select = $(\"select[name='country']\");")
lines.append("    ")
lines.append("    // Liste complète des pays avec codes de drapeaux (170+ pays en français)")
lines.append("    var countries = [")
for code, name, flag in countries:
    escaped_name = name.replace("'", "\\'")
    lines.append(f"      {{code: '{code}', name: '{escaped_name}', flag: '{flag}'}},")
# Remove trailing comma from last entry
lines[-1] = lines[-1].rstrip(',')
lines.append("    ];")
lines.append("")
lines.append("    // Trier les pays par ordre alphabétique")
lines.append("    countries.sort(function(a, b) {")
lines.append("      return a.name.localeCompare(b.name, 'fr');")
lines.append("    });")
lines.append("")
lines.append("    // Vider le select d'abord")
lines.append("    select.empty();")
lines.append("")
lines.append("    // Ajouter l'option par défaut")
lines.append("    select.append($(\"<option></option>\").attr(\"value\", \"\").text(\"Sélectionnez un pays\"));")
lines.append("")
lines.append("    // Ajouter les pays avec drapeaux")
lines.append("    $.each(countries, function(index, country) {")
lines.append("      var option = $(\"<option></option>\")")
lines.append("        .attr(\"value\", country.code)")
lines.append("        .text(country.name)")
lines.append("        .attr('data-flag', country.flag);")
lines.append("      ")
lines.append("      select.append(option);")
lines.append("    });")
lines.append("")
lines.append("    // Initialiser Select2 avec formatage des drapeaux")
lines.append("    select.select2({")
lines.append("      placeholder: \"Cliquez ici pour choisir un pays\",")
lines.append("      allowClear: true,")
lines.append("      width: '100%',")
lines.append("      templateResult: formatCountry,")
lines.append("      templateSelection: formatCountrySelection,")
lines.append("      escapeMarkup: function(m) { return m; }")
lines.append("    });")
lines.append("  }")

new_load_countries = "\n".join(lines)

# Build new phone prefixes array content
prefix_lines = []
prefix_lines.append("  function loadPhonePrefixes() {")
prefix_lines.append("    var select = $(\"select[name='prefix']\");")
prefix_lines.append("    ")
prefix_lines.append("    // Liste des pays avec codes de drapeaux et préfixes téléphoniques (noms complets)")
prefix_lines.append("    var countriesWithPrefixes = [")
for code, name, prefix, flag in phone_prefixes:
    escaped_name = name.replace("'", "\\'")
    prefix_lines.append(f"        {{code: '{code}', name: '{escaped_name}', prefix: '{prefix}', flag: '{flag}'}},")
prefix_lines[-1] = prefix_lines[-1].rstrip(',')
prefix_lines.append("    ];")
prefix_lines.append("")
prefix_lines.append("    // Trier les pays par ordre alphabétique du nom")
prefix_lines.append("    countriesWithPrefixes.sort(function(a, b) {")
prefix_lines.append("        return a.name.localeCompare(b.name, 'fr');")
prefix_lines.append("    });")
prefix_lines.append("")
prefix_lines.append("    // Vider le select d'abord")
prefix_lines.append("    select.empty();")
prefix_lines.append("")
prefix_lines.append("    // Ajouter l'option par défaut")
prefix_lines.append("    select.append($(\"<option></option>\").attr(\"value\", \"\").text(\"Choisir le pays\"));")
prefix_lines.append("")
prefix_lines.append("    // Ajouter les pays avec drapeaux et préfixes")
prefix_lines.append("    $.each(countriesWithPrefixes, function(index, country) {")
prefix_lines.append("        var option = $(\"<option></option>\")")
prefix_lines.append("            .attr(\"value\", country.prefix)")
prefix_lines.append("            .text(country.prefix + \" - \" + country.name)")
prefix_lines.append("            .attr('data-flag', country.flag)")
prefix_lines.append("            .attr('data-country', country.name)")
prefix_lines.append("            .attr('data-prefix', country.prefix);")
prefix_lines.append("        ")
prefix_lines.append("        select.append(option);")
prefix_lines.append("    });")
prefix_lines.append("")
prefix_lines.append("    // Initialiser Select2 avec formatage des drapeaux")
prefix_lines.append("    select.select2({")
prefix_lines.append("        placeholder: \"Choisir le pays\",")
prefix_lines.append("        allowClear: false,")
prefix_lines.append("        width: '140px',")
prefix_lines.append("        templateResult: formatPhonePrefixWithFlag,")
prefix_lines.append("        templateSelection: formatPhonePrefixSelectionWithFlag,")
prefix_lines.append("        escapeMarkup: function(m) { return m; },")
prefix_lines.append("        minimumResultsForSearch: 5,")
prefix_lines.append("        dropdownCssClass: 'select2-container--prefix'")
prefix_lines.append("    });")
prefix_lines.append("")
prefix_lines.append("    // Sélectionner la RDC par défaut")
prefix_lines.append("    select.val('+243').trigger('change');")
prefix_lines.append("  }")

new_load_prefixes = "\n".join(prefix_lines)

# Find and replace the loadCountriesWithFlags function
pattern_countries = r'  function loadCountriesWithFlags\(\).*?(?=\n  // Formater l)'
content = re.sub(pattern_countries, new_load_countries + '\n\n', content, flags=re.DOTALL)

# Find and replace the loadPhonePrefixes function
pattern_prefixes = r'  function loadPhonePrefixes\(\).*?(?=\n  // Formater l\'affichage des préfixes)'
content = re.sub(pattern_prefixes, new_load_prefixes + '\n\n', content, flags=re.DOTALL)

with open('chatbot_integration/form_mstep.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Countries:", len(countries), "| Prefixes:", len(phone_prefixes))

# Verify
c = open('chatbot_integration/form_mstep.js', encoding='utf-8').read()
print("Has Burkina Faso:", 'Burkina Faso' in c)
print("Has Zimbabwe:", 'Zimbabwe' in c)
print("Has full name RDC:", "République Démocratique du Congo" in c)
print("Has full Ivory Coast:", "Côte d'Ivoire" in c)
print("Total lines:", len(c.splitlines()))
