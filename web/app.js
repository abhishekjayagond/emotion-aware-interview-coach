/**
 * app.js
 * ------
 * Handlers for the frontend Virtual Interview Coach.
 * Connects to SSE (/api/events) for real-time updates and posts actions via fetch.
 * Renders live SVG composure graphs and scales the face tracking overlay dynamically.
 */

// Keep track of composure history points
let composureHistory = [];
const maxHistoryPoints = 60; // ~60 seconds of history

// DOM elements - Views
const sessionView = document.getElementById("session-view");
const reportView = document.getElementById("report-view");

// DOM elements - Session UI
const stageBadge = document.getElementById("stage-badge");
const stageTitle = document.getElementById("stage-title");
const sessionTimer = document.getElementById("session-timer");
const questionCategory = document.getElementById("question-category");
const questionText = document.getElementById("question-text");
const coachCard = document.getElementById("coach-card");
const coachTip = document.getElementById("coach-tip");
const emotionLabel = document.getElementById("emotion-label");
const emotionPct = document.getElementById("emotion-pct");
const confidenceFill = document.getElementById("confidence-fill");
const difficultyPill = document.getElementById("session-difficulty");
const calibrationOverlay = document.getElementById("calibration-overlay");

// DOM elements - Session Metrics
const metricPace = document.getElementById("metric-pace");
const metricPaceDesc = document.getElementById("metric-pace-desc");
const metricFillers = document.getElementById("metric-fillers");
const metricRt = document.getElementById("metric-rt");

// DOM elements - Controls
const btnRestart = document.getElementById("btn-restart");
const btnPause = document.getElementById("btn-pause");
const btnPauseText = document.getElementById("btn-pause-text");
const svgPauseIcon = document.getElementById("svg-pause-icon");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const btnFinish = document.getElementById("btn-finish");

// DOM elements - SVG Elements
const faceBox = document.getElementById("face-box");
const faceTag = document.getElementById("face-tag");
const videoStream = document.getElementById("video-stream");

// DOM elements - Report Dashboard UI
const reportScoreRing = document.getElementById("report-score-ring");
const reportOverallScore = document.getElementById("report-overall-score");
const reportTimestamp = document.getElementById("report-timestamp");
const reportCommScore = document.getElementById("report-comm-score");
const reportConfScore = document.getElementById("report-conf-score");
const reportEyeScore = document.getElementById("report-eye-score");
const reportPaceVal = document.getElementById("report-pace-val");
const reportPaceDesc = document.getElementById("report-pace-desc");
const barComm = document.getElementById("bar-comm");
const barConf = document.getElementById("bar-conf");
const barEye = document.getElementById("bar-eye");
const reportStrengthsList = document.getElementById("report-strengths");
const reportWeaknessesList = document.getElementById("report-weaknesses");
const reportQuestionsTimeline = document.getElementById("report-questions-timeline");
const reportRoadmap = document.getElementById("report-roadmap");
const reportDurationLabel = document.getElementById("report-total-duration");

// Control buttons (Report View)
const btnReportRestart = document.getElementById("btn-report-restart");
const btnReportExit = document.getElementById("btn-report-exit");

// Setup EventSource for SSE
let eventSource = null;

function connectSSE() {
    eventSource = new EventSource("/api/events");

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (Object.keys(data).length === 0) return;
            
            updateSessionUI(data);
        } catch (err) {
            console.error("Error parsing SSE update:", err);
        }
    };

    eventSource.onerror = (err) => {
        console.error("SSE connection dropped. Retrying...");
        // Reconnect after 2 seconds
        setTimeout(() => {
            if (eventSource.readyState === EventSource.CLOSED) {
                connectSSE();
            }
        }, 2000);
    };
}

// ── Update Live Session UI ──────────────────────────────────────────────
function updateSessionUI(state) {
    // 1. View Transition checking
    if (state.show_summary) {
        showSummaryReport();
        return;
    } else {
        sessionView.classList.remove("hidden");
        reportView.classList.add("hidden");
    }

    // Hide calibration overlay once we get valid states
    if (state.state && state.state !== "CALIBRATING") {
        calibrationOverlay.classList.add("hidden");
    } else {
        calibrationOverlay.classList.remove("hidden");
    }

    // 2. Stages & Progress
    stageBadge.textContent = `Stage ${state.stage_idx}/${state.total_stages}`;
    stageTitle.textContent = state.stage_name || "Intro";

    // 3. Question Card
    questionCategory.textContent = `Question #${state.q_count || 1}`;
    questionText.textContent = state.q_text || "Preparing next question...";

    // 4. Timer digits
    const elapsedSecs = Math.floor(state.elapsed || 0);
    const mins = Math.floor(elapsedSecs / 60).toString().padStart(2, "0");
    const secs = (elapsedSecs % 60).toString().padStart(2, "0");
    sessionTimer.textContent = `${mins}:${secs}`;

    // 5. Controls status
    btnPrev.disabled = state.stage_idx <= 1;

    // Update Pause/Resume button state and video overlay
    if (state.is_paused) {
        btnPauseText.textContent = "Resume";
        svgPauseIcon.innerHTML = `<polygon points="5 3 19 12 5 21" fill="currentColor"></polygon>`;
        btnPause.setAttribute("title", "Resume current session");
        videoStream.style.filter = "grayscale(80%) brightness(50%) blur(2px)";
        
        let pausedIndicator = document.getElementById("paused-indicator");
        if (!pausedIndicator) {
            pausedIndicator = document.createElement("div");
            pausedIndicator.id = "paused-indicator";
            pausedIndicator.style.cssText = "position: absolute; font-size: 1.4rem; font-weight: 800; color: white; background: rgba(0,0,0,0.6); padding: 12px 24px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); letter-spacing: 0.1em; pointer-events: none; z-index: 6;";
            pausedIndicator.textContent = "INTERVIEW PAUSED";
            videoStream.parentNode.appendChild(pausedIndicator);
        }
        pausedIndicator.style.display = "block";
    } else {
        btnPauseText.textContent = "Pause";
        svgPauseIcon.innerHTML = `<rect x="6" y="4" width="4" height="16" rx="1"></rect><rect x="14" y="4" width="4" height="16" rx="1"></rect>`;
        btnPause.setAttribute("title", "Pause current session");
        videoStream.style.filter = "none";
        
        const pausedIndicator = document.getElementById("paused-indicator");
        if (pausedIndicator) {
            pausedIndicator.style.display = "none";
        }
    }

    // 6. Live AI Coach Card
    if (state.coaching_tip) {
        coachTip.textContent = state.coaching_tip;
        // Apply color theme dynamically based on emotion color
        const colorHex = state.emotion_color || "#4F46E5";
        coachCard.style.borderLeftColor = colorHex;
    }

    // 7. Behavioral & Emotion metrics
    const currentEmotion = state.emotion || "neutral";
    const cleanEmotion = currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1);
    emotionLabel.textContent = cleanEmotion;
    emotionLabel.className = `emotion-title text-${currentEmotion}`;
    
    difficultyPill.textContent = state.difficulty || "Adaptive (Stable)";
    
    const confPct = Math.round(state.emotion_confidence || 0);
    emotionPct.textContent = `${confPct}% confidence`;
    confidenceFill.style.width = `${confPct}%`;
    
    // Set confidence fill color to match current state
    confidenceFill.style.backgroundColor = state.emotion_color || "#4F46E5";

    // 8. Communication Metrics
    const pace = Math.round(state.speech?.pace_wpm || 0);
    metricPace.textContent = pace > 0 ? pace : "---";
    if (pace > 145) {
        metricPaceDesc.textContent = "Fast tempo - Slow down";
        metricPaceDesc.className = "sm-metric-desc text-danger";
    } else if (pace < 115 && pace > 0) {
        metricPaceDesc.textContent = "Slow tempo - Speak up";
        metricPaceDesc.className = "sm-metric-desc text-warning";
    } else {
        metricPaceDesc.textContent = "Optimal: 120-145 WPM";
        metricPaceDesc.className = "sm-metric-desc";
    }

    metricFillers.textContent = state.speech?.filler_words ?? 0;
    if ((state.speech?.filler_words ?? 0) > 4) {
        metricFillers.className = "sm-metric-value text-danger";
    } else if ((state.speech?.filler_words ?? 0) > 1) {
        metricFillers.className = "sm-metric-value text-warning";
    } else {
        metricFillers.className = "sm-metric-value";
    }

    const rt = (state.speech?.response_time || 0).toFixed(1);
    metricRt.textContent = rt;

    // 9. Face box mapping
    if (state.region && state.region.w > 0 && state.region.h > 0) {
        faceBox.style.display = "block";
        
        // Face coords coordinates relative to python frame dimensions
        const boxX = state.region.x;
        const boxY = state.region.y;
        const boxW = state.region.w;
        const boxH = state.region.h;
        
        const frameW = state.frame_width || 640;
        const frameH = state.frame_height || 480;
        
        // Calculate percentages
        const leftPct = (boxX / frameW) * 100;
        const topPct = (boxY / frameH) * 100;
        const widthPct = (boxW / frameW) * 100;
        const heightPct = (boxH / frameH) * 100;
        
        faceBox.style.left = `${leftPct}%`;
        faceBox.style.top = `${topPct}%`;
        faceBox.style.width = `${widthPct}%`;
        faceBox.style.height = `${heightPct}%`;
        
        faceTag.textContent = cleanEmotion;
        
        if (state.emotion_color) {
            faceBox.style.borderColor = state.emotion_color;
            faceTag.style.backgroundColor = state.emotion_color;
        }
    } else {
        faceBox.style.display = "none";
    }

    // 10. Accumulate live chart point
    if (state.state !== "CALIBRATING" && state.elapsed > 0) {
        // Compose score is 100 - nervousness deduction
        const compScore = Math.max(0, Math.min(100, state.composure_score || 100));
        composureHistory.push(compScore);
        if (composureHistory.length > maxHistoryPoints) {
            composureHistory.shift();
        }
        drawLiveTrendChart();
    }
}

// ── SVG Chart Drawings ──────────────────────────────────────────────────
function drawLiveTrendChart() {
    const chart = document.getElementById("live-trend-chart");
    const pathLine = document.getElementById("chart-line");
    const pathArea = document.getElementById("chart-area");
    
    if (composureHistory.length < 2) return;
    
    const w = 300;
    const h = 100;
    const padding = 5;
    
    const count = composureHistory.length;
    const dx = w / (count - 1);
    
    let pathD = "";
    let areaD = `M 0 ${h}`;
    
    composureHistory.forEach((val, i) => {
        // Map 0-100 composure score to height 0-100
        // Y = 0 is score 100 (top of chart), Y = 100 is score 0 (bottom)
        const x = i * dx;
        const y = padding + ((100 - val) / 100) * (h - 2 * padding);
        
        if (i === 0) {
            pathD += `M ${x} ${y}`;
            areaD += ` L ${x} ${y}`;
        } else {
            pathD += ` L ${x} ${y}`;
            areaD += ` L ${x} ${y}`;
        }
    });
    
    areaD += ` L ${w} ${h} Z`;
    
    pathLine.setAttribute("d", pathD);
    pathArea.setAttribute("d", areaD);
}

// ── Transition to Performance Report View ────────────────────────────────
function showSummaryReport() {
    // Disconnect live stream updates to save bandwidth
    if (eventSource) {
        eventSource.close();
    }

    sessionView.classList.add("hidden");
    reportView.classList.remove("hidden");

    // Fetch report data
    fetch("/api/report")
        .then((res) => res.json())
        .then((data) => {
            populateReportView(data);
        })
        .catch((err) => {
            console.error("Error loading final summary report:", err);
        });
}

function populateReportView(data) {
    if (!data || Object.keys(data).length === 0) return;

    // 1. Overall Score Ring animation
    const score = Math.round(data.overall_score || 80);
    reportOverallScore.textContent = score;
    
    // SVG radial progress logic
    // Circle circumference is 2 * PI * r = 2 * 3.14159 * 40 = 251.2
    const radius = 40;
    const circ = 2 * Math.PI * radius;
    const offset = circ - (score / 100) * circ;
    reportScoreRing.style.strokeDashoffset = offset;

    // Apply color highlights based on score range
    let ringColor = "#4F46E5"; // indigo
    if (score >= 85) ringColor = "#16A34A"; // success green
    else if (score < 60) ringColor = "#DC2626"; // danger red
    reportScoreRing.style.stroke = ringColor;

    // Timestamp formatting
    const date = new Date();
    reportTimestamp.textContent = `Generated on ${date.toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    })}`;

    // 2. Progress bars and text percentages
    const commScore = Math.round(data.communication_score || 0);
    const confScore = Math.round(data.confidence_score || 0);
    const eyeScore = Math.round(data.eye_contact_score || 0);
    
    reportCommScore.textContent = commScore;
    barComm.style.width = `${commScore}%`;
    barComm.style.backgroundColor = getScoreColor(commScore);

    reportConfScore.textContent = confScore;
    barConf.style.width = `${confScore}%`;
    barConf.style.backgroundColor = getScoreColor(confScore);

    reportEyeScore.textContent = eyeScore;
    barEye.style.width = `${eyeScore}%`;
    barEye.style.backgroundColor = getScoreColor(eyeScore);

    // Pace
    const pace = Math.round(data.average_pace_wpm || 130);
    reportPaceVal.textContent = pace;
    if (pace > 145) {
        reportPaceDesc.textContent = "Spoke too fast - aim for 120-140 WPM";
        reportPaceDesc.className = "sm-metric-desc text-danger";
    } else if (pace < 115) {
        reportPaceDesc.textContent = "Spoke too slow - speak with more energy";
        reportPaceDesc.className = "sm-metric-desc text-warning";
    } else {
        reportPaceDesc.textContent = "Optimal pace maintained";
        reportPaceDesc.className = "sm-metric-desc text-success";
    }

    // 3. Strengths and Weaknesses
    reportStrengthsList.innerHTML = "";
    (data.strengths || []).forEach((str) => {
        const li = document.createElement("li");
        li.textContent = str;
        reportStrengthsList.appendChild(li);
    });

    reportWeaknessesList.innerHTML = "";
    (data.weaknesses || []).forEach((weak) => {
        const li = document.createElement("li");
        li.textContent = weak;
        reportWeaknessesList.appendChild(li);
    });

    // 4. Personalized Roadmap Steps
    reportRoadmap.innerHTML = "";
    (data.roadmap || []).forEach((step, idx) => {
        const div = document.createElement("div");
        div.className = "roadmap-step";
        
        const num = document.createElement("div");
        num.className = "step-num";
        num.textContent = idx + 1;
        
        const txt = document.createElement("div");
        txt.className = "step-text";
        txt.textContent = step;
        
        div.appendChild(num);
        div.appendChild(txt);
        reportRoadmap.appendChild(div);
    });

    // 5. Questions Breakdown Timeline
    reportQuestionsTimeline.innerHTML = "";
    (data.question_breakdown || []).forEach((item, idx) => {
        const timelineItem = document.createElement("div");
        timelineItem.className = "timeline-item";

        const header = document.createElement("div");
        header.className = "timeline-header";

        const index = document.createElement("span");
        index.className = "timeline-index";
        index.textContent = `Q${idx + 1}: ${item.category}`;

        const emotion = document.createElement("span");
        emotion.className = `timeline-emotion text-${item.emotion}`;
        emotion.textContent = item.emotion;

        header.appendChild(index);
        header.appendChild(emotion);

        const question = document.createElement("div");
        question.className = "timeline-question";
        question.textContent = item.question;

        const notes = document.createElement("div");
        notes.className = "timeline-notes";
        notes.textContent = item.coaching_notes || "Consistent composure maintained.";

        timelineItem.appendChild(header);
        timelineItem.appendChild(question);
        timelineItem.appendChild(notes);

        reportQuestionsTimeline.appendChild(timelineItem);
    });

    // Duration formatting
    const duration = data.duration_sec || 0;
    const dMins = Math.floor(duration / 60).toString().padStart(2, "0");
    const dSecs = Math.floor(duration % 60).toString().padStart(2, "0");
    reportDurationLabel.textContent = `${dMins}:${dSecs}`;

    // 6. Report SVG Composure Timeline
    drawReportHistoryChart(data.composure_history || []);
}

function getScoreColor(val) {
    if (val >= 85) return "var(--success)";
    if (val >= 70) return "var(--primary)";
    if (val >= 55) return "var(--warning)";
    return "var(--danger)";
}

function drawReportHistoryChart(history) {
    const pathLine = document.getElementById("rep-chart-line");
    const pathArea = document.getElementById("rep-chart-area");
    
    if (history.length < 2) return;
    
    const w = 300;
    const h = 120;
    const padding = 6;
    
    const count = history.length;
    const dx = w / (count - 1);
    
    let pathD = "";
    let areaD = `M 0 ${h}`;
    
    history.forEach((val, i) => {
        const x = i * dx;
        const y = padding + ((100 - val) / 100) * (h - 2 * padding);
        
        if (i === 0) {
            pathD += `M ${x} ${y}`;
            areaD += ` L ${x} ${y}`;
        } else {
            pathD += ` L ${x} ${y}`;
            areaD += ` L ${x} ${y}`;
        }
    });
    
    areaD += ` L ${w} ${h} Z`;
    
    pathLine.setAttribute("d", pathD);
    pathArea.setAttribute("d", areaD);
}

// ── Action Buttons Request Handlers ─────────────────────────────────────
function executeAction(action) {
    fetch(`/api/action/${action}`)
        .then((res) => res.json())
        .then((res) => {
            console.log(`Action [${action}] executed successfully.`, res);
            if (action === "restart") {
                // If restarting from report or session, clear graph cache
                composureHistory = [];
                // Reconnect SSE if it was closed
                if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
                    connectSSE();
                }
            }
        })
        .catch((err) => {
            console.error(`Failed to execute action [${action}]:`, err);
        });
}

// Attach Action listeners
btnRestart.addEventListener("click", () => {
    if (confirm("Are you sure you want to restart the interview? This resets current metrics.")) {
        executeAction("restart");
    }
});
btnPause.addEventListener("click", () => executeAction("pause"));
btnPrev.addEventListener("click", () => executeAction("prev"));
btnNext.addEventListener("click", () => executeAction("next"));
btnFinish.addEventListener("click", () => executeAction("finish"));

btnReportRestart.addEventListener("click", () => {
    executeAction("restart");
});

btnReportExit.addEventListener("click", () => {
    if (confirm("Are you sure you want to exit the application?")) {
        executeAction("exit");
        // Give time for backend to close before displaying notice
        setTimeout(() => {
            document.body.innerHTML = `
                <div style="font-family: 'Inter', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background-color: #F9FAFB; color: #111827;">
                    <div style="background: white; padding: 32px; border-radius: 16px; border: 1px solid rgba(0,0,0,0.06); text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <h2 style="margin-bottom: 8px; font-weight: 700;">Session Terminated</h2>
                        <p style="color: #4B5563; font-size: 0.9rem;">You can now safely close this browser tab.</p>
                    </div>
                </div>
            `;
        }, 300);
    }
});

// Keyboard Shortcuts
document.addEventListener("keydown", (e) => {
    // Avoid triggering shortcuts when focusing inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;

    const isReportVisible = !reportView.classList.contains("hidden");

    if (e.code === "KeyQ" || e.key === "q" || e.key === "Q") {
        e.preventDefault();
        if (isReportVisible) {
            btnReportExit.click();
        } else {
            btnFinish.click();
        }
    } else if (e.code === "KeyR" || e.key === "r" || e.key === "R") {
        e.preventDefault();
        if (isReportVisible) {
            btnReportRestart.click();
        } else {
            btnRestart.click();
        }
    } else if (e.code === "Space" || e.key === " ") {
        if (!isReportVisible) {
            e.preventDefault();
            btnPause.click();
        }
    } else if (e.code === "ArrowRight" || e.key === "ArrowRight") {
        if (!isReportVisible) {
            e.preventDefault();
            btnNext.click();
        }
    } else if (e.code === "ArrowLeft" || e.key === "ArrowLeft") {
        if (!isReportVisible && !btnPrev.disabled) {
            e.preventDefault();
            btnPrev.click();
        }
    } else if (e.code === "Enter" || e.key === "Enter") {
        if (isReportVisible) {
            e.preventDefault();
            btnReportRestart.click();
        }
    }
});

// Initialize on page load
connectSSE();
