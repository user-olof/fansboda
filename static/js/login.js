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

    // Password visibility toggle + last-character delay mask
    function enableDelayedPasswordMask($input, delayMs) {
        const input = $input.get(0);
        const MASK = '\u2022';
        let actual = '';
        let maskTimer = null;
        let revealed = false;
        let applyingDisplay = false;

        function clearMaskTimer() {
            if (maskTimer !== null) {
                clearTimeout(maskTimer);
                maskTimer = null;
            }
        }

        function render(showLast) {
            applyingDisplay = true;
            if (revealed) {
                input.value = actual;
            } else if (!actual) {
                input.value = '';
            } else if (showLast) {
                input.value = MASK.repeat(actual.length - 1) + actual.slice(-1);
            } else {
                input.value = MASK.repeat(actual.length);
            }
            applyingDisplay = false;
        }

        function scheduleMask() {
            clearMaskTimer();
            maskTimer = setTimeout(function () {
                maskTimer = null;
                if (!revealed) {
                    render(false);
                }
            }, delayMs);
        }

        function restoreActual() {
            clearMaskTimer();
            applyingDisplay = true;
            input.value = actual;
            applyingDisplay = false;
        }

        $input.attr({
            type: 'text',
            autocomplete: 'current-password',
            spellcheck: 'false',
            autocapitalize: 'off',
        });

        input.addEventListener('beforeinput', function (event) {
            if (revealed || applyingDisplay) {
                return;
            }

            const type = event.inputType;
            const start = input.selectionStart;
            const end = input.selectionEnd;

            if (type === 'insertText' || type === 'insertFromPaste' || type === 'insertReplacementText') {
                event.preventDefault();
                const insert = event.data || '';
                actual = actual.slice(0, start) + insert + actual.slice(end);
                render(insert.length > 0);
                input.setSelectionRange(start + insert.length, start + insert.length);
                if (insert.length > 0) {
                    scheduleMask();
                }
                return;
            }

            if (type === 'deleteContentBackward') {
                event.preventDefault();
                if (start === end) {
                    if (start === 0) {
                        return;
                    }
                    actual = actual.slice(0, start - 1) + actual.slice(end);
                    render(false);
                    input.setSelectionRange(start - 1, start - 1);
                } else {
                    actual = actual.slice(0, start) + actual.slice(end);
                    render(false);
                    input.setSelectionRange(start, start);
                }
                clearMaskTimer();
                return;
            }

            if (type === 'deleteContentForward') {
                event.preventDefault();
                if (start === end) {
                    actual = actual.slice(0, start) + actual.slice(end + 1);
                } else {
                    actual = actual.slice(0, start) + actual.slice(end);
                }
                render(false);
                input.setSelectionRange(start, start);
                clearMaskTimer();
            }
        });

        input.addEventListener('input', function () {
            if (applyingDisplay) {
                return;
            }
            if (revealed) {
                actual = input.value;
                return;
            }

            const value = input.value;
            if (!value) {
                actual = '';
                clearMaskTimer();
                return;
            }

            const fullyMasked = Array.from(value).every(function (ch) {
                return ch === MASK;
            });
            if (fullyMasked && value.length === actual.length) {
                return;
            }

            const maskedPrefix = MASK.repeat(Math.max(0, value.length - 1));
            const lastVisible = value.slice(0, -1) === maskedPrefix;
            if (lastVisible && value.length === actual.length && value.slice(-1) === actual.slice(-1)) {
                return;
            }

            if (!value.includes(MASK)) {
                actual = value;
                render(true);
                scheduleMask();
                return;
            }

            if (lastVisible && value.length === actual.length + 1) {
                actual += value.slice(-1);
                render(true);
                scheduleMask();
            }
        });

        input.addEventListener('blur', function () {
            if (!revealed) {
                clearMaskTimer();
                render(false);
            }
        });

        $input.closest('form').on('submit', restoreActual);

        return {
            restoreActual: restoreActual,
            isRevealed: function () {
                return revealed;
            },
            setRevealed: function (isRevealed) {
                revealed = isRevealed;
                clearMaskTimer();
                render(false);
            },
        };
    }

    if ($passwordInput.length) {
        const passwordMask = enableDelayedPasswordMask($passwordInput, 1000);

        // Create password toggle button
        const $toggleBtn = $(`
     <button type="button" class="btn btn-link password-toggle p-0" title="Show password" aria-label="Show password">
    <i class="bi bi-eye"></i>
</button>
        `);

        // Add relative positioning to password field container
        $passwordInput.parent().css('position', 'relative');
        $passwordInput.parent().append($toggleBtn);

        $toggleBtn.on('click', function (e) {
            e.preventDefault();
            const showing = !passwordMask.isRevealed();
            passwordMask.setRevealed(showing);

            const $icon = $(this).find('i');
            if (showing) {
                $icon.removeClass('bi-eye').addClass('bi-eye-slash');
                $(this).attr({ title: 'Hide password', 'aria-label': 'Hide password' });
            } else {
                $icon.removeClass('bi-eye-slash').addClass('bi-eye');
                $(this).attr({ title: 'Show password', 'aria-label': 'Show password' });
            }
        });

        $form.on('submit', function () {
            passwordMask.restoreActual();
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