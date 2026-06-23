// tablet.js — Tablet única NCN (acceso + enrolamiento dual-mode)

const WS_URL = window.TABLET_WS_URL;
const RECONNECT_DELAY_MS = 3000;
const ACCESS_CAPTURE_COOLDOWN_MS = 2000;
const ENROLLMENT_CAPTURE_COOLDOWN_MS = 2500;
const RESULT_DISPLAY_MS = 4000;
const JPEG_QUALITY = 0.9;

const MODE_ACCESS = 'access';
const MODE_ENROLLMENT = 'enrollment';

const cameraFeed = document.getElementById('camera-feed');
const overlayCanvas = document.getElementById('overlay-canvas');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const faceGuide = document.getElementById('face-guide');
const faceGuideOvalAccess = document.querySelector('.access-guide-oval');
const faceGuideOvalEnrollment = document.querySelector('.face-guide-oval');
const accessBottomBanner = document.getElementById('access-bottom-banner');
const accessBannerTitle = document.getElementById('access-banner-title');
const accessBannerSubtitle = document.getElementById('access-banner-subtitle');
const hudInstruction = document.getElementById('hud-instruction');
const hudText = document.getElementById('hud-text');
const termsOverlay = document.getElementById('terms-overlay');
const termsAcceptBtn = document.getElementById('terms-accept-btn');

let currentMode = MODE_ACCESS;
let socket = null;
let reconnectTimer = null;
let cameraStream = null;
let canvasCtx = overlayCanvas.getContext('2d');
let isModelsLoaded = false;
let accessLoopActive = false;

let isProcessingAccess = false;
let isCooldown = false;
let resultTimeout = null;
let serverTimeoutTimer = null;
let lastAccessCaptureTime = 0;

let isEnrollmentCaptureActive = false;
let enrollmentCaptureCompleted = false;
let termsAcceptedThisSession = false;
let skipTermsAfterCapture = false;
let lastEnrollmentCaptureTime = 0;
let enrollmentDetectionRunning = false;
let stableSince = null;

async function loadModels() {
    const MODEL_URL = '/static/models';
    await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
    ]);
    isModelsLoaded = true;
}

function setStatus(state, text) {
    statusDot.className = state;
    statusText.textContent = text;
}

function setHud(text) {
    hudText.textContent = text;
}

function hideTermsScreen() {
    if (termsOverlay) {
        termsOverlay.classList.add('hidden');
    }
}

function showTermsScreen() {
    if (!termsOverlay) {
        finishEnrollmentWaiting();
        return;
    }
    termsOverlay.classList.remove('hidden');
    setStatus('connected', 'Lea y acepte');
}

function resetStability() {
    stableSince = null;
}

function clearAccessTimers() {
    clearTimeout(resultTimeout);
    clearTimeout(serverTimeoutTimer);
}

function setFaceGuideVariant(variant) {
    faceGuide.className = 'face-guide face-guide-access active' + (variant ? ' ' + variant : '');
}

function hideBottomBanner() {
    accessBottomBanner.className = 'access-bottom-banner hidden';
    accessBottomBanner.classList.remove(
        'granted', 'denied_unknown', 'denied_suspended', 'denied_schedule', 'denied_other', 'processing'
    );
}

function showBottomBanner(variant, title, subtitle) {
    hideBottomBanner();
    accessBottomBanner.classList.remove('hidden');
    accessBottomBanner.classList.add(variant);
    accessBannerTitle.textContent = title;
    accessBannerSubtitle.textContent = subtitle || '';
}

function clearAccessResult() {
    setFaceGuideVariant('');
    hideBottomBanner();
    hudInstruction.classList.remove('hidden');
    isProcessingAccess = false;
}

function formatCutLine(data) {
    if (data.covered_until_display) {
        return 'Vigente hasta ' + data.covered_until_display;
    }
    if (data.next_cut_display) {
        return 'Próximo corte: ' + data.next_cut_display;
    }
    if (data.cut_day) {
        return 'Fecha de corte: día ' + data.cut_day + ' de cada mes';
    }
    if (data.days_until_cut != null) {
        const days = data.days_until_cut;
        const dayWord = days === 1 ? 'día' : 'días';
        return 'Faltan ' + days + ' ' + dayWord + ' para el corte';
    }
    if (data.days_membership_left != null) {
        const days = data.days_membership_left;
        const dayWord = days === 1 ? 'día' : 'días';
        return 'Membresía activa: ' + days + ' ' + dayWord;
    }
    return '';
}

function showAccessProcessing() {
    isProcessingAccess = true;
    setFaceGuideVariant('processing');
    hudInstruction.classList.add('hidden');
    showBottomBanner('processing', 'Verificando…', 'Un momento por favor');
}

function showAccessResult(data) {
    if (currentMode !== MODE_ACCESS) {
        return;
    }

    const variant = data.variant || (data.status === 'GRANTED' ? 'granted' : 'denied_unknown');
    isCooldown = true;
    isProcessingAccess = false;
    setFaceGuideVariant(variant);
    hudInstruction.classList.add('hidden');

    let title = '';
    let subtitle = '';

    if (variant === 'granted') {
        title = '¡Aprobado!';
        const name = data.name ? data.name + ' — ' : '';
        const cutLine = formatCutLine(data);
        subtitle = name + (cutLine || 'Acceso concedido');
    } else if (variant === 'denied_unknown') {
        title = 'No reconocido';
        subtitle = data.detail || 'Rostro no registrado en el sistema';
    } else if (variant === 'denied_schedule') {
        title = 'Fuera de horario';
        subtitle = (data.name ? data.name + ' — ' : '') + (data.detail || 'Horario no permitido');
    } else if (variant === 'denied_suspended') {
        title = 'Acceso suspendido';
        const since = data.suspended_since_display
            ? 'Suspendido desde ' + data.suspended_since_display
            : (data.detail || 'Suscripción sin pagar');
        subtitle = (data.name ? data.name + ' — ' : '') + since;
    } else {
        title = 'Acceso denegado';
        subtitle = (data.name ? data.name + ' — ' : '') + (data.detail || data.reason || '');
    }

    showBottomBanner(variant, title, subtitle);

    clearTimeout(resultTimeout);
    const waitMs = variant === 'granted' ? RESULT_DISPLAY_MS : 3200;
    resultTimeout = setTimeout(function () {
        if (currentMode !== MODE_ACCESS) {
            return;
        }
        clearAccessResult();
        setHud('Coloque su rostro en el óvalo');
        setTimeout(function () {
            if (currentMode === MODE_ACCESS) {
                isCooldown = false;
            }
        }, 300);
    }, waitMs);
}

async function accessDetectLoop() {
    if (!accessLoopActive || currentMode !== MODE_ACCESS) {
        return;
    }

    if (!isModelsLoaded || cameraFeed.paused || cameraFeed.ended) {
        requestAnimationFrame(accessDetectLoop);
        return;
    }

    const displaySize = { width: cameraFeed.videoWidth, height: cameraFeed.videoHeight };
    if (overlayCanvas.width !== displaySize.width) {
        faceapi.matchDimensions(overlayCanvas, displaySize);
    }

    const now = Date.now();
    const canCapture = (now - lastAccessCaptureTime) > ACCESS_CAPTURE_COOLDOWN_MS;

    try {
        const detection = await faceapi.detectSingleFace(
            cameraFeed,
            TabletFaceUtils.accessDetectorOptions()
        );
        canvasCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (detection && canCapture && !isProcessingAccess && !isCooldown) {
            const resizedDetection = faceapi.resizeResults(detection, displaySize);

            if (TabletFaceUtils.meetsAccessCaptureCriteria(
                detection, resizedDetection, cameraFeed, faceGuideOvalAccess
            )) {
                showAccessProcessing();
                sendAccessFrame();
                lastAccessCaptureTime = now;
            } else if (!isProcessingAccess) {
                setHud('Coloque su rostro en el óvalo');
            }
        } else if (!detection && !isProcessingAccess) {
            setHud('Coloque su rostro en el óvalo');
        }
    } catch (e) {
        console.error('[Tablet] Error en bucle de acceso:', e);
    }

    requestAnimationFrame(accessDetectLoop);
}

function startAccessLoop() {
    if (!accessLoopActive) {
        accessLoopActive = true;
        requestAnimationFrame(accessDetectLoop);
    }
}

function stopAccessLoop() {
    accessLoopActive = false;
}

function sendAccessFrame() {
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeed.videoWidth;
    canvas.height = cameraFeed.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(cameraFeed, 0, 0, canvas.width, canvas.height);
    const dataURL = canvas.toDataURL('image/jpeg', 0.85);

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'FRAME', image: dataURL }));
        clearTimeout(serverTimeoutTimer);
        serverTimeoutTimer = setTimeout(function () {
            if (isProcessingAccess && currentMode === MODE_ACCESS) {
                showAccessResult({
                    status: 'DENIED',
                    variant: 'denied_unknown',
                    detail: 'Sin respuesta del servidor',
                });
            }
        }, 8000);
    } else {
        showAccessResult({
            status: 'DENIED',
            variant: 'denied_unknown',
            detail: 'Sin conexión con el servidor',
        });
    }
}

async function enrollmentDetectLoop() {
    if (!isEnrollmentCaptureActive || !isModelsLoaded || enrollmentCaptureCompleted
        || currentMode !== MODE_ENROLLMENT) {
        enrollmentDetectionRunning = false;
        return;
    }

    if (cameraFeed.paused || cameraFeed.ended) {
        requestAnimationFrame(enrollmentDetectLoop);
        return;
    }

    const displaySize = { width: cameraFeed.videoWidth, height: cameraFeed.videoHeight };
    if (overlayCanvas.width !== displaySize.width) {
        faceapi.matchDimensions(overlayCanvas, displaySize);
    }

    const now = Date.now();
    const canCapture = (now - lastEnrollmentCaptureTime) > ENROLLMENT_CAPTURE_COOLDOWN_MS;

    try {
        const detection = await faceapi.detectSingleFace(
            cameraFeed,
            TabletFaceUtils.detectorOptions()
        ).withFaceLandmarks();
        canvasCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (detection && canCapture) {
            const resizedDetection = faceapi.resizeResults(detection, displaySize);

            if (TabletFaceUtils.meetsCaptureCriteria(
                detection, resizedDetection, cameraFeed, faceGuideOvalEnrollment
            )) {
                if (stableSince === null) {
                    stableSince = now;
                }

                if (now - stableSince >= TabletFaceUtils.STABILITY_MS) {
                    hudText.textContent = 'Capturando...';
                    sendEnrollmentPhoto();
                    lastEnrollmentCaptureTime = now;
                    enrollmentCaptureCompleted = true;
                    resetStability();
                    setTimeout(function () {
                        stopCameraTracks();
                        faceGuide.classList.remove('active');
                        faceGuide.classList.remove('face-guide-access');
                        hudInstruction.classList.add('hidden');
                        if (skipTermsAfterCapture) {
                            finishEnrollmentWaiting();
                        } else {
                            showTermsScreen();
                        }
                    }, 1200);
                } else {
                    hudText.textContent = 'Coloque su rostro en el óvalo';
                }
            } else {
                resetStability();
                hudText.textContent = 'Coloque su rostro en el óvalo';
            }
        } else if (!detection) {
            resetStability();
        }
    } catch (e) {
        console.error('[Tablet] Error en bucle de enrolamiento:', e);
        resetStability();
    }

    requestAnimationFrame(enrollmentDetectLoop);
}

function startEnrollmentDetectionLoop() {
    if (!enrollmentDetectionRunning && isEnrollmentCaptureActive && !enrollmentCaptureCompleted) {
        enrollmentDetectionRunning = true;
        requestAnimationFrame(enrollmentDetectLoop);
    }
}

function sendEnrollmentPhoto() {
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeed.videoWidth;
    canvas.height = cameraFeed.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(cameraFeed, 0, 0, canvas.width, canvas.height);
    const dataURL = canvas.toDataURL('image/jpeg', JPEG_QUALITY);

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'ENROLLMENT_PHOTO',
            photoType: 'FRONT',
            image: dataURL,
        }));
    }
}

async function ensureCamera() {
    if (cameraStream) {
        return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    });
    cameraStream = stream;
    cameraFeed.srcObject = stream;
    return new Promise(function (resolve) {
        cameraFeed.addEventListener('loadedmetadata', resolve, { once: true });
    });
}

function stopCameraTracks() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(function (track) {
            track.stop();
        });
        cameraStream = null;
    }
    cameraFeed.srcObject = null;
    canvasCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function resetEnrollmentState() {
    isEnrollmentCaptureActive = false;
    enrollmentCaptureCompleted = false;
    termsAcceptedThisSession = false;
    skipTermsAfterCapture = false;
    enrollmentDetectionRunning = false;
    resetStability();
    hideTermsScreen();
}

async function enterAccessMode() {
    currentMode = MODE_ACCESS;
    resetEnrollmentState();
    clearAccessTimers();
    clearAccessResult();
    isCooldown = false;
    isProcessingAccess = false;
    lastAccessCaptureTime = 0;

    faceGuide.classList.add('face-guide-access');
    faceGuide.classList.add('active');
    hudInstruction.classList.remove('hidden');
    setHud('Coloque su rostro en el óvalo');

    try {
        await ensureCamera();
        stopAccessLoop();
        startAccessLoop();
        setStatus('connected', 'Conectado');
    } catch (err) {
        console.error('[Tablet] Error al iniciar cámara:', err);
        setStatus('disconnected', 'Sin cámara');
    }
}

async function startEnrollmentSession() {
    currentMode = MODE_ENROLLMENT;
    clearAccessTimers();
    clearAccessResult();
    stopAccessLoop();
    isCooldown = true;
    isProcessingAccess = false;

    hideTermsScreen();
    faceGuide.classList.add('active');
    faceGuide.classList.remove('face-guide-access');
    hudInstruction.classList.remove('hidden');
    hudText.textContent = 'Coloque su rostro en el óvalo';
    enrollmentCaptureCompleted = false;
    termsAcceptedThisSession = false;
    skipTermsAfterCapture = false;
    isEnrollmentCaptureActive = true;
    resetStability();
    setStatus('connected', 'Capturando');

    try {
        stopCameraTracks();
        await ensureCamera();
        startEnrollmentDetectionLoop();
    } catch (err) {
        console.error('[Tablet] Error iniciando enrolamiento:', err);
        hudText.textContent = 'No se pudo acceder a la cámara.';
        setStatus('disconnected', 'Sin cámara');
    }
}

function finishEnrollmentWaiting() {
    hideTermsScreen();
    faceGuide.classList.remove('active');
    hudInstruction.classList.add('hidden');
    isEnrollmentCaptureActive = false;
    stopCameraTracks();
    setStatus('connected', termsAcceptedThisSession ? 'Listo' : 'Foto lista');
}

function stopEnrollmentSession() {
    enterAccessMode();
}

function acceptTermsOnTablet() {
    if (termsAcceptedThisSession) {
        return;
    }
    termsAcceptedThisSession = true;
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ENROLLMENT_TERMS_ACCEPTED' }));
    }
    finishEnrollmentWaiting();
}

function skipTermsOnTablet() {
    termsAcceptedThisSession = true;
    skipTermsAfterCapture = true;
    hideTermsScreen();
    if (enrollmentCaptureCompleted) {
        finishEnrollmentWaiting();
    }
}

function requireTermsOnTablet() {
    termsAcceptedThisSession = false;
    if (enrollmentCaptureCompleted) {
        showTermsScreen();
        setStatus('connected', 'Lea y acepte');
    }
}

function handleEnrollmentCommand(data) {
    if (data.type === 'ENROLLMENT_START') {
        startEnrollmentSession();
    } else if (data.type === 'ENROLLMENT_END') {
        stopEnrollmentSession();
    } else if (data.type === 'ENROLLMENT_SKIP_TERMS') {
        skipTermsOnTablet();
    } else if (data.type === 'ENROLLMENT_REQUIRE_TERMS') {
        requireTermsOnTablet();
    }
}

function handleAccessResponse(data) {
    if (currentMode !== MODE_ACCESS) {
        return;
    }

    clearTimeout(serverTimeoutTimer);

    if (data.status === 'ERROR') {
        showAccessResult({
            status: 'DENIED',
            variant: 'denied_unknown',
            detail: data.reason || 'Error',
        });
        return;
    }

    if (data.status === 'GRANTED' || data.status === 'DENIED') {
        if (!data.variant) {
            data.variant = data.status === 'GRANTED' ? 'granted' : 'denied_unknown';
        }
        showAccessResult(data);
    }
}

function handleServerMessage(data) {
    if (data.type && String(data.type).indexOf('ENROLLMENT_') === 0) {
        handleEnrollmentCommand(data);
        return;
    }
    handleAccessResponse(data);
}

function connectWebSocket() {
    clearTimeout(reconnectTimer);
    socket = new WebSocket(WS_URL);

    socket.onopen = function () {
        if (currentMode === MODE_ENROLLMENT && !isEnrollmentCaptureActive && !enrollmentCaptureCompleted) {
            enterAccessMode();
        } else if (currentMode === MODE_ACCESS) {
            setStatus('connected', 'Conectado');
        }
    };

    socket.onclose = function () {
        setStatus('disconnected', 'Sin conexión...');
        stopAccessLoop();
        reconnectTimer = setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
    };

    socket.onmessage = function (event) {
        try {
            handleServerMessage(JSON.parse(event.data));
        } catch (err) {
            console.error('[Tablet] Mensaje inválido:', event.data);
        }
    };
}

document.addEventListener('DOMContentLoaded', function () {
    if (termsAcceptBtn) {
        termsAcceptBtn.addEventListener('click', acceptTermsOnTablet);
    }
    loadModels().then(function () {
        return enterAccessMode();
    }).catch(function (err) {
        console.error('[Tablet] Error cargando IA:', err);
        setStatus('disconnected', 'Error IA');
    });
    connectWebSocket();
});
