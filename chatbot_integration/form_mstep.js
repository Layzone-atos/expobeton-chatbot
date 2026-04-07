$(document).ready(function(){
  console.log('🚀 Démarrage du formulaire multi-étapes');
  
  // Vérifier SweetAlert
  if (typeof Swal === 'undefined') {
    console.error('❌ SweetAlert non détecté ! Vérifiez que la librairie est chargée.');
    // Fallback sans SweetAlert
    window.showSuccessMessage = function(data) {
      alert('Félicitations ! Votre inscription a été enregistrée avec succès.\nRéférence: ' + (data.reference || 'N/A'));
      resetForm();
    };
  } else {
    console.log('✅ SweetAlert détecté, version:', Swal.version || 'inconnue');
  }
  
  // Fonction de test pour le popup (utilisable dans la console)
  window.testSuccessPopup = function() {
    console.log('🧪 Test de la modal de succès personnalisée');
    showSuccessMessage({
      company: 'Test Société',
      reference: 'TEST-2025-123456'
    });
  };
  
  // Fonction de debug pour forcer la fermeture
  window.forceCloseModal = function() {
    console.log('🔧 Fermeture forcée de toutes les modals');
    $('#success-modal').remove();
    $('.swal2-container').remove();
    resetForm();
  };
  
  // === INITIALISATION ANTI-SPAM ===
  $('#form_timestamp').val(Math.floor(Date.now() / 1000));
  console.log('✅ Timestamp anti-spam initialisé:', $('#form_timestamp').val());
  
  // Vérifier que le formulaire principal existe
  if ($('#msform').length === 0) {
    console.error('❌ Formulaire #msform introuvable !');
    return;
  }
  
  console.log('✅ Formulaire principal détecté');
  
  // Stockage des références des fichiers uploadés
  window.uploadedFiles = {
    logo: null,
    passport: null
  };

  // ---------------------------
  // Variables globales
  // ---------------------------
  var current_fs, next_fs, previous_fs;
  var current = 1;
  // Count only non-conditional fieldsets for base progress (6 steps: etape1-6)
  // Conditional steps will adjust dynamically
  var steps = $("fieldset").not('.conditional-step').length;

  // Initialisation - Afficher seulement le premier fieldset
  $("fieldset").hide();
  $("fieldset[data-step='etape1']").show();
  
  // Masquer toutes les étapes conditionnelles au début
  hideAllConditionalSteps();
  
  // S'assurer que TOUTES les étapes conditionnelles sont complètement masquées
  $("fieldset.conditional-step").removeClass('active-step').hide();
  
  // Activer le premier point de la progressbar
  $("#progressbar li#etape1").addClass("active");
  
  console.log('✅ Formulaire initialisé - Étape 1 affichée');
  
  setProgressBar(current);

  // ---------------------------
  // Gestion des étapes conditionnelles
  // ---------------------------
  function hideAllConditionalSteps() {
    console.log('🔧 Masquage de toutes les étapes conditionnelles');
    // Masquer les fieldsets conditionnels en retirant la classe 'active-step'
    $('fieldset.conditional-step').removeClass('active-step');
    // Masquer les éléments de progressbar conditionnels
    $('#progressbar li.conditional-step').hide();
  }

  function showStepsForCategory(categoryType) {
    console.log('🔧 Configuration des étapes pour:', categoryType);
    hideAllConditionalSteps();
    
    // NE PAS rendre les étapes visibles - juste configurer la progressbar
    if (categoryType === 'sponsor') {
      // Sponsor : étapes 6b, 7, 8, 9, 10, 11 (6 base + 6 conditional = 12)
      $('#progressbar li#etape6b, #progressbar li#etape7, #progressbar li#etape8, #progressbar li#etape9, #progressbar li#etape10, #progressbar li#etape11').show();
      steps = 12;
      console.log('✅ Étapes sponsor configurées dans la progressbar');
      
    } else if (categoryType === 'exposant') {
      // Exposant : étapes 6c, 7, 8, 9, 10, 11 (6 base + 6 conditional = 12)
      $('#progressbar li#etape6c, #progressbar li#etape7, #progressbar li#etape8, #progressbar li#etape9, #progressbar li#etape10, #progressbar li#etape11').show();
      steps = 12;
      console.log('✅ Étapes exposant configurées dans la progressbar');
    } else if (categoryType === 'participant') {
      // Participant simple : seulement étape 9 (historique) (6 base + 1 conditional = 7)
      $('#progressbar li#etape9').show();
      steps = 7;
      console.log('✅ Étapes participant configurées dans la progressbar');
    }
  }

  // Écouter les changements de catégorie
  $(document).on('change', 'input[name="category_type"]', function() {
    var selectedCategory = $(this).val();
    console.log('📋 Catégorie sélectionnée:', selectedCategory);
    
    // SEULEMENT configurer la progressbar et la description - PAS d'affichage des étapes
    // La fonction showStepsForCategory sera appelée lors de la navigation depuis etape6
    
    // Mettre à jour la description
    var descriptions = {
      'sponsor': 'En tant que sponsor, vous bénéficierez d\'une visibilité maximale et de nombreux avantages exclusifs.',
      'exposant': 'En tant qu\'exposant, vous disposerez d\'un espace dédié pour présenter vos produits et services.',
      'participant': 'Participation simple aux conférences et événements du salon.'
    };
    $('#category-desc').text(descriptions[selectedCategory] || '');
    
    console.log('✅ Description mise à jour pour:', selectedCategory);
  });

  // ---------------------------
  // Validation améliorée pour le bouton "Suivant"
  // ---------------------------
  $(".next").click(function(){
    var currentStep = $(this).closest("fieldset");
    var currentStepId = currentStep.data("step");
    console.log('🔄 Tentative de navigation depuis:', currentStepId);
    
    var valid = validateStep(currentStep);
    
    if (!valid) {
      console.log('❌ Validation échouée pour étape:', currentStepId);
      return;
    }

    // Logique de navigation conditionnelle
    var nextStepId = getNextStep(currentStepId);
    console.log('➡️ Prochaine étape déterminée:', nextStepId);
    
    if (!nextStepId) {
      console.log('❌ Aucune étape suivante trouvée - arrêt de la navigation');
      // Arrêter la navigation au lieu de créer une boucle
      return;
    }

    // Vérifier que l'étape suivante existe
    var next_fs = $("fieldset[data-step='" + nextStepId + "']");
    if (next_fs.length === 0) {
      console.log('❌ Étape suivante introuvable dans le DOM:', nextStepId);
      return;
    }

    // Si valide → passer à l'étape suivante
    current_fs = currentStep;
    console.log('✅ Navigation vers étape:', nextStepId);

    // Activer le point du progressbar
    $("#progressbar li#" + nextStepId).addClass("active");

    // Animation améliorée
    current_fs.animate({opacity: 0}, {
      duration: 400,
      complete: function() {
        // Masquer l'étape actuelle
        current_fs.hide().removeClass('active-step');
        
        // Afficher la prochaine étape selon son type
        if (next_fs.hasClass('conditional-step')) {
          // Pour les étapes conditionnelles, utiliser la classe active-step
          next_fs.addClass('active-step').show().css({
            'opacity': 1
          });
        } else {
          // Pour les étapes normales, affichage direct
          next_fs.show().css({
            'opacity': 1
          });
        }
        
        console.log('📄 Étape affichée:', nextStepId);
        
        // Si nous arrivons à l'étape 9 (historique), configurer les boutons selon le type
        if (nextStepId === 'etape9') {
          var categoryType = $('input[name="category_type"]:checked').val();
          console.log('📋 Arrivée à l\'étape historique - catégorie:', categoryType);
          setTimeout(function() {
            updateHistoryStepButtons(categoryType);
          }, 100);
        }
        
        // Scroll vers le haut pour une meilleure expérience
        $('html, body').animate({
          scrollTop: $("#msform").offset().top - 50
        }, 500);
      }
    });

    setProgressBar(++current);
  });

  // Fonction pour déterminer l'étape suivante
  function getNextStep(currentStepId) {
    var categoryType = $('input[name="category_type"]:checked').val();
    var visaChoice = $('input[name="visa"]:checked').val();
    
    console.log('🧱 Détermination de l\'\u00e9tape suivante depuis:', currentStepId, '| Catégorie:', categoryType, '| Visa:', visaChoice);
    
    switch(currentStepId) {
      case 'etape1': return 'etape2';
      case 'etape2': return 'etape3';
      case 'etape3': return 'etape4';
      case 'etape4': return 'etape5';
      case 'etape5': return 'etape6';
      case 'etape6':
        console.log('🔄 Navigation depuis étape 6 avec catégorie:', categoryType);
        
        // Vérifier si une catégorie est réellement sélectionnée
        if (!categoryType) {
          console.log('❌ Aucune catégorie sélectionnée - impossible de continuer');
          return null;
        }
        
        // IMPORTANT: Configurer les étapes avant de déterminer la suivante
        showStepsForCategory(categoryType);
        
        if (categoryType === 'sponsor') {
          console.log('➡️ Redirection vers etape6b (sponsor)');
          return 'etape6b';
        }
        if (categoryType === 'exposant') {
          console.log('➡️ Redirection vers etape6c (exposant)');
          return 'etape6c';
        }
        if (categoryType === 'participant') {
          console.log('➡️ Redirection vers etape9 (participant)');
          return 'etape9';
        }
        console.log('❌ Catégorie non reconnue:', categoryType);
        break;
      case 'etape6b': return 'etape7'; // Sponsor → Paiement
      case 'etape6c': return 'etape7'; // Exposant → Paiement
      case 'etape7': return 'etape8'; // Paiement → Visa
      case 'etape8': return 'etape9'; // Visa → Historique
      case 'etape9':
        if (categoryType === 'participant') {
          // Participant simple soumet directement
          console.log('🏁 Participant simple - fin du formulaire');
          return null;
        }
        return 'etape10'; // Sponsor/Exposant → Logo
      case 'etape10':
        // Si visa = oui, aller au passeport, sinon terminer
        if (visaChoice === 'oui') {
          return 'etape11';
        }
        // Pour visa = non, le formulaire se termine à cette étape
        console.log('🏁 Formulaire terminé à etape10 (visa = non)');
        return null; // Terminer
      case 'etape11': return null; // Dernière étape
    }
    return null;
  }

  // ---------------------------
  // Bouton "Précédent"
  // ---------------------------
  $(".previous").click(function(){
    current_fs = $(this).closest("fieldset");
    var currentStepId = current_fs.data("step");
    var previousStepId = getPreviousStep(currentStepId);
    
    if (!previousStepId) return;
    
    previous_fs = $("fieldset[data-step='" + previousStepId + "']");

    // Désactiver le point du progressbar
    $("#progressbar li#" + currentStepId).removeClass("active");

    // Animation améliorée
    current_fs.animate({opacity: 0}, {
      duration: 400,
      complete: function() {
        current_fs.hide().removeClass('active-step');
        
        // Afficher l'étape précédente selon son type
        if (previous_fs.hasClass('conditional-step')) {
          previous_fs.addClass('active-step').show().css({opacity: 1});
        } else {
          previous_fs.show().css({opacity: 1});
        }
        
        // Scroll vers le haut pour une meilleure expérience
        $('html, body').animate({
          scrollTop: $("#msform").offset().top - 50
        }, 500);
      }
    });

    setProgressBar(--current);
  });

  // Fonction pour déterminer l'étape précédente
  function getPreviousStep(currentStepId) {
    var categoryType = $('input[name="category_type"]:checked').val();
    
    switch(currentStepId) {
      case 'etape2': return 'etape1';
      case 'etape3': return 'etape2';
      case 'etape4': return 'etape3';
      case 'etape5': return 'etape4';
      case 'etape6': return 'etape5';
      case 'etape6b': return 'etape6'; // Sponsor
      case 'etape6c': return 'etape6'; // Exposant
      case 'etape7':
        if (categoryType === 'sponsor') return 'etape6b';
        if (categoryType === 'exposant') return 'etape6c';
        break;
      case 'etape8': return 'etape7';
      case 'etape9':
        if (categoryType === 'participant') return 'etape6';
        return 'etape8';
      case 'etape10': return 'etape9';
      case 'etape11': return 'etape10';
    }
    return null;
  }

  // ---------------------------
  // Gestion conditionnelle des boutons à l'étape historique selon le type de participant
  $(document).on('change', 'input[name="category_type"]', function() {
    var categoryType = $(this).val();
    console.log('📋 Changement de catégorie détecté:', categoryType);
    updateHistoryStepButtons(categoryType);
  });
  
  // Fonction pour mettre à jour les boutons de l'étape historique
  function updateHistoryStepButtons(categoryType) {
    console.log('🔧 Mise à jour boutons historique pour:', categoryType);
    
    // Masquer tous les boutons de navigation de l'étape historique d'abord
    $('#next-history, #submit-participant').hide();
    
    if (categoryType === 'participant') {
      // Pour participant simple, afficher seulement le bouton soumettre
      $('#submit-participant').show();
      $('#next-history').hide();
      console.log('✅ Bouton soumission participant affiché (historique)');
    } else if (categoryType === 'sponsor' || categoryType === 'exposant') {
      // Pour sponsor et exposant, afficher seulement le bouton suivant
      $('#next-history').show();
      $('#submit-participant').hide();
      console.log('✅ Bouton suivant affiché pour sponsor/exposant (historique)');
    }
    
    // Si nous sommes actuellement à l'étape historique, appliquer immédiatement
    var currentStep = $('fieldset[data-step="etape9"]');
    if (currentStep.is(':visible')) {
      console.log('📋 Application immédiate - étape historique visible');
      // Les boutons ont déjà été mis à jour ci-dessus
    }
  }

  // Gestion conditionnelle de l'étape passeport selon le choix visa
  $(document).on('change', 'input[name="visa"]', function() {
    var visaChoice = $(this).val();
    
    if (visaChoice === 'oui') {
      $('#etape11').show();
      $('#progressbar #etape11').show();
    } else {
      $('#etape11').hide();
      $('#progressbar #etape11').hide();
    }
    
    // Mettre à jour l'affichage des boutons si nous sommes déjà à l'étape 10
    var currentStep = $('fieldset[data-step="etape10"]');
    if (currentStep.is(':visible')) {
      console.log('🔧 Changement visa à l\'étape 10 - visa:', visaChoice);
      if (visaChoice === 'non') {
        // Masquer le bouton suivant et afficher le bouton de soumission
        currentStep.find('.next').hide();
        console.log('🔧 Visa=non - affichage bouton soumission finale');
        showFinalSubmitButton();
      } else {
        // Afficher le bouton suivant et masquer le bouton de soumission
        console.log('🔧 Visa=oui - affichage bouton suivant');
        currentStep.find('.next').show();
        currentStep.find('.submit-final').hide();
      }
    }
  });

  // ---------------------------
  // Afficher le bouton de soumission finale pour etape10 (visa = non)
  // ---------------------------
  function showFinalSubmitButton() {
    console.log('🔧 showFinalSubmitButton() appelée');
    // Vérifier si nous sommes à l'étape 10
    var currentStep = $('fieldset[data-step="etape10"]');
    if (currentStep.is(':visible')) {
      console.log('✅ Étape 10 visible - configuration boutons');
      // Masquer le bouton "Suivant" s'il existe
      currentStep.find('.next').hide();
      
      // Afficher/créer le bouton de soumission finale s'il n'existe pas déjà
      if (currentStep.find('.submit-final').length === 0) {
        var submitButton = $('<input type="button" name="submit" class="submit submit-final action-button" value="Finaliser l\'inscription" />');
        // Trouver où insérer le bouton - après le dernier bouton existant ou à la fin du fieldset
        var lastButton = currentStep.find('.action-button, .action-button-previous').last();
        if (lastButton.length > 0) {
          lastButton.after(submitButton);
        } else {
          currentStep.append(submitButton);
        }
        console.log('✅ Bouton de soumission finale ajouté à l\'etape10');
      } else {
        currentStep.find('.submit-final').show();
        console.log('✅ Bouton de soumission finale affiché à l\'etape10');
      }
    } else {
      console.log('⚠️ Étape 10 non visible - bouton non ajouté');
    }
  }

  // ---------------------------
  // Fonction de validation d'étape améliorée
  // ---------------------------
  function validateStep(step) {
    var isValid = true;
    var invalidFields = [];
    
    // Réinitialiser les styles d'erreur
    step.find("input, select").removeClass("invalid");
    step.find(".error-message").remove();
    
    // Valider les champs input et select requis
    step.find("input[required], select[required]").each(function() {
      var $field = $(this);
      var fieldName = getFieldName($field);

      // helper to normalize file/input name keys (remove trailing [] )
      function normalizeKey(name) {
        if (!name) return '';
        return name.toString().replace(/\[\]$/, '');
      }

      if ($field.attr("type") === "radio") {
        // Pour les groupes radio
        var name = $field.attr("name");
        var radioGroup = step.find("input[name='" + name + "']");
        if (!radioGroup.is(":checked")) {
          showFieldError(radioGroup.first(), "Veuillez sélectionner une option pour " + fieldName);
          invalidFields.push(fieldName);
          isValid = false;
        }
      // Validation spécifique pour les fichiers - CORRIGER LA LOGIQUE DE VALIDATION
      } else if ($field.attr("type") === "file") {
        // Pour les fichiers - Vérifier si le fichier est uploadé SEULEMENT pour sponsor/exposant
        var rawName = $field.attr('name');
        var fileKey = normalizeKey($field.data('file-name') || rawName);
        var currentCategoryType = $('input[name="category_type"]:checked').val();
        var currentVisaChoice = $('input[name="visa"]:checked').val();

        // Le logo n'est requis que pour sponsor et exposant
        if (fileKey === 'logo' && (currentCategoryType === 'sponsor' || currentCategoryType === 'exposant')) {
          if (!window.uploadedFiles || !window.uploadedFiles[fileKey]) {
            showFieldError($field, "Veuillez uploader un fichier pour " + fieldName);
            invalidFields.push(fieldName);
            isValid = false;
            console.log('❌ Logo manquant pour', currentCategoryType);
          } else {
            console.log('✅ Logo trouvé pour', currentCategoryType);
          }
        }
        // Le passeport n'est requis que si visa = oui
        else if (fileKey === 'passport') {
          if (currentVisaChoice === 'oui' && (!window.uploadedFiles || !window.uploadedFiles[fileKey])) {
            showFieldError($field, "Veuillez uploader un fichier pour " + fieldName);
            invalidFields.push(fieldName);
            isValid = false;
            console.log('❌ Passeport manquant pour visa=oui');
          } else if (currentVisaChoice === 'oui') {
            console.log('✅ Passeport trouvé pour visa=oui');
          } else {
            console.log('ℹ️ Passeport non requis (visa=non)');
          }
        }
      } else {
        // Pour les autres champs
        if (!$field.val().trim()) {
          showFieldError($field, "Le champ " + fieldName + " est requis");
          invalidFields.push(fieldName);
          isValid = false;
        }
      }
    });

    // Validation spécifique pour l'email
    var emailField = step.find("input[type='email']");
    if (emailField.length && emailField.val()) {
      var email = emailField.val();
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        var fieldName = getFieldName(emailField);
        showFieldError(emailField, "Format d'email invalide pour " + fieldName);
        invalidFields.push(fieldName);
        isValid = false;
      }
    }

    // Validation spécifique pour le téléphone
    var phoneField = step.find("input[name='phone']");
    if (phoneField.length && phoneField.val()) {
      var phone = phoneField.val();
      var phoneRegex = /^[0-9\s\-\(\)]{8,}$/;
      if (!phoneRegex.test(phone.replace(/\s/g, ''))) {
        showFieldError(phoneField, "Numéro de téléphone invalide");
        isValid = false;
      }
    }

    // Si des champs sont invalides, afficher une alerte avec la liste
    if (!isValid && invalidFields.length > 0) {
      showValidationAlert(invalidFields);
    }

    return isValid;
  }

  // ---------------------------
  // Obtenir le nom d'un champ pour les messages d'erreur
  // ---------------------------
  function getFieldName($field) {
    var fieldType = $field.attr('type');
    var name = $field.attr('name');
    
    var fieldNames = {
      'company': 'Nom de la société, institution, ou profession',
      'contact_name': 'Personne de contact',
      'address': 'Adresse',
      'city': 'Ville',
      'postal': 'Code postal',
      'country': 'Pays',
      'email': 'Email',
      'prefix': 'Préfixe téléphonique',
      'phone': 'Numéro de téléphone',
      'category_type': 'Type de participation',
      'sponsor_level': 'Niveau de sponsoring',
      'exposant_stand': 'Type de stand',
      'payment': 'Mode de paiement',
      'visa': 'Invitation visa',
      'history': 'Historique de participation',
      'logo': 'Logo',
      'passport': 'Passeport'
    };
    
    return fieldNames[name] || name;
  }

  // ---------------------------
  // Afficher les erreurs de champ amélioré
  // ---------------------------
  function showFieldError(field, message) {
    field.addClass("invalid");
    
    // Créer ou mettre à jour le message d'erreur
    var errorDiv = field.closest('.form-card').find(".error-message[data-field='" + field.attr('name') + "']");
    if (errorDiv.length === 0) {
      errorDiv = $('<div class="error-message" data-field="' + field.attr('name') + '"></div>');
      field.after(errorDiv);
    }
    errorDiv.text(message);
  }

  // ---------------------------
  // Afficher une alerte avec les champs manquants
  // ---------------------------
  function showValidationAlert(invalidFields) {
    var fieldsList = invalidFields.map(function(field) {
      return '• ' + field;
    }).join('<br>');
    
    Swal.fire({
      title: '❌ Champs incomplets',
      html: 'Veuillez remplir les champs suivants :<br><br>' + fieldsList,
      icon: 'error',
      confirmButtonText: 'Compris',
      confirmButtonColor: '#ffae00',
      background: '#fff',
      customClass: {
        popup: 'animated fadeIn'
      }
    });
  }

  // ---------------------------
  // Fonction de mise à jour de la barre %
  // ---------------------------
  function setProgressBar(curStep){
    var percent = parseFloat(100 / steps) * curStep;
    percent = percent > 100 ? 100 : percent; // Ne pas dépasser 100%
    percent = Math.round(percent);
    
    $(".progress-bar")
      .not(".upload-bar")
      .css("width", percent + "%")
      .attr("aria-valuenow", percent)
      .text(percent + "%");
  }

  // ---------------------------
  // Gestion des uploads IMMÉDIATS ET DÉFINITIFS
  // ---------------------------
  function initializeFileUploads() {
    $('.file-upload-area').each(function() {
      const uploadArea = $(this);
      const fileInput = uploadArea.find('input[type="file"]');

      // Normalize key helper
      function getFileKey(input) {
        var key = input.data('file-name') || input.attr('name') || '';
        // Remove array suffixes like name[]
        key = key.replace(/\[\]$/, '');
        return key;
      }

      // Drag and drop
      uploadArea.on('dragover', function(e) {
        e.preventDefault();
        $(this).addClass('dragover');
      });

      uploadArea.on('dragleave', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
      });

      uploadArea.on('drop', function(e) {
        e.preventDefault();
        $(this).removeClass('dragover');
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
          fileInput[0].files = files;
          fileInput.trigger('change');
        }
      });

      // Gestion du changement de fichier - UPLOAD IMMÉDIAT ET DÉFINITIF
      fileInput.on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
          // Vérifier la taille du fichier
          if (file.size > 10 * 1024 * 1024) {
            showErrorMessage(`Le fichier "${file.name}" est trop volumineux (${(file.size/1024/1024).toFixed(2)} MB). Maximum: 10 MB`);
            resetFileInput(uploadArea, fileInput);
            return;
          }

          var key = getFileKey(fileInput);
          // Upload immédiat et définitif
          uploadFileToServer(fileInput, file, key);
        }
      });
    });
  }

  // ---------------------------
  // UPLOAD DÉFINITIF - Fonction principale
  // ---------------------------
  function uploadFileToServer(input, file, fileName) {
    const uploadArea = input.closest('.file-upload-area');
    const progressBar = uploadArea.find('.upload-progress-bar');
    const progressText = uploadArea.find('.upload-progress-text');
    const successIcon = uploadArea.find('.upload-success');
    const uploadPlaceholder = uploadArea.find('.upload-placeholder');
    const uploadProgress = progressBar.closest('.upload-progress');
    
    // Masquer le placeholder et afficher la progression
    uploadPlaceholder.hide();
    progressBar.css('width', '0%');
    progressText.text('0%');
    uploadProgress.show().css('display', 'flex');
    successIcon.hide();
    
    // S'assurer que la section de confirmation est cachée au début
    const confirmationSection = uploadArea.find('.file-uploaded-confirmation');
    confirmationSection.hide();
    
    console.log(`📤 Début upload définitif: ${file.name} (${(file.size/1024/1024).toFixed(2)} MB)`);
    
  // Créer FormData pour l'upload
  const formData = new FormData();
  formData.append('file', file);
  // fileName ici est la clé normalisée (ex: logo, passport)
  formData.append('file_type', fileName);
    
    // Upload via AJAX
    const xhr = new XMLHttpRequest();
    
    // Suivre la progression
    xhr.upload.addEventListener('progress', function(e) {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        progressBar.css('width', percentComplete + '%');
        progressText.text(Math.round(percentComplete) + '%');
        
        // Messages selon la progression
        if (percentComplete > 80) {
          progressText.text(Math.round(percentComplete) + '% - Finalisation...');
        } else if (percentComplete > 50) {
          progressText.text(Math.round(percentComplete) + '% - Traitement...');
        }
      }
    }, false);
    
    xhr.addEventListener('load', function() {
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.success) {
            // Normaliser la clé (retirer [] si besoin)
            var key = (fileName || input.data('file-name') || input.attr('name') || '').toString().replace(/\[\]$/, '');

            // Stocker la référence du fichier uploadé avec métadonnées utiles
            window.uploadedFiles = window.uploadedFiles || {};
            window.uploadedFiles[key] = {
              original_name: response.data.original_name || file.name,
              size: response.data.size || file.size,
              server_data: response.data || response,
              uploaded_at: new Date().toISOString()
            };

            // Marquer l'input comme uploadé pour la validation
            try { input.data('uploaded', true); input.data('uploaded-filekey', key); } catch(e){}

            console.log(`✅ Fichier "${file.name}" uploadé définitivement avec succès (key=${key})`);
            console.log('📁 Référence stockée:', window.uploadedFiles[key]);

            // Afficher la confirmation
            uploadProgress.hide();
            successIcon.show().html('<i class="fas fa-check"></i> Fichier uploadé avec succès');
            showFileConfirmation(uploadArea, window.uploadedFiles[key], input);
            uploadArea.addClass('uploaded');

            // Vérifier si nous sommes à l'étape 10 avec visa = non POUR DÉCLENCHER LA VALIDATION
            var currentStep = input.closest('fieldset');
            var currentStepId = currentStep.data('step');
            var visaChoice = $('input[name="visa"]:checked').val();
            var categoryType = $('input[name="category_type"]:checked').val();

            console.log('🔍 Post-upload check - Étape:', currentStepId, 'Visa:', visaChoice, 'Catégorie:', categoryType);

            if (currentStepId === 'etape10') {
              console.log('🔄 Upload terminé à etape10 - visa:', visaChoice);
              if (visaChoice === 'non') {
                console.log('🔄 Upload terminé à etape10 avec visa=non - affichage bouton soumission');
                // Petite temporisation pour s'assurer que l'interface est prête
                setTimeout(function() {
                  showFinalSubmitButton();
                }, 500);
              } else {
                console.log('🔄 Upload terminé à etape10 avec visa=oui - vérifier bouton suivant');
                // S'assurer que le bouton suivant est visible pour visa=oui
                var currentStep = $('fieldset[data-step="etape10"]');
                if (currentStep.is(':visible')) {
                  currentStep.find('.next').show();
                  currentStep.find('.submit-final').hide();
                }
              }
            } else if (currentStepId === 'etape11') {
              // À l'étape 11 (passeport), toujours permettre la soumission finale
              console.log('🔄 Upload terminé à etape11 - affichage bouton soumission finale');
              setTimeout(function() {
                var step11 = $('fieldset[data-step="etape11"]');
                if (step11.is(':visible')) {
                  step11.find('.next').hide();
                  if (step11.find('.submit-final').length === 0) {
                    var submitButton = $('<input type="button" name="submit" class="submit submit-final action-button" value="Finaliser l\'inscription" />');
                    var lastButton = step11.find('.action-button, .action-button-previous').last();
                    if (lastButton.length > 0) {
                      lastButton.after(submitButton);
                    } else {
                      step11.append(submitButton);
                    }
                  } else {
                    step11.find('.submit-final').show();
                  }
                }
              }, 500);
            }
          } else {
            throw new Error(response.message || 'Erreur lors de l\'upload');
          }
        } catch (e) {
          handleUploadError(uploadArea, input, `Erreur de traitement: ${e.message}`);
        }
      } else {
        handleUploadError(uploadArea, input, `Erreur serveur (${xhr.status})`);
      }
    });
    
    xhr.addEventListener('error', function() {
      handleUploadError(uploadArea, input, 'Erreur de connexion lors de l\'upload');
    });
    
    xhr.addEventListener('timeout', function() {
      handleUploadError(uploadArea, input, 'Timeout - Upload trop long');
    });
    
    xhr.timeout = 300000; // 5 minutes timeout
    xhr.open('POST', 'upload_file.php');
    xhr.send(formData);
  }

  // ---------------------------
  // Gestion des erreurs d'upload avec bouton Réessayer
  // ---------------------------
  function handleUploadError(uploadArea, input, errorMessage) {
    console.error(`❌ Erreur upload: ${errorMessage}`);
    
    const uploadPlaceholder = uploadArea.find('.upload-placeholder');
    const uploadProgress = uploadArea.find('.upload-progress');
    const progressBar = uploadArea.find('.upload-progress-bar');
    const progressText = uploadArea.find('.upload-progress-text');
    
    // Réinitialiser l'affichage
    uploadProgress.hide();
    progressBar.css('width', '0%');
    progressText.text('0%');
    
    // Afficher message d'erreur avec option de réessayer
    Swal.fire({
      title: '❌ Erreur d\'upload',
      html: `
        <div style="text-align: left;">
          <p>${errorMessage}</p>
          <p><strong>Voulez-vous réessayer ?</strong></p>
        </div>
      `,
      icon: 'error',
      showCancelButton: true,
      confirmButtonText: 'Réessayer',
      cancelButtonText: 'Changer de fichier',
      confirmButtonColor: '#ffae00',
      cancelButtonColor: '#6c757d',
      background: '#fff'
    }).then((result) => {
      if (result.isConfirmed) {
        // Réessayer l'upload
        const file = input[0].files[0];
        const fileName = input.attr('name');
        if (file) {
          uploadFileToServer(input, file, fileName);
        }
      } else {
        // Réinitialiser et permettre de choisir un autre fichier
        resetFileInput(uploadArea, input);
        uploadPlaceholder.show();
      }
    });
  }

  // ---------------------------
  // Afficher la confirmation de fichier uploadé
  // ---------------------------
  function showFileConfirmation(uploadArea, fileData, input) {
    const confirmationSection = uploadArea.find('.file-uploaded-confirmation');
    const fileNameElem = uploadArea.find('.file-uploaded-name');
    const fileSize = uploadArea.find('.file-uploaded-size');
    const changeBtn = uploadArea.find('.change-file-btn');
    const removeBtn = uploadArea.find('.remove-file-btn');

    // Normalisation de la clé
    var rawName = input.attr('name') || input.data('file-name') || '';
    var key = rawName.toString().replace(/\[\]$/, '');

    // Calculer la taille du fichier
    const fileSizeMB = (fileData.size / 1024 / 1024).toFixed(2);

    // Mettre à jour les informations
    fileNameElem.text(fileData.original_name || (fileData.server_data && fileData.server_data.original_name) || 'Fichier');
    fileSize.text(fileSizeMB + ' MB');

    // Afficher la section de confirmation
    confirmationSection.show();

    // Gestionnaire pour le bouton "Changer"
    changeBtn.off('click').on('click', function() {
      // Supprimer la référence locale puis ouvrir le file picker
      if (window.uploadedFiles && window.uploadedFiles[key]) delete window.uploadedFiles[key];
      resetFileInput(uploadArea, input);
      input.trigger('click');
    });

    // Gestionnaire pour le bouton "Supprimer"
    removeBtn.off('click').on('click', function() {
      // Optionnel: Supprimer le fichier du serveur si filename connu
      var serverFilename = (window.uploadedFiles && window.uploadedFiles[key] && window.uploadedFiles[key].server_data && window.uploadedFiles[key].server_data.filename) || null;
      if (serverFilename) {
        deleteFileFromServer(key, serverFilename);
      }
      if (window.uploadedFiles && window.uploadedFiles[key]) delete window.uploadedFiles[key];
      resetFileInput(uploadArea, input);
    });
  }

  // ---------------------------
  // Supprimer un fichier du serveur (optionnel)
  // ---------------------------
  function deleteFileFromServer(fileType, filename) {
    // Envoyer une requête pour supprimer le fichier
    fetch('delete_file.php', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `filename=${encodeURIComponent(filename)}&file_type=${fileType}`
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        console.log(`🗑️ Fichier ${filename} supprimé du serveur`);
      } else {
        console.warn(`⚠️ Impossible de supprimer ${filename} du serveur`);
      }
    })
    .catch(error => {
      console.error('Erreur lors de la suppression:', error);
    });
  }

  // ---------------------------
  // Réinitialiser l'input fichier
  // ---------------------------
  function resetFileInput(uploadArea, input) {
    input.val('');
    const confirmationSection = uploadArea.find('.file-uploaded-confirmation');
    const uploadPlaceholder = uploadArea.find('.upload-placeholder');
    const successIcon = uploadArea.find('.upload-success');
    const progressBar = uploadArea.find('.upload-progress-bar');
    const progressText = uploadArea.find('.upload-progress-text');
    const uploadProgress = progressBar.closest('.upload-progress');
    
    // Réinitialiser l'affichage
    confirmationSection.hide();
    uploadPlaceholder.show();
    successIcon.hide();
    uploadProgress.hide();
    progressBar.css('width', '0%');
    progressText.text('0%');
    
    // Retirer la classe de succès
    uploadArea.removeClass('uploaded');
    // Supprimer la référence globale associée à cet input
    var rawName = input.attr('name') || input.data('file-name') || '';
    var key = rawName.toString().replace(/\[\]$/, '');
    if (window.uploadedFiles && window.uploadedFiles[key]) {
      delete window.uploadedFiles[key];
    }
  }

  // Initialiser les uploads de fichiers
  initializeFileUploads();

  // ---------------------------
  // Chargement dynamique des pays avec drapeaux
  // ---------------------------
  function loadCountriesWithFlags() {
    var select = $("select[name='country']");
    
    // Liste des pays avec codes de drapeaux
    var countries = [
      {code: 'CD', name: 'République Démocratique du Congo', flag: 'cd'},
      {code: 'FR', name: 'France', flag: 'fr'},
      {code: 'BE', name: 'Belgique', flag: 'be'},
      {code: 'US', name: 'États-Unis', flag: 'us'},
      {code: 'CA', name: 'Canada', flag: 'ca'},
      {code: 'CH', name: 'Suisse', flag: 'ch'},
      {code: 'GB', name: 'Royaume-Uni', flag: 'gb'},
      {code: 'DE', name: 'Allemagne', flag: 'de'},
      {code: 'ZA', name: 'Afrique du Sud', flag: 'za'},
      {code: 'SN', name: 'Sénégal', flag: 'sn'},
      {code: 'CI', name: 'Côte d\'Ivoire', flag: 'ci'},
      {code: 'CM', name: 'Cameroun', flag: 'cm'},
      {code: 'TG', name: 'Togo', flag: 'tg'},
      {code: 'BJ', name: 'Bénin', flag: 'bj'},
      {code: 'ML', name: 'Mali', flag: 'ml'},
      {code: 'BF', name: 'Burkina Faso', flag: 'bf'},
      {code: 'GN', name: 'Guinée', flag: 'gn'},
      {code: 'NE', name: 'Niger', flag: 'ne'},
      {code: 'TN', name: 'Tunisie', flag: 'tn'},
      {code: 'MA', name: 'Maroc', flag: 'ma'},
      {code: 'DZ', name: 'Algérie', flag: 'dz'},
      {code: 'EG', name: 'Égypte', flag: 'eg'},
      {code: 'KE', name: 'Kenya', flag: 'ke'},
      {code: 'NG', name: 'Nigeria', flag: 'ng'},
      {code: 'GH', name: 'Ghana', flag: 'gh'},
      {code: 'ET', name: 'Éthiopie', flag: 'et'}
    ];

    // Trier les pays par ordre alphabétique
    countries.sort(function(a, b) {
      return a.name.localeCompare(b.name);
    });

    // Vider le select d'abord
    select.empty();

    // Ajouter l'option par défaut
    select.append($("<option></option>").attr("value", "").text("Sélectionnez un pays"));

    // Ajouter les pays avec drapeaux
    $.each(countries, function(index, country) {
      var option = $("<option></option>")
        .attr("value", country.code)
        .text(country.name)
        .attr('data-flag', country.flag);
      
      select.append(option);
    });

    // Initialiser Select2 avec formatage des drapeaux
    select.select2({
      placeholder: "Cliquez ici pour choisir un pays",
      allowClear: true,
      width: '100%',
      templateResult: formatCountry,
      templateSelection: formatCountrySelection,
      escapeMarkup: function(m) { return m; }
    });
  }

  // Formater l'affichage des pays avec drapeaux
  function formatCountry(country) {
    if (!country.id) { 
      return country.text; 
    }
    
    var flagCode = $(country.element).attr('data-flag') || country.id.toLowerCase();
    var flagUrl = `https://flagcdn.com/w20/${flagCode}.png`;
    
    var $country = $(
      `<span>
        <img src="${flagUrl}" class="flag-icon" alt="${country.text}" style="margin-right: 8px;">
        ${country.text}
      </span>`
    );
    return $country;
  }

  function formatCountrySelection(country) {
    if (!country.id) { 
      return country.text; 
    }
    
    var flagCode = $(country.element).attr('data-flag') || country.id.toLowerCase();
    var flagUrl = `https://flagcdn.com/w20/${flagCode}.png`;
    
    var $country = $(
      `<span>
        <img src="${flagUrl}" class="flag-icon" alt="${country.text}" style="margin-right: 8px;">
        ${country.text}
      </span>`
    );
    return $country;
  }

  // ---------------------------
  // Chargement dynamique des préfixes téléphoniques avec drapeaux - VERSION AMÉLIORÉE
  // ---------------------------
  function loadPhonePrefixes() {
    var select = $("select[name='prefix']");
    
    // Liste des pays avec codes de drapeaux et préfixes
    var countriesWithPrefixes = [
        {code: 'CD', name: 'RDC', prefix: '+243', flag: 'cd'},
        {code: 'FR', name: 'France', prefix: '+33', flag: 'fr'},
        {code: 'BE', name: 'Belgique', prefix: '+32', flag: 'be'},
        {code: 'US', name: 'USA', prefix: '+1', flag: 'us'},
        {code: 'CA', name: 'Canada', prefix: '+1', flag: 'ca'},
        {code: 'CH', name: 'Suisse', prefix: '+41', flag: 'ch'},
        {code: 'GB', name: 'UK', prefix: '+44', flag: 'gb'},
        {code: 'DE', name: 'Allemagne', prefix: '+49', flag: 'de'},
        {code: 'ZA', name: 'Afrique Sud', prefix: '+27', flag: 'za'},
        {code: 'SN', name: 'Sénégal', prefix: '+221', flag: 'sn'},
        {code: 'CI', name: 'Côte Ivoire', prefix: '+225', flag: 'ci'},
        {code: 'CM', name: 'Cameroun', prefix: '+237', flag: 'cm'},
        {code: 'TG', name: 'Togo', prefix: '+228', flag: 'tg'},
        {code: 'BJ', name: 'Bénin', prefix: '+229', flag: 'bj'},
        {code: 'ML', name: 'Mali', prefix: '+223', flag: 'ml'},
        {code: 'BF', name: 'Burkina', prefix: '+226', flag: 'bf'},
        {code: 'GN', name: 'Guinée', prefix: '+224', flag: 'gn'},
        {code: 'NE', name: 'Niger', prefix: '+227', flag: 'ne'},
        {code: 'TN', name: 'Tunisie', prefix: '+216', flag: 'tn'},
        {code: 'MA', name: 'Maroc', prefix: '+212', flag: 'ma'},
        {code: 'DZ', name: 'Algérie', prefix: '+213', flag: 'dz'},
        {code: 'EG', name: 'Égypte', prefix: '+20', flag: 'eg'},
        {code: 'KE', name: 'Kenya', prefix: '+254', flag: 'ke'},
        {code: 'NG', name: 'Nigeria', prefix: '+234', flag: 'ng'},
        {code: 'GH', name: 'Ghana', prefix: '+233', flag: 'gh'}
    ];

    // Trier les pays par ordre alphabétique du nom
    countriesWithPrefixes.sort(function(a, b) {
        return a.name.localeCompare(b.name);
    });

    // Vider le select d'abord
    select.empty();

    // Ajouter l'option par défaut
    select.append($("<option></option>").attr("value", "").text("Choisir le pays"));

    // Ajouter les pays avec drapeaux et préfixes
    $.each(countriesWithPrefixes, function(index, country) {
        var option = $("<option></option>")
            .attr("value", country.prefix)
            .text(country.prefix + " - " + country.name)
            .attr('data-flag', country.flag)
            .attr('data-country', country.name)
            .attr('data-prefix', country.prefix);
        
        select.append(option);
    });

    // Initialiser Select2 avec formatage des drapeaux
    select.select2({
        placeholder: "Choisir le pays",
        allowClear: false,
        width: '140px',
        templateResult: formatPhonePrefixWithFlag,
        templateSelection: formatPhonePrefixSelectionWithFlag,
        escapeMarkup: function(m) { return m; },
        minimumResultsForSearch: 5,
        dropdownCssClass: 'select2-container--prefix'
    });

    // Sélectionner la RDC par défaut
    select.val('+243').trigger('change');
  }

  // Formater l'affichage des préfixes avec drapeaux (menu déroulant)
  function formatPhonePrefixWithFlag(prefix) {
    if (!prefix.id) { 
        return prefix.text; 
    }
    
    var flagCode = $(prefix.element).attr('data-flag');
    var countryName = $(prefix.element).attr('data-country');
    var prefixValue = $(prefix.element).attr('data-prefix');
    
    if (flagCode) {
        var flagUrl = `https://flagcdn.com/w20/${flagCode}.png`;
        
        var $prefix = $(
            `<div class="prefix-option">
                <img src="${flagUrl}" class="prefix-flag" alt="${countryName}">
                <span class="prefix-text">${prefixValue}</span>
                <span class="prefix-country">${countryName}</span>
            </div>`
        );
        return $prefix;
    }
    return prefix.text;
  }

  // Formater la sélection affichée (champ sélectionné)
  function formatPhonePrefixSelectionWithFlag(prefix) {
    if (!prefix.id) { 
        return prefix.text; 
    }
    
    var flagCode = $(prefix.element).attr('data-flag');
    var prefixValue = $(prefix.element).attr('data-prefix');
    
    if (flagCode) {
        var flagUrl = `https://flagcdn.com/w20/${flagCode}.png`;
        
        var $prefix = $(
            `<div style="display: flex; align-items: center; gap: 8px;">
                <img src="${flagUrl}" style="width: 20px; height: 15px; border: 1px solid #ddd; border-radius: 2px;" alt="">
                <span style="font-weight: bold;">${prefixValue}</span>
            </div>`
        );
        return $prefix;
    }
    return prefix.text;
  }

  // Charger les pays au démarrage
  loadCountriesWithFlags();

  // Charger les préfixes téléphoniques au démarrage
  loadPhonePrefixes();

  // ---------------------------
  // Soumission finale - GESTIONNAIRE D'ÉVÉNEMENTS AMÉLIORÉ
  // ---------------------------
  $(document).on('click', '.submit, #submit-participant, .submit-final', function(e){
    e.preventDefault();
    
    console.log('🔄 Click détecté sur bouton de soumission:', $(this).attr('class'), $(this).attr('id'));
    
    // Vérifier si c'est le bouton participant simple
    if ($(this).attr('id') === 'submit-participant') {
      console.log('📝 Soumission participant simple - validation allégée');
      
      // Validation de base uniquement pour participant simple
      var lastStep = $(this).closest("fieldset");
      var valid = validateStep(lastStep);
      
      if (!valid) {
        console.log('❌ Validation de l\'étape échouée pour participant simple');
        return;
      }
      
      console.log('✅ Validation participant simple réussie - soumission directe');
      submitFormData();
      return;
    }
    
    console.log('=== DÉBUT SOUMISSION FORMULAIRE INSCRIPTION ===');
    console.log('📦 Fichiers uploadés:', window.uploadedFiles);
    
    // === VÉRIFICATION ANTI-SPAM ===
    const honeypot = $('input[name="website"]').val();
    if (honeypot && honeypot !== '') {
        console.log('🚫 SPAM DÉTECTÉ: Honeypot rempli');
        showErrorMessage('Soumission bloquée pour cause de sécurité.');
        return;
    }
    
    // Vérification du timestamp
    const submitTime = Math.floor(Date.now() / 1000);
    const formTime = parseInt($('#form_timestamp').val());
    if (submitTime - formTime < 3) {
        console.log('🚫 SPAM DÉTECTÉ: Soumission trop rapide');
        showErrorMessage('Soumission trop rapide. Veuillez réessayer.');
        return;
    }
    
    console.log('✅ Vérifications anti-spam réussies');

    // Validation finale de la dernière étape
    var lastStep = $(this).closest("fieldset");
    var valid = validateStep(lastStep);
    
    if (!valid) {
      console.log('❌ Validation de la dernière étape échouée');
      return;
    }

    // Vérification conditionnelle des fichiers selon le type de participant
    var categoryType = $('input[name="category_type"]:checked').val();
    var visaChoice = $('input[name="visa"]:checked').val();
    
    console.log('🔍 Vérification avant soumission - Catégorie détectée:', categoryType);
    console.log('🔍 Vérification avant soumission - Visa:', visaChoice);
    
    if (categoryType === 'sponsor' || categoryType === 'exposant') {
      console.log('📋 Vérification fichiers pour sponsor/exposant');
      // Vérifier le logo pour sponsor et exposant
      if (!window.uploadedFiles.logo) {
        console.log('❌ Logo manquant pour', categoryType);
        showErrorMessage('Le logo doit être uploadé avant soumission');
        return;
      }
      
      // Vérifier le passeport seulement si visa = oui
      if (visaChoice === 'oui' && !window.uploadedFiles.passport) {
        console.log('❌ Passeport manquant pour visa');
        showErrorMessage('Le passeport doit être uploadé avant soumission');
        return;
      }
    } else if (categoryType === 'participant') {
      console.log('✅ Participant simple - aucun fichier requis');
    } else {
      console.log('⚠️ Type de catégorie non reconnu:', categoryType);
    }

    console.log('✅ Validation de la dernière étape réussie');
    console.log('✅ Fichiers vérifiés uploadés');

    // Lancer la soumission
    submitFormData();
  });

  // ---------------------------
  // Fonction de soumission des données (SEULEMENT RÉFÉRENCES)
  // ---------------------------
  function submitFormData() {
    // Animation de soumission - AMÉLIORER POUR TOUS LES BOUTONS
    $(".submit, .submit-final").html('<i class="fas fa-spinner fa-spin"></i> Soumission en cours...').addClass('pulsing');
    $(".submit, .submit-final").prop('disabled', true);
    $("#submit-participant").html('<i class="fas fa-spinner fa-spin"></i> Soumission en cours...').addClass('pulsing');
    $("#submit-participant").prop('disabled', true);

    // Afficher la progression globale d'envoi
    showGlobalUploadProgress();

    // Préparer les données du formulaire (SANS FICHIERS)
    var formData = new FormData();
    
    // Ajouter tous les champs du formulaire
    $('#msform').find('input, select').each(function() {
      var $field = $(this);
      var name = $field.attr('name');
      var type = $field.attr('type');
      
      // Ignorer les champs anti-spam et fichiers
      if (name && type !== 'file' && type !== 'button' && type !== 'submit') {
        
        // Filtrer les champs selon le type de participant
        var categoryType = $('input[name="category_type"]:checked').val();
        var shouldIncludeField = true;
        
        // Exclure les champs spécifiques selon le type
        if (categoryType === 'participant') {
          // Participant simple : exclure les champs sponsor/exposant/visa/paiement
          var excludedFields = ['sponsor_level', 'exposant_stand', 'payment', 'visa'];
          if (excludedFields.includes(name)) {
            console.log('🚫 Champ exclu pour participant simple:', name);
            shouldIncludeField = false;
          }
        } else if (categoryType === 'sponsor') {
          // Sponsor : exclure les champs exposant
          if (name === 'exposant_stand') {
            console.log('🚫 Champ exclu pour sponsor:', name);
            shouldIncludeField = false;
          }
        } else if (categoryType === 'exposant') {
          // Exposant : exclure les champs sponsor
          if (name === 'sponsor_level') {
            console.log('🚫 Champ exclu pour exposant:', name);
            shouldIncludeField = false;
          }
        }
        
        if (shouldIncludeField) {
          if (type === 'radio') {
            if ($field.is(':checked')) {
              formData.append(name, $field.val());
              console.log(`📋 Champ ${name}: ${$field.val()}`);
            }
          } else if (type === 'checkbox') {
            if ($field.is(':checked')) {
              formData.append(name, $field.val());
            }
          } else {
            // Ne pas logger le honeypot pour la sécurité
            if (name !== 'website') {
              console.log(`📋 Champ ${name}: ${$field.val()}`);
            }
            formData.append(name, $field.val());
          }
        }
      }
    });

    // Consolider les données de catégorie selon le type
    var categoryType = $('input[name="category_type"]:checked').val();
    console.log('🔍 DEBUG - categoryType détecté:', categoryType);
    console.log('🔍 DEBUG - Nombre de radios category_type:', $('input[name="category_type"]').length);
    console.log('🔍 DEBUG - Radio checked:', $('input[name="category_type"]:checked').length);
    
    var finalCategory = '';
    
    if (categoryType === 'sponsor') {
      var sponsorLevel = $('input[name="sponsor_level"]:checked').val();
      console.log('🔍 DEBUG - sponsor_level:', sponsorLevel);
      finalCategory = sponsorLevel || 'Sponsor';
    } else if (categoryType === 'exposant') {
      var exposantStand = $('input[name="exposant_stand"]:checked').val();
      console.log('🔍 DEBUG - exposant_stand:', exposantStand);
      finalCategory = 'Exposant - ' + (exposantStand || 'Standard');
    } else if (categoryType === 'participant') {
      finalCategory = 'Participant Simple';
    } else {
      // Fallback: essayer de détecter la catégorie autrement
      console.warn('⚠️ categoryType non détecté, tentative de fallback...');
      // Vérifier si on est dans un flux exposant (présence de champs exposant)
      if ($('#etape6c').is(':visible') || $('input[name="exposant_stand"]').length > 0) {
        var exposantStand = $('input[name="exposant_stand"]:checked').val();
        finalCategory = 'Exposant - ' + (exposantStand || 'Standard');
      } else if ($('#etape6b').is(':visible') || $('input[name="sponsor_level"]').length > 0) {
        var sponsorLevel = $('input[name="sponsor_level"]:checked').val();
        finalCategory = sponsorLevel || 'Sponsor';
      } else {
        finalCategory = 'Participant Simple';
      }
      console.log('🔍 DEBUG - Fallback catégorie:', finalCategory);
    }
    
    // Vérification finale
    if (!finalCategory || finalCategory.trim() === '') {
      console.error('❌ ERREUR: Catégorie vide!');
      finalCategory = 'Non spécifié';
    }
    
    formData.append('category', finalCategory);
    console.log(`📋 Catégorie finale: ${finalCategory}`);

    // Ajouter les RÉFÉRENCES des fichiers déjà uploadés (si applicable)
    if (window.uploadedFiles.logo) {
      formData.append('logo_filename', window.uploadedFiles.logo.server_data.filename);
      formData.append('logo_original_name', window.uploadedFiles.logo.original_name);
    }
    if (window.uploadedFiles.passport) {
      formData.append('passport_filename', window.uploadedFiles.passport.server_data.filename);
      formData.append('passport_original_name', window.uploadedFiles.passport.original_name);
    }
    formData.append('files_uploaded', 'true');
    
    console.log('📤 Envoi des données via AJAX (sans fichiers)...');

    // Envoyer les données via AJAX - SEULEMENT LES RÉFÉRENCES
    var xhr = new XMLHttpRequest();
    
    // Suivre la progression de l'upload (seulement pour les données texte)
    xhr.upload.addEventListener('progress', function(e) {
      if (e.lengthComputable) {
        var percentComplete = (e.loaded / e.total) * 100;
        updateGlobalUploadProgress(percentComplete);
        console.log(`📤 Progression envoi: ${percentComplete.toFixed(1)}%`);
      }
    }, false);
    
    xhr.addEventListener('load', function(e) {
      console.log('✅ Transfert terminé');
      hideGlobalUploadProgress();
      
      try {
        var response = JSON.parse(xhr.responseText);
        console.log('📨 Réponse du serveur:', response);
        
        if (response.success) {
          showSuccessMessage(response.data || response);
          // Nettoyer les références après succès
          window.uploadedFiles = { logo: null, passport: null };
        } else {
          var errorMsg = response.message || 
                         (response.errors ? response.errors.join(', ') : 'Erreur lors de la soumission');
          showErrorMessage(errorMsg, true, function() {
            submitFormData(); // Réessayer
          });
        }
      } catch (e) {
        console.error('❌ Erreur parsing JSON:', e);
        console.error('❌ Réponse brute:', xhr.responseText);
        showErrorMessage('Erreur de traitement de la réponse du serveur', true, function() {
          submitFormData(); // Réessayer
        });
      }
      
      // Réactiver le bouton
      $(".submit, .submit-final").html('Soumettre').removeClass('pulsing').prop('disabled', false);
      $("#submit-participant").html('Soumettre').removeClass('pulsing').prop('disabled', false);
    });
    
    xhr.addEventListener('error', function(e) {
      console.error('💥 Erreur de transfert:', e);
      hideGlobalUploadProgress();
      showErrorMessage('Erreur de connexion lors de la soumission', true, function() {
        submitFormData(); // Réessayer
      });
      $(".submit, .submit-final").html('Soumettre').removeClass('pulsing').prop('disabled', false);
      $("#submit-participant").html('Soumettre').removeClass('pulsing').prop('disabled', false);
    });
    
    xhr.addEventListener('timeout', function(e) {
      console.error('⏰ Timeout de transfert');
      hideGlobalUploadProgress();
      showErrorMessage('Timeout - La soumission a pris trop de temps', true, function() {
        submitFormData(); // Réessayer
      });
      $(".submit, .submit-final").html('Soumettre').removeClass('pulsing').prop('disabled', false);
      $("#submit-participant").html('Soumettre').removeClass('pulsing').prop('disabled', false);
    });
    
    xhr.timeout = 30000; // 30 secondes seulement (données légères)
    xhr.open('POST', 'process_inscription.php');
    xhr.send(formData);
  }

  // ---------------------------
  // Progression globale d'envoi
  // ---------------------------
  function showGlobalUploadProgress() {
    // Créer l'overlay de progression s'il n'existe pas
    if ($('#global-upload-progress').length === 0) {
      const progressHTML = `
        <div id="global-upload-progress" style="
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.8);
          display: flex;
          justify-content: center;
          align-items: center;
          flex-direction: column;
          z-index: 9999;
          color: white;
        ">
          <div style="
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            color: #333;
            max-width: 400px;
            width: 90%;
          ">
            <h3 style="margin-bottom: 20px; color: #FFA500;">
              <i class="fas fa-paper-plane"></i> Soumission en cours
            </h3>
            <p>Finalisation de l'inscription...</p>
            <div style="
              background: #f0f0f0;
              border-radius: 10px;
              height: 20px;
              margin: 20px 0;
              overflow: hidden;
            ">
              <div id="global-progress-bar" style="
                background: linear-gradient(90deg, #FFA500, #FF8C00);
                height: 100%;
                width: 0%;
                transition: width 0.3s ease;
                border-radius: 10px;
              "></div>
            </div>
            <div id="global-progress-text" style="font-weight: bold;">0%</div>
            <div style="margin-top: 15px; font-size: 12px; color: #666;">
              <i class="fas fa-info-circle"></i>
              Les fichiers ont déjà été uploadés, soumission des données...
            </div>
          </div>
        </div>
      `;
      $('body').append(progressHTML);
    } else {
      $('#global-upload-progress').show();
    }
    
    $('#global-progress-bar').css('width', '0%');
    $('#global-progress-text').text('0%');
  }

  function updateGlobalUploadProgress(percent) {
    $('#global-progress-bar').css('width', percent + '%');
    $('#global-progress-text').text(Math.round(percent) + '%');
  }

  function hideGlobalUploadProgress() {
    $('#global-upload-progress').hide();
  }

  // ---------------------------
  // Fonction d'affichage du message de succès - VERSION CORRIGÉE POUR FERMETURE
  // ---------------------------
  function showSuccessMessage(data) {
    console.log('🎉 Affichage message de succès:', data);
    
    // Alternative robuste : utiliser une modal personnalisée au lieu de SweetAlert
    const modalHtml = `
      <div id="success-modal" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        font-family: Arial, sans-serif;
      ">
        <div style="
          background: white;
          border-radius: 15px;
          padding: 30px;
          max-width: 600px;
          width: 90%;
          position: relative;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
          animation: slideIn 0.5s ease-out;
        ">
          <!-- Bouton X de fermeture -->
          <button id="close-success-modal" style="
            position: absolute;
            top: 15px;
            right: 20px;
            background: none;
            border: none;
            font-size: 28px;
            cursor: pointer;
            color: #666;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
          ">&times;</button>
          
          <!-- Contenu principal -->
          <div style="text-align: center; margin-bottom: 25px;">
            <div style="font-size: 60px; margin-bottom: 15px;">🎉</div>
            <h2 style="color: #28a745; margin: 0; font-size: 24px;">Félicitations !</h2>
          </div>
          
          <div style="text-align: left; padding: 0;">
            <p style="margin-bottom: 15px; font-size: 16px; color: #333; text-align: center;">
              <strong>Votre inscription et sponsoring ont bien été enregistrés !</strong>
            </p>
            <div style="background: #f8fff9; padding: 15px; border-radius: 10px; border-left: 4px solid #28a745; margin-bottom: 20px;">
              <p style="margin: 5px 0; font-size: 14px;">
                <i class="fas fa-building" style="color: #28a745; margin-right: 8px;"></i>
                <strong>Société:</strong> ${data.company || 'Non spécifié'}
              </p>
              <p style="margin: 5px 0; font-size: 14px;">
                <i class="fas fa-hashtag" style="color: #28a745; margin-right: 8px;"></i>
                <strong>Référence:</strong> ${data.reference || 'EXPOBETON-' + new Date().getFullYear() + '-' + Math.random().toString(36).substr(2, 9).toUpperCase()}
              </p>
              <p style="margin: 5px 0; font-size: 14px;">
                <i class="fas fa-check-circle" style="color: #28a745; margin-right: 8px;"></i>
                <strong>Email de confirmation:</strong> Envoyé sous 24h
              </p>
              <p style="margin: 5px 0; font-size: 14px;">
                <i class="fas fa-check-circle" style="color: #28a745; margin-right: 8px;"></i>
                <strong>Contact:</strong> Notre équipe vous contactera sous 48h
              </p>
              <p style="margin: 5px 0; font-size: 14px;">
                <i class="fas fa-file" style="color: #28a745; margin-right: 8px;"></i>
                <strong>Fichiers joints:</strong> Logo et passeport transmis avec succès
              </p>
            </div>
            <p style="margin-bottom: 25px; font-size: 14px; color: #666; text-align: center;">
              Nous vous remercions pour votre confiance et vous souhaitons la bienvenue à ExpoBeton RDC 2025 !
            </p>
            
            <!-- Bouton de fermeture principal -->
            <div style="text-align: center;">
              <button id="close-and-reset-btn" style="
                background: linear-gradient(135deg, #ffae00, #e69c00);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(255, 174, 0, 0.3);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                min-width: 200px;
              ">Fermer et Nouveau Formulaire</button>
            </div>
          </div>
        </div>
      </div>
      
      <style>
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-30px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        
        #close-success-modal:hover {
          color: #ff4444 !important;
          transform: scale(1.1);
        }
        
        #close-and-reset-btn:hover {
          background: linear-gradient(135deg, #e69c00, #cc8a00) !important;
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(255, 174, 0, 0.4) !important;
        }
      </style>
    `;
    
    // Supprimer toute modal existante
    $('#success-modal').remove();
    
    // Ajouter la nouvelle modal au body
    $('body').append(modalHtml);
    
    // Fonction de fermeture et réinitialisation
    function closeAndReset() {
      console.log('🔄 Fermeture modal et réinitialisation demandée');
      $('#success-modal').fadeOut(300, function() {
        $(this).remove();
        console.log('✅ Modal supprimée');
      });
      
      // Réinitialiser le formulaire après un court délai
      setTimeout(() => {
        resetForm();
      }, 400);
    }
    
    // Gestionnaires d'événements
    $('#close-success-modal').on('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('🔄 Clic X détecté');
      closeAndReset();
    });
    
    $('#close-and-reset-btn').on('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('🔄 Clic bouton principal détecté');
      closeAndReset();
    });
    
    // Fermeture en cliquant sur le fond
    $('#success-modal').on('click', function(e) {
      if (e.target.id === 'success-modal') {
        console.log('🔄 Clic fond modal détecté');
        closeAndReset();
      }
    });
    
    // Fermeture avec la touche Échap
    $(document).on('keydown.successModal', function(e) {
      if (e.key === 'Escape') {
        console.log('🔄 Touche Échap détectée');
        $(document).off('keydown.successModal');
        closeAndReset();
      }
    });
    
    console.log('✅ Modal de succès personnalisée affichée');
  }

  // ---------------------------
  // Fonction d'affichage des erreurs AVEC RÉESSAI
  // ---------------------------
  function showErrorMessage(message, canRetry = false, retryCallback = null) {
    let html = `
      <div class="error-with-retry">
        <div style="text-align: left; margin-bottom: 20px;">${message}</div>
    `;
    
    if (canRetry) {
      html += `
        <div class="retry-actions">
          <button id="retry-button" class="retry-btn">
            <i class="fas fa-redo"></i> Réessayer
          </button>
          <button id="cancel-button" class="action-button-previous">
            <i class="fas fa-times"></i> Annuler
          </button>
        </div>
      `;
    }

    html += `</div>`;

    Swal.fire({
      title: '❌ Erreur',
      html: html,
      icon: 'error',
      showConfirmButton: !canRetry,
      confirmButtonText: 'Compris',
      confirmButtonColor: '#ffae00',
      background: '#fff',
      customClass: {
        popup: 'animated shake'
      },
      didOpen: () => {
        if (canRetry) {
          document.getElementById('retry-button').addEventListener('click', function() {
            Swal.close();
            if (retryCallback) {
              retryCallback();
            }
          });
          
          document.getElementById('cancel-button').addEventListener('click', function() {
            Swal.close();
          });
        }
      }
    });
  }

  // ---------------------------
  // Fonction de réinitialisation du formulaire - AMÉLIORÉE
  // ---------------------------
  function resetForm() {
    console.log('🔄 Début réinitialisation du formulaire');
    
    try {
      // Réinitialiser le formulaire HTML
      $("#msform")[0].reset();
      console.log('✅ Formulaire HTML réinitialisé');
      
      // Masquer tous les fieldsets et afficher le premier
      $("fieldset").hide();
      $("fieldset").first().show();
      console.log('✅ Étapes réinitialisées - première étape affichée');
      
      // Réinitialiser la progressbar
      $("#progressbar li").removeClass("active");
      $("#progressbar li").first().addClass("active");
      console.log('✅ Progressbar réinitialisée');
      
      // Réinitialiser les variables de navigation
      current = 1;
      setProgressBar(current);
      console.log('✅ Variables de navigation réinitialisées');
      
      // Masquer toutes les étapes conditionnelles
      hideAllConditionalSteps();
      console.log('✅ Étapes conditionnelles masquées');
      
      // Réinitialiser Select2
      try {
        $("select[name='country']").val(null).trigger('change');
        $("select[name='prefix']").val('+243').trigger('change'); // RDC par défaut
        console.log('✅ Select2 réinitialisés');
      } catch(e) {
        console.warn('⚠️ Erreur réinitialisation Select2:', e);
      }
      
      // Réinitialiser les uploads de fichiers
      $('.file-upload-area').each(function() {
        const uploadArea = $(this);
        const input = uploadArea.find('input[type="file"]');
        resetFileInput(uploadArea, input);
      });
      console.log('✅ Zones d\'upload réinitialisées');
      
      // Vider les références des fichiers
      window.uploadedFiles = { logo: null, passport: null };
      console.log('✅ Références fichiers vidées');
      
      // Réactiver tous les boutons de soumission
      $(".submit, .submit-final, #submit-participant").html('Soumettre').removeClass('pulsing').prop('disabled', false);
      console.log('✅ Boutons de soumission réactivés');
      
      // Réinitialiser le timestamp anti-spam
      $('#form_timestamp').val(Math.floor(Date.now() / 1000));
      console.log('✅ Timestamp anti-spam réinitialisé');
      
      // Supprimer tous les messages d'erreur
      $('.error-message').remove();
      $('.invalid').removeClass('invalid');
      console.log('✅ Messages d\'erreur supprimés');
      
      // Scroll vers le haut avec une petite temporisation
      setTimeout(function() {
        $('html, body').animate({
          scrollTop: $("#msform").offset().top - 50
        }, 500);
        console.log('✅ Scroll vers le haut effectué');
      }, 100);
      
      console.log('✅ Réinitialisation du formulaire complète');
      
    } catch(error) {
      console.error('❌ Erreur lors de la réinitialisation:', error);
      // En cas d'erreur, forcer un rechargement de la page
      setTimeout(function() {
        window.location.reload();
      }, 1000);
    }
  }

  // ---------------------------
  // Supprimer les messages d'erreur lors de la saisie
  // ---------------------------
  $("input, select").on('input change', function() {
    var $field = $(this);
    $field.removeClass("invalid");
    $field.siblings(".error-message").remove();
    
    // Pour les radios, supprimer l'erreur de tout le groupe
    if ($field.attr("type") === "radio") {
      var name = $field.attr("name");
      $('input[name="' + name + '"]').removeClass("invalid");
      $('input[name="' + name + '"]').siblings(".error-message").remove();
    }
  });

  // ---------------------------
  // Validation en temps réel pour l'email
  // ---------------------------
  $("input[type='email']").on('blur', function() {
    var email = $(this).val();
    if (email) {
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        showFieldError($(this), "Format d'email invalide");
      }
    }
  });

  console.log('✅ Formulaire d\'inscription initialisé avec upload immédiat');
});