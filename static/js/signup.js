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
    const $submitBtn = $('#submitBtn');
    const $termsCheck = $('#termsCheck');
    const $passwordInput = $('#floatingPassword');
    const $passwordConfirmInput = $('#floatingPasswordConfirm');
    const $passwordHelp = $('#passwordHelp');

    // Enable/disable submit button based on terms checkbox
    function updateSubmitButton() {
        $submitBtn.prop('disabled', !$termsCheck.prop('checked'));

        if ($termsCheck.prop('checked')) {
            $submitBtn.removeClass('btn-secondary').addClass('btn-success');
        } else {
            $submitBtn.removeClass('btn-success').addClass('btn-secondary');
        }
    }

    $termsCheck.on('change', updateSubmitButton);
    updateSubmitButton(); // Initial state

    // Form submission handling
    $form.on('submit', function (e) {
        if (!$termsCheck.prop('checked')) {
            e.preventDefault();
            showToast('Please accept the Terms of Service and Privacy Policy to continue.', 'warning');
            return;
        }

        $submitBtn.prop('disabled', true);
        $submitBtn.val('Creating Account...');
        $submitBtn.html('<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Creating Account...');

        // Re-enable after 5 seconds in case of error
        setTimeout(function () {
            $submitBtn.prop('disabled', false);
            $submitBtn.val('Sign Up');
            $submitBtn.html('Sign Up');
        }, 5000);
    });

    // Password strength indicator
    if ($passwordInput.length) {
        $passwordInput.on('input', function () {
            const password = $(this).val();
            let strength = 0;
            let message = '';
            let colorClass = '';

            if (password.length >= 8) strength++;
            if (password.match(/[a-z]/)) strength++;
            if (password.match(/[A-Z]/)) strength++;
            if (password.match(/[0-9]/)) strength++;
            if (password.match(/[^a-zA-Z0-9]/)) strength++;

            switch (strength) {
                case 0:
                case 1:
                    message = 'Very weak password';
                    colorClass = 'text-danger';
                    break;
                case 2:
                    message = 'Weak password';
                    colorClass = 'text-warning';
                    break;
                case 3:
                    message = 'Fair password';
                    colorClass = 'text-info';
                    break;
                case 4:
                    message = 'Good password';
                    colorClass = 'text-success';
                    break;
                case 5:
                    message = 'Strong password';
                    colorClass = 'text-success fw-bold';
                    break;
            }

            if (password.length > 0) {
                $passwordHelp.html(`<small class="${colorClass}"><i class="bi bi-shield-check me-1"></i>${message}</small>`);
            } else {
                $passwordHelp.html('<small class="text-muted"><i class="bi bi-info-circle me-1"></i>Password should be at least 8 characters long</small>');
            }
        });
    }

    // Password confirmation matching
    if ($passwordConfirmInput.length) {
        function checkPasswordMatch() {
            const password = $passwordInput.val();
            const confirmPassword = $passwordConfirmInput.val();

            if (confirmPassword.length > 0) {
                if (password === confirmPassword) {
                    $passwordConfirmInput.removeClass('is-invalid').addClass('is-valid');
                } else {
                    $passwordConfirmInput.removeClass('is-valid').addClass('is-invalid');
                }
            } else {
                $passwordConfirmInput.removeClass('is-valid is-invalid');
            }
        }

        $passwordInput.on('input', checkPasswordMatch);
        $passwordConfirmInput.on('input', checkPasswordMatch);
    }

    // Toast notification function
    window.showToast = function (message, type = 'info') {
        let $toastContainer = $('#toast-container');

        if (!$toastContainer.length) {
            $toastContainer = createToastContainer();
        }

        const $toast = $(`
            <div class="toast align-items-center text-white bg-${type === 'warning' ? 'warning' : type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-exclamation-triangle me-2"></i>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `);

        $toastContainer.append($toast);

        // Initialize Bootstrap toast
        const toast = new bootstrap.Toast($toast[0]);
        toast.show();

        // Remove toast element after it's hidden
        $toast.on('hidden.bs.toast', function () {
            $(this).remove();
        });
    };

    function createToastContainer() {
        const $container = $('<div id="toast-container" class="toast-container position-fixed top-0 end-0 p-3"></div>');
        $('body').append($container);
        return $container;
    }
}); 