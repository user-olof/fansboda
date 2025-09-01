/**
 * Electricity Bill Calculator
 * Divides the electricity bill between three services
 */

$(document).ready(function () {
    // Configuration: Define the distribution percentages or ratios
    const DISTRIBUTION = {
        telekom: 0.20, // 20% to Telekom
        johanOchEmilBilservice: 0.512, // 51,2% to Johan och Emil's Bilservice
        jaBilservice: 0.096, // 9,6% to JA Bilservice
        tkMatservice: 0.192 // 19,2% to TK Mätservice
    };

    // Alternative: Equal distribution (uncomment to use)
    // const DISTRIBUTION = {
    //     telekom: 1/3,      // 33.33% each
    //     jaBilservice: 1/3,
    //     tkMatservice: 1/3
    // };

    /**
     * Calculate and distribute electricity bill
     */
    function calculateDistribution() {
        // Get the electricity bill value
        const electricityBill = parseFloat($('#floatingInput').val()) || 0;

        // Calculate distributions
        const telekomAmount = electricityBill * DISTRIBUTION.telekom;
        const johanOchEmilBilserviceAmount = electricityBill * DISTRIBUTION.johanOchEmilBilservice;
        const jaBilserviceAmount = electricityBill * DISTRIBUTION.jaBilservice;
        const tkMatserviceAmount = electricityBill * DISTRIBUTION.tkMatservice;

        // Update the readonly fields with calculated values
        $('#telecomFormControlInput').val(telekomAmount.toFixed(2));
        $('#johanOchEmilBilserviceControlInput').val(johanOchEmilBilserviceAmount.toFixed(2));
        $('#jaBilserviceControlInput').val(jaBilserviceAmount.toFixed(2));
        $('#tkMatserviceControlInput').val(tkMatserviceAmount.toFixed(2));

        // Optional: Add visual feedback
        if (electricityBill > 0) {
            // Add success styling to show calculation is active
            $('.card').removeClass('border-warning').addClass('border-success');

            // Optional: Show total verification
            const total = telekomAmount + jaBilserviceAmount + tkMatserviceAmount;
            console.log(`Distribution: ${electricityBill} → ${total.toFixed(2)} (${total === electricityBill ? '✓' : '⚠️'})`);
        } else {
            // Reset styling when no bill amount
            $('.card').removeClass('border-success border-warning');
        }
    }

    /**
     * Real-time calculation on input change
     */
    $('#floatingInput').on('input keyup change', function () {
        calculateDistribution();

        // Add visual feedback while typing
        const value = parseFloat($(this).val()) || 0;
        if (value > 0) {
            $(this).removeClass('is-invalid').addClass('is-valid');
        } else {
            $(this).removeClass('is-valid is-invalid');
        }
    });

    /**
     * Calculate on page load if there's already a value
     */
    if ($('#floatingInput').val()) {
        calculateDistribution();
    }

    /**
     * Optional: Add clear button functionality
     */
    function addClearButton() {
        if ($('.clear-btn').length === 0) {
            const clearButton = $(`
                <button type="button" class="btn btn-outline-secondary btn-sm mt-2 clear-btn">
                    <i class="bi bi-x-circle me-1"></i>Rensa
                </button>
            `);

            $('#floatingInput').closest('.form-floating').after(clearButton);

            clearButton.on('click', function () {
                $('#floatingInput').val('').removeClass('is-valid is-invalid');
                calculateDistribution();
                $('#floatingInput').focus();
            });
        }
    }

    // Add clear button
    addClearButton();

    /**
     * Optional: Format numbers with Swedish locale
     */
    function formatSwedishNumber(number) {
        return new Intl.NumberFormat('sv-SE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(number);
    }

    /**
 * Enhanced calculation with Swedish formatting (optional)
 */
    function calculateDistributionSwedish() {
        const electricityBill = parseFloat($('#floatingInput').val()) || 0;

        if (electricityBill > 0) {
            const telekomAmount = electricityBill * DISTRIBUTION.telekom;
            const johanOchEmilBilserviceAmount = electricityBill * DISTRIBUTION.johanOchEmilBilservice;
            const jaBilserviceAmount = electricityBill * DISTRIBUTION.jaBilservice;
            const tkMatserviceAmount = electricityBill * DISTRIBUTION.tkMatservice;

            // Use Swedish number formatting (uncomment to use)
            // $('#telecomFormControlInput').val(formatSwedishNumber(telekomAmount));
            // $('#johanOchEmilBilserviceControlInput').val(formatSwedishNumber(johanOchEmilBilserviceAmount));
            // $('#jaBilserviceControlInput').val(formatSwedishNumber(jaBilserviceAmount));
            // $('#tkMatserviceControlInput').val(formatSwedishNumber(tkMatserviceAmount));
        }
    }
});