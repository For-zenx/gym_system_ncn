
const WS_URL = window.DASHBOARD_WS_URL;
let dashboardSocket = null;
let reconnectTimer = null;
let tabletOnline = false;

function getTabletStatusElements() {
    var widget = document.getElementById('tabletStatusWidget');
    if (!widget) {
        return null;
    }
    return {
        dot: widget.querySelector('.tablet-status-dot-indicator'),
        row: widget.querySelector('.tablet-status-popover-row'),
        statusText: widget.querySelector('.tablet-status-popover-text'),
    };
}

function updateTabletStatus(online) {
    var elements = getTabletStatusElements();
    if (!elements || !elements.dot || !elements.row) {
        return;
    }

    tabletOnline = online;
    elements.dot.classList.toggle('online', online);
    elements.row.classList.toggle('online', online);

    if (elements.statusText) {
        elements.statusText.textContent = online ? 'Online' : 'Offline';
    }

    window.dispatchEvent(new CustomEvent('tabletStatusChanged', {
        detail: { online: online },
    }));
}

function setTabletPopoverOpen(isOpen) {
    var trigger = document.getElementById('tabletStatusTrigger');
    var popover = document.getElementById('tabletStatusPopover');
    if (!trigger || !popover) {
        return;
    }
    trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    popover.hidden = !isOpen;
}

function initTabletStatusPopover() {
    var widget = document.getElementById('tabletStatusWidget');
    var trigger = document.getElementById('tabletStatusTrigger');
    var popover = document.getElementById('tabletStatusPopover');
    if (!widget || !trigger || !popover) {
        return;
    }

    trigger.addEventListener('click', function (event) {
        event.stopPropagation();
        var isOpen = trigger.getAttribute('aria-expanded') === 'true';
        setTabletPopoverOpen(!isOpen);
    });

    document.addEventListener('click', function (event) {
        if (!widget.contains(event.target)) {
            setTabletPopoverOpen(false);
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            setTabletPopoverOpen(false);
        }
    });
}

function connectDashboardWebSocket() {
    clearTimeout(reconnectTimer);
    dashboardSocket = new WebSocket(WS_URL);

    dashboardSocket.onopen = function () {
        console.log('[Dashboard] WebSocket conectado al servidor.');
    };

    dashboardSocket.onclose = function () {
        console.warn('[Dashboard] WebSocket cerrado. Reintentando en 3s...');
        updateTabletStatus(false);
        reconnectTimer = setTimeout(connectDashboardWebSocket, 3000);
    };

    dashboardSocket.onerror = function (error) {
        console.error('[Dashboard] Error en WebSocket:', error);
    };

    dashboardSocket.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'tablet_status') {
                updateTabletStatus(!!data.online);
            } else if (data.type === 'ENROLLMENT_PHOTO') {
                window.dispatchEvent(new CustomEvent('enrollmentPhotoReceived', {
                    detail: { photoType: data.photoType, image: data.image },
                }));
            } else if (data.type === 'ENROLLMENT_TERMS_ACCEPTED') {
                window.dispatchEvent(new CustomEvent('enrollmentTermsAccepted'));
            } else if (data.type === 'NEW_ACCESS_LOG') {
                window.dispatchEvent(new CustomEvent('newAccessLog', { detail: data }));
            }
        } catch (err) {
            console.error('[Dashboard] Error parseando mensaje:', event.data);
        }
    };
}

document.addEventListener('DOMContentLoaded', function () {
    initTabletStatusPopover();
    updateTabletStatus(false);
    if (WS_URL) {
        connectDashboardWebSocket();
    }
});

window.sendDashboardCommand = function (commandData) {
    if (dashboardSocket && dashboardSocket.readyState === WebSocket.OPEN) {
        dashboardSocket.send(JSON.stringify(commandData));
    } else {
        console.warn('[Dashboard] Imposible enviar comando. WebSocket no está abierto.');
    }
};
