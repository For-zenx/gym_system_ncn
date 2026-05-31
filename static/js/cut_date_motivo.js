(function () {
    window.initCutDateMotivoFields = function (config) {
        const preset = document.getElementById(config.presetId);
        const customWrap = document.getElementById(config.customWrapId);
        const customInput = document.getElementById(config.customId);
        const otherValue = config.otherValue || '__other__';

        function update() {
            if (!preset) return;
            const isOther = preset.value === otherValue;
            if (customWrap) customWrap.style.display = isOther ? 'block' : 'none';
            if (customInput) customInput.required = isOther;
        }

        if (preset) {
            preset.addEventListener('change', update);
        }
        update();

        return {
            reset: function () {
                if (preset) preset.selectedIndex = 0;
                if (customInput) {
                    customInput.value = '';
                    customInput.required = false;
                }
                update();
            },
        };
    };
})();
