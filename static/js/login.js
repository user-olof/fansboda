$(document).ready(function () {
    // Add focus effects to form inputs
    $('.form-control').each(function () {
        $(this).on('focus', function () {
            $(this).parent().addClass('focused');
        });

        $(this).on('blur', function () {
            if (!$(this).val()) {
                $(this).parent().removeClass('focused');
            }
        });
    });

    // Form elements
    const $form = $('form');
    const $submitBtn = $('input[type="submit"]');
    const $emailInput = $('#floatingEmail');
    const $passwordInput = $('#floatingPassword');
    const $rememberMe = $('#flexCheckDefault');

    // Add submit button loading state with enhanced UX
    $form.on('submit', function (e) {
        // Basic form validation before submission
        let isValid = true;

        // Check email
        if (!$emailInput.val().trim()) {
            $emailInput.addClass('is-invalid');
            isValid = false;
        } else {
            $emailInput.removeClass('is-invalid');
        }

        // Check password
        if (!$passwordInput.val().trim()) {
            $passwordInput.addClass('is-invalid');
            isValid = false;
        } else {
            $passwordInput.removeClass('is-invalid');
        }

        if (!isValid) {
            e.preventDefault();
            return false;
        }

        // Show loading state
        $submitBtn.prop('disabled', true);
        $submitBtn.val('Signing In...');
        $submitBtn.html('<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Signing In...');

        // Handle remember me functionality
        if ($rememberMe.prop('checked')) {
            localStorage.setItem('rememberMe', 'true');
            localStorage.setItem('savedEmail', $emailInput.val());
        } else {
            localStorage.removeItem('rememberMe');
            localStorage.removeItem('savedEmail');
        }

        // Re-enable after 5 seconds in case of error
        setTimeout(function () {
            $submitBtn.prop('disabled', false);
            $submitBtn.val('Sign In');
            $submitBtn.html('Sign In');
        }, 5000);
    });

    // Email validation with visual feedback
    $emailInput.on('blur', function () {
        const email = $(this).val().trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (email && !emailRegex.test(email)) {
            $(this).addClass('is-invalid');
            // Add custom error message if not already present
            if (!$(this).siblings('.invalid-feedback').length) {
                $(this).parent().append('<div class="invalid-feedback">Please enter a valid email address.</div>');
            }
        } else if (email) {
            $(this).removeClass('is-invalid').addClass('is-valid');
            $(this).siblings('.invalid-feedback').remove();
        } else {
            $(this).removeClass('is-invalid is-valid');
            $(this).siblings('.invalid-feedback').remove();
        }
    });

    // Password visibility toggle
    if ($passwordInput.length) {
        // Create password toggle button
        const $toggleBtn = $(`
            <button type="button" class="btn btn-link password-toggle p-0" 
                    style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); z-index: 10; color: #6c757d;">
                <i class="bi bi-eye"></i>
            </button>
        `);

        // Add relative positioning to password field container
        $passwordInput.parent().css('position', 'relative');
        $passwordInput.parent().append($toggleBtn);

        $toggleBtn.on('click', function (e) {
            e.preventDefault();
            const type = $passwordInput.attr('type') === 'password' ? 'text' : 'password';
            $passwordInput.attr('type', type);

            // Toggle icon
            const $icon = $(this).find('i');
            if (type === 'text') {
                $icon.removeClass('bi-eye').addClass('bi-eye-slash');
                $(this).attr('title', 'Hide password');
            } else {
                $icon.removeClass('bi-eye-slash').addClass('bi-eye');
                $(this).attr('title', 'Show password');
            }
        });
    }

    // Load saved email if remember me was previously checked
    if (localStorage.getItem('rememberMe') === 'true') {
        const savedEmail = localStorage.getItem('savedEmail');
        if (savedEmail) {
            $emailInput.val(savedEmail);
            $rememberMe.prop('checked', true);
            // Trigger focus effect for pre-filled field
            $emailInput.parent().addClass('focused');
        }
    }

    // Enhanced keyboard navigation
    $form.on('keydown', function (e) {
        if (e.key === 'Enter') {
            const $focusedElement = $(document.activeElement);

            // If email field is focused and valid, move to password
            if ($focusedElement.is($emailInput) && $emailInput.val().trim()) {
                e.preventDefault();
                $passwordInput.focus();
            }
            // If password field is focused and form is valid, submit
            else if ($focusedElement.is($passwordInput) && $passwordInput.val().trim()) {
                if ($emailInput.val().trim()) {
                    $form.submit();
                }
            }
        }
    });

    // Add subtle animations on form interaction
    $('.form-control').on('focus', function () {
        $(this).parent().addClass('shadow-sm');
    }).on('blur', function () {
        $(this).parent().removeClass('shadow-sm');
    });

    // Auto-clear validation states when user starts typing
    $('.form-control').on('input', function () {
        $(this).removeClass('is-invalid is-valid');
    });
}); 