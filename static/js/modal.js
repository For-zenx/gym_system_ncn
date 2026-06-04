(function (global) {
    function bindDismissibleModal(overlay, options) {
        if (!overlay) {
            return;
        }
        options = options || {};
        var onClose = options.onClose || function () {
            overlay.classList.remove('show');
        };
        var closeBtn = overlay.querySelector('[data-modal-close]');
        if (closeBtn) {
            closeBtn.addEventListener('click', function (event) {
                event.preventDefault();
                if (options.canClose && !options.canClose()) {
                    return;
                }
                onClose();
            });
        }
        overlay.addEventListener('click', function (event) {
            if (event.target !== overlay) {
                return;
            }
            if (options.allowBackdrop === false) {
                return;
            }
            if (options.canClose && !options.canClose()) {
                return;
            }
            onClose();
        });
    }

    function bindDismissibleModalById(id, options) {
        bindDismissibleModal(document.getElementById(id), options);
    }

    global.bindDismissibleModal = bindDismissibleModal;
    global.bindDismissibleModalById = bindDismissibleModalById;
})(window);
