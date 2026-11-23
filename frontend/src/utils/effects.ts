/**
 * Interactive audio and visual effects for the University AI Companion.
 */

/**
 * Play a gentle, harmonious chime using the Web Audio API without requiring any audio files.
 */
export function playChime() {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;

    const ctx = new AudioContextClass();
    const now = ctx.currentTime;

    // First note (E5 ~ 659Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(659.25, now);
    gain1.gain.setValueAtTime(0.08, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.35);

    // Second note (B5 ~ 987Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(987.77, now + 0.1);
    gain2.gain.setValueAtTime(0.08, now + 0.1);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(now + 0.1);
    osc2.stop(now + 0.55);
  } catch (e) {
    // Audio autoplay restrictions or unsupported
  }
}

/**
 * Trigger celebration confetti particles on the screen.
 */
export function triggerConfetti() {
  const canvas = document.createElement("canvas");
  canvas.style.position = "fixed";
  canvas.style.top = "0";
  canvas.style.left = "0";
  canvas.style.width = "100vw";
  canvas.style.height = "100vh";
  canvas.style.pointerEvents = "none";
  canvas.style.zIndex = "999999";
  document.body.appendChild(canvas);

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    document.body.removeChild(canvas);
    return;
  }

  const dpr = window.devicePixelRatio || 1;
  canvas.width = window.innerWidth * dpr;
  canvas.height = window.innerHeight * dpr;
  ctx.scale(dpr, dpr);

  const colors = ["#10b981", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#3b82f6", "#eab308"];
  const particleCount = 85;
  const particles: Array<{
    x: number;
    y: number;
    w: number;
    h: number;
    color: string;
    vx: number;
    vy: number;
    rotation: number;
    vRot: number;
    opacity: number;
  }> = [];

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: window.innerWidth * Math.random(),
      y: window.innerHeight * -0.2 - Math.random() * 120,
      w: 8 + Math.random() * 10,
      h: 5 + Math.random() * 6,
      color: colors[Math.floor(Math.random() * colors.length)],
      vx: (Math.random() - 0.5) * 4.5,
      vy: 3.5 + Math.random() * 5.5,
      rotation: Math.random() * 360,
      vRot: (Math.random() - 0.5) * 12,
      opacity: 1,
    });
  }

  let animationFrameId: number;
  const startTime = Date.now();

  function animate() {
    if (!ctx) return;
    const elapsed = Date.now() - startTime;
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

    let allDone = true;
    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.rotation += p.vRot;
      if (elapsed > 2000) {
        p.opacity = Math.max(0, 1 - (elapsed - 2000) / 700);
      }

      if (p.y < window.innerHeight && p.opacity > 0) {
        allDone = false;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
    }

    if (allDone || elapsed > 2800) {
      cancelAnimationFrame(animationFrameId);
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
    } else {
      animationFrameId = requestAnimationFrame(animate);
    }
  }

  animationFrameId = requestAnimationFrame(animate);
}

/**
 * Accurately determines if the assistant response indicates the student IS eligible for admission or scholarship.
 * Strictly guarantees that ineligible responses (e.g. below 50% threshold, rejection messages) NEVER trigger the effect.
 */
export function isEligibleResponse(data: { answer?: string; cards?: any[]; eligible?: boolean }): boolean {
  // Explicit server flag wins if provided
  if (data.eligible === true) return true;
  if (data.eligible === false) return false;

  const text = (data.answer || "").toLowerCase();
  if (!text) return false;

  // Strict negative exclusions: If any rejection indicator is found, student is NOT eligible!
  const ineligiblePhrases = [
    "not eligible",
    "not be eligible",
    "ineligible",
    "below 50%",
    "below the 50%",
    "does not meet",
    "do not meet",
    "cannot be provided",
    "sorry, but with",
    "sorry you are not",
    "unfortunately",
  ];
  if (ineligiblePhrases.some((phrase) => text.includes(phrase))) {
    return false;
  }

  // Positive eligibility affirmations
  const eligiblePhrases = [
    "eligible for admission",
    "eligible for our",
    "eligible to apply",
    "qualify for our",
    "qualify for an",
    "qualify for a",
    "qualify for merit",
    "qualify for the",
    "qualifies you for",
    "qualifies for",
    "fully eligible",
    "congratulations on qualifying",
    "you are eligible",
    "you're eligible",
    "top-tier merit scholarship",
    "premier merit scholarship",
    "highest merit scholarship",
    "merit scholarship tier",
    "tuition fee waiver",
    "scholarship reduction",
    "### your scholarship assessment",
    "matching scholarship category",
    "meets the academic eligibility",
    "meet the academic eligibility",
    "meets the eligibility",
    "meet the eligibility",
    "fulfill sr university's academic eligibility",
    "fulfills sr university's academic eligibility",
  ];

  if (eligiblePhrases.some((phrase) => text.includes(phrase))) {
    return true;
  }

  // Check if cards contain calculate_fee or scholarship assessment data
  if (data.cards && Array.isArray(data.cards)) {
    const hasFeeCalc = data.cards.some((c) => c?.type === "calculate_fee" && c?.data?.status === "ok");
    if (hasFeeCalc) {
      return true;
    }
  }

  return false;
}

