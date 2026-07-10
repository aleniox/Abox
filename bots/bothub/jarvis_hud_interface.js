let isMuted = false;
let isVRMode = false;
let isCamActive = false;
let webcamStream = null;
let faceStream = null;
let isFaceTrackingActive = true;
let audioCtx = null;

// WebSocket connection to backend
let ws = null;
let wsReconnectTimer = null;

function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/ws/chat`;
    ws = new WebSocket(url);
    ws.onopen = () => {
        if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
    };
    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'segment' && data.audio) {
            console.log("[SEGMENT] received:", data.text?.slice(0, 50));
            try {
                const blob = await fetch(`data:audio/wav;base64,${data.audio}`).then(r => r.blob());
                const url = URL.createObjectURL(blob);
                audioQueue.push({ url, text: data.text });
                playNextAudio();
            } catch (e) {
                console.error("[SEGMENT] error:", e);
            }
        }
        if (data.type === 'response') {
            if (pendingResolve) {
                pendingResolve(data);
                pendingResolve = null;
            }
        }
        if (data.type === 'status' && data.text) {
            updateSubtitles(data.text);
        }
    };
    ws.onclose = () => {
        ws = null;
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = () => { ws?.close(); };
}

let pendingResolve = null;

function sendViaWebSocket(message) {
    return new Promise((resolve, reject) => {
        const doSend = () => {
            pendingResolve = resolve;
            ws.send(JSON.stringify({ message }));
            setTimeout(() => {
                if (pendingResolve) {
                    pendingResolve({
                        type: 'response',
                        text: 'Thưa Ngài starkling, yêu cầu đã hết thời gian chờ. Vui lòng thử lại.',
                        search_results: null
                    });
                    pendingResolve = null;
                }
            }, 60000);
        };

        if (ws && ws.readyState === WebSocket.OPEN) {
            doSend();
            return;
        }

        updateSubtitles("Mất kết nối J.A.R.V.I.S., đang thử lại...");
        connectWebSocket();

        const retry = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                clearInterval(retry);
                doSend();
            }
        }, 500);

        setTimeout(() => {
            clearInterval(retry);
            if (!pendingResolve) return;
            pendingResolve({
                type: 'response',
                text: 'Thưa Ngài starkling, không thể kết nối lại J.A.R.V.I.S.. Vui lòng thử lại sau.',
                search_results: null
            });
            pendingResolve = null;
        }, 10000);
    });
}

// Simulative data
let speed = 1.85;
let alt = 2450.0;
let gforce = 1.00;
let corePower = 100;

// Holo-Browser State Variables
let isBrowserOpen = false;
let browserMode = 'ai';
let currentBrowserUrl = 'https://vi.m.wikipedia.org';

function toggleHoloBrowser(forceState) {
    console.log("[TOGGLE] forceState:", forceState, "was:", isBrowserOpen, "->", forceState !== undefined ? forceState : !isBrowserOpen);
    isBrowserOpen = forceState !== undefined ? forceState : !isBrowserOpen;
    playSfx('toggle');

    const singleBrowser = document.getElementById('singleHoloBrowser');
    const targetReticle = document.getElementById('centralTargetReticle');
    const browserL = document.getElementById('browser-L');
    const browserR = document.getElementById('browser-R');
    const reticleL = document.getElementById('reticle-L');
    const reticleR = document.getElementById('reticle-R');
    if (!singleBrowser) return;

    if (isBrowserOpen) {
        singleBrowser.classList.remove('hidden');
        if (targetReticle) targetReticle.classList.add('opacity-10');
        if (browserL) browserL.classList.remove('hidden');
        if (browserR) browserR.classList.remove('hidden');
        if (reticleL) reticleL.classList.add('opacity-10');
        if (reticleR) reticleR.classList.add('opacity-10');
    } else {
        singleBrowser.classList.add('hidden');
        if (targetReticle) targetReticle.classList.remove('opacity-10');
        if (browserL) browserL.classList.add('hidden');
        if (browserR) browserR.classList.add('hidden');
        if (reticleL) reticleL.classList.remove('opacity-10');
        if (reticleR) reticleR.classList.remove('opacity-10');
    }
}

function setBrowserMode(mode) {
    browserMode = mode;
    playSfx('beep');

    const btnAi = document.getElementById('btn-mode-ai-single');
    const btnWeb = document.getElementById('btn-mode-web-single');
    const aiContent = document.getElementById('browserAiContentSingle');
    const iframeSingle = document.getElementById('browserIframeSingle');
    
    const iframeL = document.getElementById('iframe-L');
    const iframeR = document.getElementById('iframe-R');
    const contentL = document.getElementById('browserContentL');
    const contentR = document.getElementById('browserContentR');

    if (mode === 'ai') {
        btnAi.className = "px-1.5 py-0.5 rounded bg-green-400 text-black font-bold";
        btnWeb.className = "px-1.5 py-0.5 rounded border border-green-500/40 text-green-400";
        
        aiContent.classList.remove('hidden');
        iframeSingle.classList.add('hidden');

        iframeL.classList.add('hidden');
        iframeR.classList.add('hidden');
        contentL.classList.remove('hidden');
        contentR.classList.remove('hidden');
    } else {
        btnWeb.className = "px-1.5 py-0.5 rounded bg-green-400 text-black font-bold";
        btnAi.className = "px-1.5 py-0.5 rounded border border-green-500/40 text-green-400";
        
        aiContent.classList.add('hidden');
        iframeSingle.classList.remove('hidden');

        iframeL.classList.remove('hidden');
        iframeR.classList.remove('hidden');
        contentL.classList.add('hidden');
        contentR.classList.add('hidden');
        
        iframeSingle.src = currentBrowserUrl;
        iframeL.src = currentBrowserUrl;
        iframeR.src = currentBrowserUrl;
    }
}

async function executeBrowserSearch(viewType) {
    const inputField = document.getElementById('browserUrlSingle');
    const query = inputField.value.trim();
    if (!query) return;

    if (query.startsWith('http://') || query.startsWith('https://') || !/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]/i.test(query.split(' ').slice(0, 3).join(' '))) {
        let url = query;
        if (!query.startsWith('http://') && !query.startsWith('https://')) {
            url = 'https://' + query;
        }
        currentBrowserUrl = url;
        setBrowserMode('web');
        return;
    }

    playSfx('activate');
    updateSubtitles(`J.A.R.V.I.S đang thực thi lệnh truy vấn: "${query}"...`);

    const aiContent = document.getElementById('browserAiContentSingle');
    const contentL = document.getElementById('browserContentL');
    const contentR = document.getElementById('browserContentR');

    aiContent.innerHTML = `<div class="animate-pulse space-y-2 mt-4 text-green-400">
        <p class="font-bold"><i class="fa-solid fa-spin fa-circle-notch"></i> ĐANG TRUY VẤN STARK GRID...</p>
        <div class="h-1.5 bg-green-950 rounded w-3/4"></div>
        <div class="h-1.5 bg-green-950 rounded w-5/6"></div>
        <div class="h-1.5 bg-green-950 rounded w-1/2"></div>
    </div>`;
    contentL.innerHTML = aiContent.innerHTML;
    contentR.innerHTML = aiContent.innerHTML;

    try {
        const data = await sendViaWebSocket(query);
        if (data.search_results?.length) {
            renderSearchResults(data.search_results, query);
        } else {
            const textHtml = data.text.split('\n').filter(l => l.trim()).map(l =>
                `<p class="text-green-300">${l}</p>`
            ).join('');
            aiContent.innerHTML = `<div class="space-y-1 text-[10px]">${textHtml}</div>`;
            contentL.innerHTML = aiContent.innerHTML;
            contentR.innerHTML = aiContent.innerHTML;
        }
    } catch (err) {
        aiContent.innerHTML = `<div class="space-y-1.5 text-amber-400"><p>Mất kết nối hệ thống.</p></div>`;
        contentL.innerHTML = aiContent.innerHTML;
        contentR.innerHTML = aiContent.innerHTML;
    }
}

function renderSearchResults(results, query) {
    console.log("[RENDER] Called with", results.length, "results, isBrowserOpen:", isBrowserOpen);
    const html = `<div class="space-y-1 text-[10px]">
        <div class="text-white border-b border-green-400/30 pb-1 uppercase font-bold tracking-wide flex justify-between">
            <span>KẾT QUẢ TÌM KIẾM: ${query}</span>
            <span class="text-green-400">GROUNDED DATA</span>
        </div>
        ${results.map((r, i) => `
            <div onclick="openSearchResult('${r.url.replace(/'/g, "\\'")}')" class="border border-green-500/20 rounded p-1.5 cursor-pointer hover:bg-green-950/60 transition-all">
                <div class="text-green-200 font-bold text-[11px]">${i+1}. ${r.title}</div>
                <div class="text-green-500/70 text-[8px] truncate">${r.url}</div>
                <div class="text-green-300/80 mt-0.5 leading-tight">${r.description}</div>
            </div>
        `).join('')}
    </div>`;

    document.getElementById('browserAiContentSingle').innerHTML = html;
    document.getElementById('browserContentL').innerHTML = html;
    document.getElementById('browserContentR').innerHTML = html;

    if (!isBrowserOpen) toggleHoloBrowser();
}

function openSearchResult(url) {
    currentBrowserUrl = url;
    setBrowserMode('web');
    document.getElementById('browserIframeSingle').src = url;
    document.getElementById('iframe-L').src = url;
    document.getElementById('iframe-R').src = url;
    updateSubtitles(`Đã mở: ${url}`);
    playSfx('activate');
}

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playSfx(type) {
    if (isMuted) return;
    try {
        initAudio();
        const now = audioCtx.currentTime;

        if (type === 'beep') {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(1200, now);
            gain.gain.setValueAtTime(0.04, now);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.1);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(now + 0.1);
        } else if (type === 'toggle') {
            const osc1 = audioCtx.createOscillator();
            const osc2 = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            
            osc1.frequency.setValueAtTime(400, now);
            osc1.frequency.linearRampToValueAtTime(800, now + 0.15);
            osc2.frequency.setValueAtTime(200, now);
            osc2.frequency.linearRampToValueAtTime(600, now + 0.15);
            
            gain.gain.setValueAtTime(0.03, now);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);
            
            osc1.connect(gain);
            osc2.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc1.start();
            osc2.start();
            osc1.stop(now + 0.15);
            osc2.stop(now + 0.15);
        } else if (type === 'activate') {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(100, now);
            osc.frequency.exponentialRampToValueAtTime(1200, now + 0.8);
            
            gain.gain.setValueAtTime(0.01, now);
            gain.gain.linearRampToValueAtTime(0.05, now + 0.4);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.8);
            
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(now + 0.8);
        }
    } catch (e) {
        console.warn("Synth error:", e);
    }
}

function toggleSound() {
    isMuted = !isMuted;
    const updateSoundBtn = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (isMuted) {
            el.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
            el.classList.add('text-red-400');
        } else {
            el.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
            el.classList.remove('text-red-400');
        }
    };
    updateSoundBtn('btnMute');
    updateSoundBtn('btnMuteSide');
    if (!isMuted) playSfx('beep');
}

async function toggleWebcam() {
    const video = document.getElementById('arWebcam');
    const faceVideo = document.getElementById('faceWebcam');
    const faceVideoL = document.getElementById('faceWebcam-L');
    const btn = document.getElementById('btnCam');
    const btnSwitch = document.getElementById('btnSwitchCam');

    const faceContainers = ['faceCamContainer', 'faceCamContainer-L'];

    if (isCamActive) {
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcamStream = null;
        }
        if (faceStream) {
            faceStream.getTracks().forEach(track => track.stop());
            faceStream = null;
        }

        video.classList.add('hidden');
        
        faceContainers.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.add('hidden');
        });

        btn.classList.remove('bg-green-400', 'text-black');
        btn.classList.add('text-green-400');
        const camSide = document.getElementById('btnCamSide');
        if (camSide) { camSide.classList.remove('bg-green-400', 'text-black'); camSide.classList.add('text-green-400'); }
        const switchSide = document.getElementById('btnSwitchCamSide');
        if (switchSide) { switchSide.classList.add('hidden'); switchSide.classList.add('bg-cyan-400', 'text-black'); switchSide.classList.remove('text-cyan-400'); }
        if (btnSwitch) {
            btnSwitch.classList.add('hidden');
            btnSwitch.classList.add('bg-cyan-400', 'text-black');
            btnSwitch.classList.remove('text-cyan-400');
        }
        isCamActive = false;
        isFaceTrackingActive = true;
        playSfx('toggle');
        updateSubtitles("Bộ thu camera AR đã tắt. Hệ thống quay về màn nền mô phỏng vũ trụ tối.");
    } else {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            updateSubtitles("Trình duyệt từ chối Camera: Bạn phải dùng HTTPS hoặc localhost để cấp quyền.");
            console.error("Camera access failed: secure context (HTTPS) is required.");
            return;
        }

        try {
            try {
                webcamStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: "environment" } },
                    audio: false
                });
            } catch (e) {
                console.warn("Back camera fail, fallback to default camera", e);
                webcamStream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: false
                });
            }

            video.srcObject = webcamStream;
            await video.play();
            video.classList.remove('hidden');

            try {
                faceStream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: "user" } },
                    audio: false
                });
                
                if (faceVideo) faceVideo.srcObject = faceStream;
                if (faceVideoL) faceVideoL.srcObject = faceStream;

                if (faceVideo) await faceVideo.play();
                if (faceVideoL) await faceVideoL.play();

                if (isFaceTrackingActive) {
                    faceContainers.forEach(id => {
                          const el = document.getElementById(id);
                          if (el) el.classList.remove('hidden');
                    });
                }
                
                updateSubtitles("AR Pass-through và Giao thức Quét Khuôn Mặt (Face Tracking) đã kết nối thành công.");
            } catch (errFace) {
                console.warn("Dual camera mode not fully supported by browser or hardware constraints", errFace);
                updateSubtitles("Kích hoạt AR camera sau. Thiết bị không hỗ trợ chạy hai luồng camera song song.");
            }

            btn.classList.add('bg-green-400', 'text-black');
            btn.classList.remove('text-green-400');
            const camSide2 = document.getElementById('btnCamSide');
            if (camSide2) { camSide2.classList.add('bg-green-400', 'text-black'); camSide2.classList.remove('text-green-400'); }
            const switchSide2 = document.getElementById('btnSwitchCamSide');
            if (switchSide2) { switchSide2.classList.remove('hidden'); switchSide2.classList.add('bg-cyan-400', 'text-black'); switchSide2.classList.remove('text-cyan-400'); }
            if (btnSwitch) {
                btnSwitch.classList.remove('hidden');
                btnSwitch.classList.add('bg-cyan-400', 'text-black');
                btnSwitch.classList.remove('text-cyan-400');
            }
            isCamActive = true;
            playSfx('activate');
        } catch (e) {
            console.error("Camera access failed", e);
            updateSubtitles("Lỗi kết nối camera AR. Kiểm tra quyền truy cập thiết bị hoặc cài đặt trình duyệt.");
        }
    }
}

function toggleFaceTracking() {
    if (!isCamActive || !faceStream) return;
    isFaceTrackingActive = !isFaceTrackingActive;
    playSfx('toggle');

    const faceContainers = ['faceCamContainer', 'faceCamContainer-L'];
    faceContainers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (isFaceTrackingActive) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });

    const btn = document.getElementById('btnSwitchCam');
    const syncFaceBtn = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (isFaceTrackingActive) {
            el.classList.add('bg-cyan-400', 'text-black');
            el.classList.remove('text-cyan-400');
        } else {
            el.classList.remove('bg-cyan-400', 'text-black');
            el.classList.add('text-cyan-400');
        }
    };
    syncFaceBtn('btnSwitchCam');
    syncFaceBtn('btnSwitchCamSide');
    if (isFaceTrackingActive) {
        updateSubtitles("Đã kích hoạt quét gương mặt.");
    } else {
        updateSubtitles("Đã ẩn khung quét gương mặt.");
    }
}

async function toggleVRMode() {
    isVRMode = !isVRMode;
    const singleView = document.getElementById('singleView');
    const vrDualView = document.getElementById('vrDualView');
    const btnVR = document.getElementById('btnVR');

    playSfx('toggle');

    if (isVRMode) {
        singleView.classList.add('hidden');
        vrDualView.classList.remove('hidden');
        btnVR.classList.add('bg-amber-500', 'text-black');
        btnVR.classList.remove('text-amber-400');
        updateSubtitles("Đã kích hoạt chế độ VR SBS. Hãy lắp điện thoại của bạn vào kính thực tế ảo.");

        try {
            const docEl = document.documentElement;
            if (docEl.requestFullscreen) {
                await docEl.requestFullscreen();
            } else if (docEl.webkitRequestFullscreen) {
                await docEl.webkitRequestFullscreen();
            }

            if (screen.orientation && screen.orientation.lock) {
                await screen.orientation.lock('landscape').catch(e => console.warn("Orientation lock rejected:", e));
            }
        } catch (e) {
            console.warn("Fullscreen/orientation request failed:", e);
        }
    } else {
        singleView.classList.remove('hidden');
        vrDualView.classList.add('hidden');
        btnVR.classList.remove('bg-amber-500', 'text-black');
        btnVR.classList.add('text-amber-400');
        updateSubtitles("Đã quay trở lại chế độ xem kính AR đơn màn hình.");

        try {
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                await document.webkitExitFullscreen();
            }

            if (screen.orientation && screen.orientation.unlock) {
                screen.orientation.unlock();
            }
        } catch (e) {
            console.warn("Exit fullscreen failed:", e);
        }
    }
}

let audioQueue = [];
let isAudioPlaying = false;

function ensureAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function playNextAudio() {
    if (isAudioPlaying || audioQueue.length === 0) return;
    isAudioPlaying = true;
    const { url, text } = audioQueue.shift();
    updateSubtitles(text);
    console.log("[PLAY] playing:", text?.slice(0, 50));
    ensureAudioCtx();
    if (audioCtx.state === 'suspended') {
        console.warn("[PLAY] AudioContext suspended, attempting to resume...");
        audioCtx.resume().catch(e => console.warn("Cannot resume:", e));
    }
    fetch(url)
        .then(r => r.arrayBuffer())
        .then(buffer => audioCtx.decodeAudioData(buffer))
        .then(audioBuffer => {
            const source = audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioCtx.destination);
            source.onended = () => {
                URL.revokeObjectURL(url);
                isAudioPlaying = false;
                playNextAudio();
            };
            source.start();
        })
        .catch(e => {
            console.warn("[PLAY] error:", e);
            URL.revokeObjectURL(url);
            isAudioPlaying = false;
            playNextAudio();
        });
}

let micRecognition = null;
let micSilenceTimer = null;
let voiceProcessing = false;
let wakeMode = false;
let wakeRecognition = null;
let wakeRestartCount = 0;
let wakeRestartTimer = null;
let wakeSilenceTimer = null;
let wakeFullText = '';
let isAwake = false;
let awakeIdleTimer = null;
const AWAKE_IDLE_TIMEOUT = 30000;

function triggerVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        updateSubtitles("Trình duyệt hoặc thiết bị của bạn không hỗ trợ công cụ Speech Recognition.");
        return;
    }

    const btnMic = document.getElementById('btnMic');
    const btnMicSide = document.getElementById('btnMicSide');

    // Nếu đang nghe thì stop
    if (micRecognition) {
        try { micRecognition.stop(); } catch(e) {}
        micRecognition = null;
        if (micSilenceTimer) clearTimeout(micSilenceTimer);
        btnMic.innerHTML = '<i class="fa-solid fa-microphone"></i> Ra Lệnh Giọng Nói';
        if (btnMicSide) btnMicSide.innerHTML = '<i class="fa-solid fa-microphone text-xs"></i>';
        return;
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    micRecognition = new SpeechRec();
    micRecognition.lang = 'vi-VN';
    micRecognition.continuous = true;
    micRecognition.interimResults = true;
    micRecognition.maxAlternatives = 1;

    playSfx('beep');
    let finalText = '';
    let hasResult = false;

    micRecognition.onstart = () => {
        btnMic.innerHTML = '<i class="fa-solid fa-microphone text-red-500 animate-pulse"></i> Đang Nghe';
        if (btnMicSide) btnMicSide.innerHTML = '<i class="fa-solid fa-microphone text-xs text-red-500 animate-pulse"></i>';
        updateSubtitles("J.A.R.V.I.S. đang thu tiếng từ Microphone...");
    };

    micRecognition.onresult = (event) => {
        if (micSilenceTimer) clearTimeout(micSilenceTimer);

        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalText += ' ' + event.results[i][0].transcript;
                hasResult = true;
            }
        }
        document.getElementById('voiceCommand').value = finalText.trim();

        // Tự động dừng sau 1.5s im lặng
        micSilenceTimer = setTimeout(() => {
            if (finalText.trim()) {
                voiceProcessing = true;
                processCommand(finalText.trim());
            }
            try { micRecognition.stop(); } catch(e) {}
            micRecognition = null;
        }, 1500);
    };

    micRecognition.onerror = () => {
        if (micSilenceTimer) clearTimeout(micSilenceTimer);
        voiceProcessing = false;
        micRecognition = null;
        btnMic.innerHTML = '<i class="fa-solid fa-microphone"></i> Ra Lệnh Giọng Nói';
        if (btnMicSide) btnMicSide.innerHTML = '<i class="fa-solid fa-microphone text-xs"></i>';
        if (!hasResult) {
            updateSubtitles("Không phát hiện tín hiệu giọng nói.");
        }
    };

    micRecognition.onend = () => {
        if (micSilenceTimer) clearTimeout(micSilenceTimer);
        if (!voiceProcessing && finalText.trim()) {
            document.getElementById('voiceCommand').value = finalText.trim();
            processCommand(finalText.trim());
        }
        voiceProcessing = false;
        micRecognition = null;
        btnMic.innerHTML = '<i class="fa-solid fa-microphone"></i> Ra Lệnh Giọng Nói';
        if (btnMicSide) btnMicSide.innerHTML = '<i class="fa-solid fa-microphone text-xs"></i>';
        if (wakeMode) setTimeout(() => { if (wakeMode) startWakeListening(); }, 500);
    };

    micRecognition.start();
}

function toggleWakeMode() {
    wakeMode = !wakeMode;
    const btn = document.getElementById('btnWake');
    if (!btn) return;
    if (wakeMode) {
        wakeRestartCount = 0;
        startWakeListening();
        btn.classList.add('bg-green-500', 'text-black', 'shadow-[0_0_12px_rgba(0,255,136,0.5)]');
        btn.classList.remove('text-green-400', 'border-green-500/30');
        const icon = btn.querySelector('i');
        if (icon) icon.classList.add('animate-pulse');
        updateSubtitles("Wake mode ON — nói 'Jarvis', 'Luna' hoặc 'Nuna' để ra lệnh.");
    } else {
        stopWakeListening();
        isAwake = false;
        updateWakeStatusUI();
        if (awakeIdleTimer) { clearTimeout(awakeIdleTimer); awakeIdleTimer = null; }
        btn.classList.remove('bg-green-500', 'text-black', 'shadow-[0_0_12px_rgba(0,255,136,0.5)]');
        btn.classList.add('text-green-400');
        const icon = btn.querySelector('i');
        if (icon) icon.classList.remove('animate-pulse');
        if (wakeRestartTimer) { clearTimeout(wakeRestartTimer); wakeRestartTimer = null; }
        if (wakeSilenceTimer) { clearTimeout(wakeSilenceTimer); wakeSilenceTimer = null; }
        wakeFullText = '';
        updateSubtitles("Wake mode OFF.");
    }
}

function startWakeListening() {
    stopWakeListening();
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) return;
    if (wakeRestartCount > 50) {
        wakeMode = false;
        toggleWakeMode();
        updateSubtitles("Wake mode đã tự tắt sau nhiều lần thử lại. Refresh trang để dùng lại.");
        return;
    }
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    wakeRecognition = new SpeechRec();
    wakeRecognition.lang = 'vi-VN';
    wakeRecognition.continuous = true;
    wakeRecognition.interimResults = true;
    wakeRecognition.maxAlternatives = 1;

    const wakeRegex = /(?:hey\s+)?(?:j(?:\.?\s*a\.?\s*r\.?\s*v\.?\s*i\.?\s*s|arvis)|luna|nuna)/i;

    wakeRecognition.onresult = (event) => {
        wakeRestartCount = 0;
        if (wakeSilenceTimer) clearTimeout(wakeSilenceTimer);

        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                wakeFullText += ' ' + event.results[i][0].transcript;
            }
        }
        document.getElementById('voiceCommand').value = wakeFullText.trim();

        wakeSilenceTimer = setTimeout(() => {
            console.log('[WAKE] Before parse - raw text:', wakeFullText);
            const text = wakeFullText.trim().toLowerCase();

            if (isAwake) {
                playSfx('beep');
                stopWakeListening();
                const cmd = wakeFullText.trim();
                if (cmd) {
                    document.getElementById('voiceCommand').value = cmd;
                    processCommand();
                }
                wakeFullText = '';
                return;
            }

            const match = text.match(wakeRegex);
            if (match) {
                console.log('[WAKE] After parse - matched:', match[0], '| afterWake:', text.slice(match.index + match[0].length).trim());
                playSfx('activate');
                updateSubtitles("J.A.R.V.I.S. đã thức!");
                isAwake = true;
                updateWakeStatusUI();
                resetAwakeIdleTimer();
                wakeRestartCount = 0;
                stopWakeListening();
                const afterWake = text.slice(match.index + match[0].length).trim();
                if (afterWake) {
                    document.getElementById('voiceCommand').value = afterWake;
                    processCommand();
                } else {
                    document.getElementById('voiceCommand').value = '';
                    setTimeout(() => triggerVoiceInput(), 300);
                }
            }
            wakeFullText = '';
        }, 1500);
    };

    const scheduleRestart = () => {
        wakeRestartCount++;
        const delay = Math.min(1000 + wakeRestartCount * 500, 10000);
        wakeRestartTimer = setTimeout(() => {
            if (wakeMode) startWakeListening();
        }, delay);
    };

    wakeRecognition.onerror = () => {
        wakeRecognition = null;
        scheduleRestart();
    };

    wakeRecognition.onend = () => {
        wakeRecognition = null;
        scheduleRestart();
    };

    try { wakeRecognition.start(); } catch(e) { scheduleRestart(); }
}

function stopWakeListening() {
    if (wakeRecognition) {
        try { wakeRecognition.stop(); } catch(e) {}
        wakeRecognition = null;
    }
}

function updateWakeStatusUI() {
    const dot = document.getElementById('wakeStatusDot');
    if (!dot) return;
    if (isAwake) {
        dot.className = 'w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_8px_rgba(0,255,136,0.8)] mx-auto mt-0.5 animate-pulse';
    } else {
        dot.className = 'w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_6px_rgba(255,0,0,0.6)] mx-auto mt-0.5';
    }
}

function resetAwakeIdleTimer() {
    if (awakeIdleTimer) clearTimeout(awakeIdleTimer);
    awakeIdleTimer = setTimeout(() => {
        if (wakeMode && isAwake) {
            isAwake = false;
            updateWakeStatusUI();
            stopWakeListening();
            updateSubtitles("J.A.R.V.I.S. đã ngủ. Nói 'Luna' để đánh thức.");
            if (wakeMode) startWakeListening();
        }
    }, AWAKE_IDLE_TIMEOUT);
}

function restartWakeIfAwake() {
    if (isAwake && wakeMode) {
        resetAwakeIdleTimer();
        setTimeout(() => {
            if (wakeMode && isAwake) startWakeListening();
        }, 300);
    }
}

function updateSubtitles(text) {
    const ids = ['subtitle-single', 'subtitle-L', 'subtitle-R'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = text;
            el.parentElement.classList.remove('flash-receive');
            void el.parentElement.offsetWidth;
            el.parentElement.classList.add('flash-receive');
        }
    });
}

function processCommand(customQuery = null) {
    const inputField = document.getElementById('voiceCommand');
    const query = (customQuery || inputField.value).trim();
    if (!query) return;

    inputField.value = "";
    playSfx('beep');

    const lq = query.toLowerCase();
    if (lq.includes("camera") || lq.includes("thực tế ảo")) {
        toggleWebcam();
        restartWakeIfAwake();
        return;
    }
    if (lq.includes("kính vr") || lq.includes("sbs")) {
        toggleVRMode();
        restartWakeIfAwake();
        return;
    }
    if (lq.includes("mở web") || lq.includes("trình duyệt")) {
        if (!isBrowserOpen) toggleHoloBrowser();
        restartWakeIfAwake();
        return;
    }
    if (lq.includes("tắt âm") || lq.includes("bật âm") || lq.includes("mute")) {
        toggleSound();
        restartWakeIfAwake();
        return;
    }

    const singleHoloEl = document.getElementById('singleHoloBrowser');
    const isHolVisible = singleHoloEl && !singleHoloEl.classList.contains('hidden');

    if (isHolVisible) {
        setBrowserMode('ai');
        const loadingHtml = `<div class="animate-pulse space-y-2 mt-4 text-green-400">
            <p class="font-bold"><i class="fa-solid fa-spin fa-circle-notch"></i> ĐANG TRUY VẤN STARK GRID...</p>
            <div class="h-1.5 bg-green-950 rounded w-3/4"></div>
            <div class="h-1.5 bg-green-950 rounded w-5/6"></div>
            <div class="h-1.5 bg-green-950 rounded w-1/2"></div>
        </div>`;
        document.getElementById('browserAiContentSingle').innerHTML = loadingHtml;
        document.getElementById('browserContentL').innerHTML = loadingHtml;
        document.getElementById('browserContentR').innerHTML = loadingHtml;
    }

    sendViaWebSocket(query).then(data => {
        if (data.text) updateSubtitles(data.text);
        if (data.search_results?.length) {
            renderSearchResults(data.search_results, query);
        } else if (isHolVisible && data.text) {
            const textHtml = data.text.split('\n').filter(l => l.trim()).map(l =>
                `<p class="text-green-300">${l}</p>`
            ).join('');
            const textDiv = `<div class="space-y-1 text-xs">${textHtml}</div>`;
            document.getElementById('browserAiContentSingle').innerHTML = textDiv;
            document.getElementById('browserContentL').innerHTML = textDiv;
            document.getElementById('browserContentR').innerHTML = textDiv;
        }
        restartWakeIfAwake();
    }).catch(() => {
        updateSubtitles("Mất kết nối J.A.R.V.I.S. Kiểm tra backend server.");
        if (isHolVisible) {
            document.getElementById('browserAiContentSingle').innerHTML = '<div class="text-amber-400 mt-4"><p>Mất kết nối J.A.R.V.I.S. Kiểm tra backend server.</p></div>';
        }
        restartWakeIfAwake();
    });
}

function updateTelemetryUI() {
    document.getElementById('speed-single').textContent = `Mach ${speed.toFixed(2)}`;
    document.getElementById('speed-L').textContent = `Mach ${speed.toFixed(2)}`;
    document.getElementById('speed-R').textContent = `Mach ${speed.toFixed(2)}`;

    document.getElementById('alt-single').textContent = `${alt.toFixed(1)} m`;
    document.getElementById('alt-L').textContent = `${alt.toFixed(1)} m`;
    document.getElementById('alt-R').textContent = `${alt.toFixed(1)} m`;

    document.getElementById('gforce-single').textContent = `${gforce.toFixed(2)} G`;
    document.getElementById('gforce-L').textContent = `${gforce.toFixed(2)} G`;
    document.getElementById('gforce-R').textContent = `${gforce.toFixed(2)} G`;

    document.getElementById('reactor-single').textContent = `${corePower}%`;
    document.getElementById('reactor-L').textContent = `${corePower}%`;
    document.getElementById('reactor-R').textContent = `${corePower}%`;
}

function runTimers() {
    setInterval(() => {
        const now = new Date();
        const timeString = now.toLocaleTimeString('vi-VN');
        document.getElementById('clock-single').textContent = timeString;
        document.getElementById('clock-L').textContent = timeString;
        document.getElementById('clock-R').textContent = timeString;

        if (isVRMode && window.innerHeight > window.innerWidth) {
            updateSubtitles("Vui lòng xoay ngang điện thoại và TẮT Khóa xoay màn hình (Portrait Lock).");
        }
    }, 1000);

    setInterval(() => {
        if (speed > 0) {
            const variance = (Math.random() - 0.5) * 0.05;
            speed += variance;
            alt += variance * 10;
            gforce = 4.0 + (Math.random() - 0.5) * 0.15;
            updateTelemetryUI();
        }
    }, 500);
}

window.addEventListener('beforeunload', () => {
    wakeMode = false;
    isAwake = false;
    updateWakeStatusUI();
    stopWakeListening();
    if (wakeRestartTimer) { clearTimeout(wakeRestartTimer); wakeRestartTimer = null; }
    if (awakeIdleTimer) { clearTimeout(awakeIdleTimer); awakeIdleTimer = null; }
});

window.onload = function() {
    connectWebSocket();
    runTimers();
    updateTelemetryUI();

    // Resume AudioContext sớm nhất có thể — click đầu tiên
    document.addEventListener('click', () => { initAudio(); }, { once: true });

    document.body.addEventListener('click', function(e) {
        if (isVRMode) {
            if (e.target.closest('.no-trigger-mic')) {
                return;
            }
            triggerVoiceInput();
        }
    });



    document.getElementById('voiceCommand').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            processCommand();
        }
    });

    document.getElementById('browserUrlSingle').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            executeBrowserSearch('single');
        }
    });
};
