// tablet_enrollment.js — Tablet de enrolamiento (Perfect Line II)

const WS_URL = window.TABLET_WS_URL;
const RECONNECT_DELAY_MS = 3000;
const CAPTURE_COOLDOWN_MS = 2500;
const JPEG_QUALITY = 0.9;

const cameraFeed = document.getElementById('camera-feed');
const overlayCanvas = document.getElementById('overlay-canvas');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const idleOverlay = document.getElementById('idle-overlay');
const faceGuide = document.getElementById('face-guide');
const faceGuideOval = document.querySelector('.face-guide-oval');
const hudInstruction = document.getElementById('hud-instruction');
const hudText = document.getElementById('hud-text');

let socket = null;
let reconnectTimer = null;
let cameraStream = null;
let canvasCtx = overlayCanvas.getContext('2d');
let isModelsLoaded = false;
let isCaptureActive = false;
let captureCompleted = false;
let lastCaptureTime = 0;
let detectionLoopRunning = false;
let stableSince = null;

async function loadModels() {
    hudText.textContent = 'Cargando motor de IA...';
    const MODEL_URL = '/static/models';
    await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
    ]);
    isModelsLoaded = true;
}

function resetStability() {
    stableSince = null;
}

async function detectFaceLoop() {
    if (!isCaptureActive || !isModelsLoaded || captureCompleted) {
        detectionLoopRunning = false;
        return;
    }

    if (cameraFeed.paused || cameraFeed.ended) {
        requestAnimationFrame(detectFaceLoop);
        return;
    }

    const displaySize = { width: cameraFeed.videoWidth, height: cameraFeed.videoHeight };
    if (overlayCanvas.width !== displaySize.width) {
        faceapi.matchDimensions(overlayCanvas, displaySize);
    }

    const now = Date.now();
    const canCapture = (now - lastCaptureTime) > CAPTURE_COOLDOWN_MS;

    try {
        const detection = await faceapi.detectSingleFace(
            cameraFeed,
            TabletFaceUtils.detectorOptions()
        ).withFaceLandmarks();
        canvasCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        if (detection && canCapture) {
            const resizedDetection = faceapi.resizeResults(detection, displaySize);

            if (TabletFaceUtils.meetsCaptureCriteria(detection, resizedDetection, cameraFeed, faceGuideOval)) {
                if (stableSince === null) {
                    stableSince = now;
                }

                if (now - stableSince >= TabletFaceUtils.STABILITY_MS) {
                    hudText.textContent = 'Capturando...';
                    sendEnrollmentPhoto();
                    lastCaptureTime = now;
                    captureCompleted = true;
                    resetStability();
                    setTimeout(function () {
                        stopCamera();
                        faceGuide.classList.remove('active');
                        hudInstruction.classList.add('hidden');
                        idleOverlay.classList.remove('hidden');
                        idleOverlay.querySelector('.idle-subtitle').textContent = 'Foto capturada';
                        setStatus('connected', 'Foto lista');
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
        console.error('Error en bucle de enrolamiento:', e);
        resetStability();
    }

    requestAnimationFrame(detectFaceLoop);
}

function startDetectionLoop() {
    if (!detectionLoopRunning && isCaptureActive && !captureCompleted) {
        detectionLoopRunning = true;
        requestAnimationFrame(detectFaceLoop);
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

async function startCamera() {
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    });
    cameraStream = stream;
    cameraFeed.srcObject = stream;
    cameraFeed.classList.remove('hidden');
    overlayCanvas.classList.remove('hidden');
    return new Promise(function (resolve) {
        cameraFeed.addEventListener('loadedmetadata', resolve, { once: true });
    });
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(function (track) {
            track.stop();
        });
        cameraStream = null;
    }
    cameraFeed.srcObject = null;
    cameraFeed.classList.add('hidden');
    overlayCanvas.classList.add('hidden');
    canvasCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function showIdleScreen() {
    idleOverlay.classList.remove('hidden');
    const idleSubtitle = idleOverlay.querySelector('.idle-subtitle');
    if (idleSubtitle) {
        idleSubtitle.textContent = 'Conectada — en espera del encargado en caja';
    }
    faceGuide.classList.remove('active');
    hudInstruction.classList.add('hidden');
    isCaptureActive = false;
    captureCompleted = false;
    detectionLoopRunning = false;
    resetStability();
}

function connectWebSocket() {
    clearTimeout(reconnectTimer);
    socket = new WebSocket(WS_URL);

    socket.onopen = function () {
        setStatus('connected', 'En espera');
    };

    socket.onclose = function () {
        setStatus('disconnected', 'Sin conexión...');
        stopEnrollmentSession();
        reconnectTimer = setTimeout(connectWebSocket, RECONNECT_DELAY_MS);
    };

    socket.onmessage = function (event) {
        try {
            handleServerMessage(JSON.parse(event.data));
        } catch (err) {
            console.error('[Tablet Enrolamiento] Mensaje inválido:', event.data);
        }
    };
}

async function startEnrollmentSession() {
    if (cameraStream) {
        stopCamera();
    }
    idleOverlay.classList.add('hidden');
    faceGuide.classList.add('active');
    hudInstruction.classList.remove('hidden');
    hudText.textContent = 'Coloque su rostro en el óvalo';
    captureCompleted = false;
    isCaptureActive = true;
    resetStability();
    setStatus('connected', 'Capturando');

    try {
        if (!isModelsLoaded) {
            await loadModels();
        }
        await startCamera();
        startDetectionLoop();
    } catch (err) {
        console.error('[Tablet Enrolamiento] Error iniciando sesión:', err);
        hudText.textContent = 'No se pudo acceder a la cámara.';
        setStatus('disconnected', 'Sin cámara');
    }
}

function stopEnrollmentSession() {
    stopCamera();
    showIdleScreen();
    setStatus(socket && socket.readyState === WebSocket.OPEN ? 'connected' : 'disconnected',
        socket && socket.readyState === WebSocket.OPEN ? 'En espera' : 'Sin conexión...');
}

function handleServerMessage(data) {
    if (data.type === 'ENROLLMENT_START') {
        startEnrollmentSession();
    } else if (data.type === 'ENROLLMENT_END') {
        stopEnrollmentSession();
    }
}

function setStatus(state, text) {
    statusDot.className = state;
    statusText.textContent = text;
}

document.addEventListener('DOMContentLoaded', function () {
    showIdleScreen();
    connectWebSocket();
});
