(function () {
    function formatVes(amount) {
        return 'Bs ' + amount.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    window.initBillingPayment = function (config) {
        const select = document.getElementById(config.selectId);
        const btnConfirm = document.getElementById(config.confirmId);
        const priceUsdEl = document.getElementById(config.priceUsdId);
        const priceVesEl = document.getElementById(config.priceVesId);
        const totalVesEl = document.getElementById(config.totalVesId);
        const periodBox = document.getElementById(config.periodBoxId);
        const periodText = document.getElementById(config.periodTextId);
        const alertSuspended = document.getElementById(config.alertSuspendedId);
        const alertFlexible = document.getElementById(config.alertFlexibleId);
        const lateFeeSection = document.getElementById(config.lateFeeSectionId);
        const lateFeeCheck = document.getElementById(config.lateFeeCheckId);
        const lateFeeInput = document.getElementById(config.lateFeeInputId);
        const lateFeeVesEl = document.getElementById(config.lateFeeVesId);
        const cutDaySection = document.getElementById('payment-cut-day-section');
        const cutDayHidden = document.getElementById('payment_cut_day');
        const cutDayDisplay = document.getElementById('payment_cut_day_display');
        const cutDayInitial = document.getElementById('payment_cut_initial');
        const cutDayEditing = document.getElementById('payment_cut_editing');
        const cutDayEditBtn = document.getElementById('payment_cut_day_edit_btn');
        const cutMotivoSection = document.getElementById('payment-cut-motivo-section');
        const cutMotivoPreset = document.getElementById('payment_cut_motivo_preset');
        const cutMotivoCustom = document.getElementById('payment_cut_motivo_custom');
        let paymentCutMotivo = null;

        const tasaDia = config.tasaDia;
        const billingContext = config.billingContext || {};
        const planPreviews = config.planPreviews || {};
        const previewUrl = config.previewUrl || '';
        let lateFeeDefaultApplied = false;
        let previewRequestId = 0;
        let cutDayEditMode = false;

        function getDefaultCutDay() {
            return billingContext.default_cut_day || billingContext.fecha_corte_dia || new Date().getDate();
        }

        function syncCutDayHidden() {
            if (!cutDayHidden || !cutDayDisplay) return;
            cutDayHidden.value = cutDayDisplay.value;
        }

        function getSelectedCutDay() {
            if (cutDayHidden && cutDayHidden.value) {
                return parseInt(cutDayHidden.value, 10);
            }
            return getDefaultCutDay();
        }

        function updateCutMotivoVisibility() {
            if (!cutMotivoSection || !cutDayDisplay || !cutDayInitial) return;
            const changed = parseInt(cutDayDisplay.value, 10) !== parseInt(cutDayInitial.value, 10);
            const showMotivo = cutDayEditMode && changed;
            cutMotivoSection.style.display = showMotivo ? 'block' : 'none';
            if (cutMotivoPreset) {
                cutMotivoPreset.required = showMotivo;
                if (!showMotivo && paymentCutMotivo) {
                    paymentCutMotivo.reset();
                } else if (showMotivo && !paymentCutMotivo && window.initCutDateMotivoFields) {
                    paymentCutMotivo = initCutDateMotivoFields({
                        presetId: 'payment_cut_motivo_preset',
                        customWrapId: 'payment_cut_motivo_custom_wrap',
                        customId: 'payment_cut_motivo_custom',
                    });
                }
            }
            if (cutMotivoCustom) {
                cutMotivoCustom.required = showMotivo &&
                    cutMotivoPreset && cutMotivoPreset.value === '__other__';
            }
        }

        function resetCutDayEditor() {
            cutDayEditMode = false;
            const defaultDay = getDefaultCutDay();
            if (cutDayHidden) cutDayHidden.value = defaultDay;
            if (cutDayInitial) cutDayInitial.value = defaultDay;
            if (cutDayEditing) cutDayEditing.value = '0';
            if (cutDayDisplay) {
                cutDayDisplay.value = defaultDay;
                cutDayDisplay.disabled = true;
            }
            if (cutDayEditBtn) {
                cutDayEditBtn.style.display = '';
            }
            if (cutMotivoPreset) {
                cutMotivoPreset.required = false;
            }
            if (cutMotivoCustom) {
                cutMotivoCustom.required = false;
            }
            if (paymentCutMotivo) {
                paymentCutMotivo.reset();
            }
            if (cutMotivoSection) cutMotivoSection.style.display = 'none';
        }

        function enableCutDayEditor() {
            cutDayEditMode = true;
            if (cutDayEditing) cutDayEditing.value = '1';
            if (cutDayDisplay) {
                cutDayDisplay.disabled = false;
                cutDayDisplay.focus();
                cutDayDisplay.select();
            }
            if (cutDayEditBtn) {
                cutDayEditBtn.style.display = 'none';
            }
            updateCutMotivoVisibility();
        }

        function applyPreviewData(preview, billingType) {
            if (periodBox && periodText && preview.inicio && preview.fin) {
                periodBox.style.display = 'block';
                if (billingType === 'FIXED') {
                    periodText.textContent = 'Periodo: ' + preview.inicio + ' al ' + preview.fin;
                } else {
                    periodText.textContent = 'Válido: ' + preview.inicio + ' al ' + preview.fin;
                }
            } else if (periodBox) {
                periodBox.style.display = 'none';
            }
        }

        function fetchPeriodPreview(planId, billingType) {
            if (!previewUrl || !planId) {
                return;
            }

            if (billingType !== 'FIXED') {
                applyPreviewData(planPreviews[planId] || {}, billingType);
                return;
            }

            const cutDay = getSelectedCutDay();
            if (!cutDay || cutDay < 1 || cutDay > 31) {
                return;
            }

            const requestId = ++previewRequestId;
            const url = previewUrl + '?plan_id=' + encodeURIComponent(planId) +
                '&cut_day=' + encodeURIComponent(cutDay);

            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (requestId !== previewRequestId) {
                        return;
                    }
                    if (data.error) {
                        return;
                    }
                    applyPreviewData(data, billingType);
                })
                .catch(function () {});
        }

        function recalcTotal(cuotaVes) {
            let multaVes = 0;
            if (lateFeeSection && lateFeeSection.style.display !== 'none' && lateFeeCheck && lateFeeCheck.checked && lateFeeInput) {
                const multaUsd = parseFloat(lateFeeInput.value.replace(',', '.')) || 0;
                multaVes = multaUsd * tasaDia;
            }
            if (lateFeeVesEl) lateFeeVesEl.textContent = formatVes(multaVes);
            if (totalVesEl) totalVesEl.textContent = 'Total: ' + formatVes(cuotaVes + multaVes);
        }

        function updatePrice() {
            if (!select || !btnConfirm) return;

            if (!select.value) {
                if (priceUsdEl) priceUsdEl.textContent = config.emptyUsdLabel || 'Precio: $0.00';
                if (priceVesEl) priceVesEl.textContent = 'Bs 0.00';
                if (totalVesEl) totalVesEl.textContent = 'Total: Bs 0.00';
                if (periodBox) periodBox.style.display = 'none';
                if (alertSuspended) alertSuspended.style.display = 'none';
                if (alertFlexible) alertFlexible.style.display = 'none';
                if (lateFeeSection) lateFeeSection.style.display = 'none';
                if (cutDaySection) cutDaySection.style.display = 'none';
                btnConfirm.disabled = true;
                return;
            }

            if (tasaDia <= 0 || isNaN(tasaDia)) {
                alert('Atención: No hay una tasa de cambio configurada en el sistema.');
                btnConfirm.disabled = true;
                return;
            }

            const option = select.options[select.selectedIndex];
            const priceUsd = parseFloat(option.getAttribute('data-usd').replace(',', '.'));
            const billingType = option.getAttribute('data-billing-type');
            const priceVes = priceUsd * tasaDia;

            if (priceUsdEl) {
                priceUsdEl.textContent = (config.usdPrefix || 'Precio: ') + '$' + priceUsd.toFixed(2);
            }
            if (priceVesEl) priceVesEl.textContent = formatVes(priceVes);

            const isFixed = billingType === 'FIXED';
            if (cutDaySection) {
                cutDaySection.style.display = isFixed ? 'block' : 'none';
            }
            if (!isFixed) {
                resetCutDayEditor();
            }

            fetchPeriodPreview(select.value, billingType);

            const showSuspended = isFixed && billingContext.fixed_status === 'SUSPENDED';
            const showFlexibleWarn = billingType === 'FLEXIBLE' && billingContext.warnings_on_flexible_purchase;

            if (alertSuspended) {
                alertSuspended.style.display = showSuspended ? 'block' : 'none';
                if (showSuspended && billingContext.unpaid_period_count > 0) {
                    alertSuspended.textContent =
                        'Suscripción fija suspendida. Periodos impagos (informativo): ' +
                        billingContext.unpaid_period_count + '.';
                }
            }

            if (alertFlexible) {
                alertFlexible.style.display = showFlexibleWarn ? 'block' : 'none';
            }

            if (lateFeeSection && lateFeeCheck && lateFeeInput) {
                lateFeeSection.style.display = showSuspended ? 'block' : 'none';
                if (showSuspended) {
                    if (!lateFeeDefaultApplied) {
                        lateFeeCheck.checked = !!billingContext.default_apply_late_fee;
                        lateFeeDefaultApplied = true;
                    }
                    if (!lateFeeInput.value) {
                        lateFeeInput.value = parseFloat(billingContext.suggested_late_fee_usd || 0).toFixed(2);
                    }
                } else {
                    lateFeeCheck.checked = false;
                    lateFeeDefaultApplied = false;
                }
            }

            recalcTotal(priceVes);
            btnConfirm.disabled = false;
        }

        if (select) {
            select.addEventListener('change', function () {
                resetCutDayEditor();
                updatePrice();
            });
        }
        if (lateFeeCheck) {
            lateFeeCheck.addEventListener('change', function () {
                const option = select.options[select.selectedIndex];
                if (!option || !option.value) return;
                const priceUsd = parseFloat(option.getAttribute('data-usd').replace(',', '.'));
                recalcTotal(priceUsd * tasaDia);
            });
        }
        if (lateFeeInput) {
            lateFeeInput.addEventListener('input', function () {
                const option = select.options[select.selectedIndex];
                if (!option || !option.value) return;
                const priceUsd = parseFloat(option.getAttribute('data-usd').replace(',', '.'));
                recalcTotal(priceUsd * tasaDia);
            });
        }
        if (cutDayDisplay) {
            cutDayDisplay.addEventListener('input', function () {
                syncCutDayHidden();
                updateCutMotivoVisibility();
                const option = select.options[select.selectedIndex];
                if (!option || !option.value) return;
                fetchPeriodPreview(option.value, option.getAttribute('data-billing-type'));
            });
        }
        if (cutDayEditBtn) {
            cutDayEditBtn.addEventListener('click', enableCutDayEditor);
        }

        updatePrice();

        return {
            reset: function () {
                if (select) select.value = '';
                if (lateFeeInput) lateFeeInput.value = '';
                resetCutDayEditor();
                lateFeeDefaultApplied = false;
                updatePrice();
            },
        };
    };
})();
