// static/js/particle-bg.js
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

// ─── Tuning ────────────────────────────────────────────────────────────────
const REPULSION_STRENGTH = 0.22;
const REPULSION_RADIUS = 2;
const RETURN_STRENGTH = 0.045;
const RETURN_OVERSHOOT = 0.1;
const Z_INFLUENCE = 0.35;
const MOUSE_SMOOTHING = 0.25;
const BLOOM_STRENGTH = 0.45;
const FIXED_MOUSE_Z = -4;

// Performance: fewer particles = smoother on mid-range hardware
const PARTICLE_COUNT = 2200;

// ─── Dark theme colors ─────────────────────────────────────────────────────
const moltenLava = new THREE.Color(0x780000);
const brickRed = new THREE.Color(0xc1121f);
const papayaWhip = new THREE.Color(0xfdf0d5);
const deepSpaceBlue = new THREE.Color(0x003049);
const steelBlue = new THREE.Color(0x669bbc);

// ─── Light theme color ─────────────────────────────────────────────────────
const pureBlack = new THREE.Color(0x0d0d0d);

// ─── Module-level state ────────────────────────────────────────────────────
let scene = null;
let camera = null;
let renderer = null;
let effectComposer = null;
let animationId = null;
let isLightTheme = false;

// Pre-allocated reusable vectors
const _mouseNDC = new THREE.Vector2();
const _rawMouseWorld = new THREE.Vector3();
const _targetMouse = new THREE.Vector3(999, 999, 999);
const _smoothedMouse = new THREE.Vector3(999, 999, 999);
const _dir = new THREE.Vector3();

// ─── Build gradient background texture ────────────────────────────────────
function buildGradientTexture(light) {
  const c = document.createElement("canvas");
  c.width = 2;
  c.height = 512;
  const ctx = c.getContext("2d");
  const grad = ctx.createLinearGradient(0, c.height, 0, 0);

  if (light) {
    grad.addColorStop(0, "#faf9f7");
    grad.addColorStop(1, "#faf9f7");
  } else {
    grad.addColorStop(0, "#fdf0d5");
    grad.addColorStop(1, "#003049");
  }

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, c.width, c.height);

  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

// ─── Build particle sprite texture ────────────────────────────────────────
function buildParticleTexture(light) {
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 64;
  const ctx = c.getContext("2d");
  const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);

  if (light) {
    grad.addColorStop(0, "rgba(10,  10,  10,  1.0)");
    grad.addColorStop(0.35, "rgba(15,  15,  15,  0.75)");
    grad.addColorStop(0.65, "rgba(30,  30,  30,  0.28)");
    grad.addColorStop(0.88, "rgba(60,  60,  60,  0.07)");
    grad.addColorStop(1, "rgba(0,   0,   0,   0)");
  } else {
    grad.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    grad.addColorStop(0.25, "rgba(245, 235, 220, 0.95)");
    grad.addColorStop(0.55, "rgba(180, 100, 80,  0.7)");
    grad.addColorStop(0.85, "rgba(80,  40,  50,  0.35)");
    grad.addColorStop(1, "rgba(30,  20,  40,  0)");
  }

  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 64, 64);

  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}

// ─── Main init ─────────────────────────────────────────────────────────────
function initBackground(container) {
  if (!container) {
    container = document.createElement("div");
    document.body.appendChild(container);
  }

  Object.assign(container.style, {
    position: "fixed",
    top: "0",
    left: "0",
    width: "100%",
    height: "100%",
    zIndex: "0",
    overflow: "hidden",
    pointerEvents: "none",
  });
  while (container.firstChild) container.removeChild(container.firstChild);

  isLightTheme = document.body.classList.contains("light-theme");

  // ── Scene ──
  scene = new THREE.Scene();
  scene.background = buildGradientTexture(isLightTheme);

  // ── Camera ──
  camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    1000,
  );
  camera.position.set(0, 1.5, 14);
  camera.lookAt(0, 0, 0);

  // ── Renderer ──
  renderer = new THREE.WebGLRenderer({
    antialias: false,
    alpha: false,
    powerPreference: "high-performance",
  });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ReinhardToneMapping;
  renderer.toneMappingExposure = 1.05;
  container.appendChild(renderer.domElement);

  // ── Post-processing ──
  const renderPass = new RenderPass(scene, camera);
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(container.clientWidth, container.clientHeight),
    BLOOM_STRENGTH,
    0.25,
    0.12,
  );
  bloomPass.threshold = 0.08;
  bloomPass.strength = BLOOM_STRENGTH;
  bloomPass.radius = 0.55;
  effectComposer = new EffectComposer(renderer);
  effectComposer.addPass(renderPass);
  effectComposer.addPass(bloomPass);

  // ── Particle data (typed arrays for perf) ──
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  const colors = new Float32Array(PARTICLE_COUNT * 3);
  const sizes = new Float32Array(PARTICLE_COUNT);
  const originalPositions = new Float32Array(PARTICLE_COUNT * 3);
  const velX = new Float32Array(PARTICLE_COUNT);
  const velY = new Float32Array(PARTICLE_COUNT);
  const velZ = new Float32Array(PARTICLE_COUNT);
  const driftX = new Float32Array(PARTICLE_COUNT);
  const driftY = new Float32Array(PARTICLE_COUNT);
  const driftZ = new Float32Array(PARTICLE_COUNT);
  const walkX = new Float32Array(PARTICLE_COUNT);
  const walkY = new Float32Array(PARTICLE_COUNT);
  const walkZ = new Float32Array(PARTICLE_COUNT);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const x = (Math.random() - 0.5) * 18;
    const y = (Math.random() - 0.5) * 10;
    const z = (Math.random() - 0.5) * 22 - 4;

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;
    originalPositions[i * 3] = x;
    originalPositions[i * 3 + 1] = y;
    originalPositions[i * 3 + 2] = z;

    driftX[i] = (Math.random() - 0.5) * 0.0008;
    driftY[i] = (Math.random() - 0.5) * 0.0008;
    driftZ[i] = (Math.random() - 0.5) * 0.0006;
    walkX[i] = (Math.random() - 0.5) * 0.0004;
    walkY[i] = (Math.random() - 0.5) * 0.0004;
    walkZ[i] = (Math.random() - 0.5) * 0.0003;

    let color;
    if (isLightTheme) {
      color = pureBlack.clone();
      color.multiplyScalar(0.85 + Math.random() * 0.15);
    } else {
      const rand = Math.random();
      const yNorm = (y + 5) / 10;
      if (yNorm > 0.65) {
        color = (rand < 0.6 ? deepSpaceBlue : steelBlue).clone();
        if (rand < 0.2) color.lerp(moltenLava, 0.15);
      } else if (yNorm < 0.3) {
        if (rand < 0.55) color = moltenLava.clone();
        else if (rand < 0.85) color = brickRed.clone();
        else color = papayaWhip.clone();
        if (rand < 0.2) color.lerp(papayaWhip, 0.25);
      } else {
        color = (rand < 0.5 ? brickRed : steelBlue).clone();
        if (rand < 0.25) color.lerp(moltenLava, 0.3);
        if (rand > 0.75) color.lerp(papayaWhip, 0.15);
      }
      color.multiplyScalar(0.7 + Math.random() * 0.6);
    }

    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
    sizes[i] = 0.5 + Math.random() * 0.5;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geo.setAttribute("size", new THREE.BufferAttribute(sizes, 1));

  const twinklePhases = new Float32Array(PARTICLE_COUNT);
  for (let i = 0; i < PARTICLE_COUNT; i++)
    twinklePhases[i] = Math.random() * Math.PI * 2;
  geo.setAttribute("aPhase", new THREE.BufferAttribute(twinklePhases, 1));

  // ── Shaders ──
  const vertexShader = `
    attribute float aPhase;
    attribute vec3  color;
    attribute float size;
    varying vec3  vColor;
    varying float vAlphaMod;
    uniform float uTime;
    void main() {
      vColor    = color;
      vAlphaMod = 0.82 + 0.18 * sin(uTime * 0.6 + aPhase);
      vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
      gl_PointSize = max(size * (220.0 / -mvPos.z), 0.18);
      gl_Position  = projectionMatrix * mvPos;
    }
  `;

  const fragmentShader = `
    uniform sampler2D uPointTexture;
    varying vec3  vColor;
    varying float vAlphaMod;
    void main() {
      vec4 tex = texture2D(uPointTexture, gl_PointCoord);
      gl_FragColor = vec4(vColor, tex.a * vAlphaMod * 0.92);
    }
  `;

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uPointTexture: { value: buildParticleTexture(isLightTheme) },
      uTime: { value: 0 },
    },
    vertexShader,
    fragmentShader,
    transparent: true,
    depthWrite: true,
    depthTest: true,
    blending: THREE.NormalBlending,
  });

  scene.add(new THREE.Points(geo, mat));

  // ── Mouse listeners ──
  window.addEventListener("mousemove", (e) => {
    _mouseNDC.x = (e.clientX / renderer.domElement.clientWidth) * 2 - 1;
    _mouseNDC.y = -(e.clientY / renderer.domElement.clientHeight) * 2 + 1;
    _rawMouseWorld.set(_mouseNDC.x, _mouseNDC.y, 0.5).unproject(camera);
    _dir.subVectors(_rawMouseWorld, camera.position).normalize();
    const dist = (FIXED_MOUSE_Z - camera.position.z) / _dir.z;
    _targetMouse.copy(camera.position).addScaledVector(_dir, dist);
    _targetMouse.x = Math.max(-9, Math.min(9, _targetMouse.x));
    _targetMouse.y = Math.max(-6, Math.min(6, _targetMouse.y));
  });

  window.addEventListener("mouseleave", () => _targetMouse.set(999, 999, 999));

  // ── Resize ──
  window.addEventListener("resize", () => {
    const w = container.clientWidth,
      h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    effectComposer.setSize(w, h);
  });

  // ── Animation loop ──
  const RADIUS_SQ = REPULSION_RADIUS * REPULSION_RADIUS;
  const posAttr = geo.attributes.position;
  const posArr = posAttr.array;
  let cameraDriftT = 0;
  const initCamPos = camera.position.clone();
  let lastTS = performance.now();

  function animate() {
    animationId = requestAnimationFrame(animate);

    const now = performance.now();
    const delta = Math.min((now - lastTS) / 1000, 0.033) || 0.016;
    lastTS = now;

    _smoothedMouse.lerp(_targetMouse, MOUSE_SMOOTHING);
    mat.uniforms.uTime.value = now / 1000;

    const noMouse = _smoothedMouse.x > 100;
    const mx = _smoothedMouse.x,
      my = _smoothedMouse.y,
      mz = _smoothedMouse.z;
    const d25 = delta * 25,
      d20 = delta * 20;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      const px = posArr[i3],
        py = posArr[i3 + 1],
        pz = posArr[i3 + 2];

      // Random walk
      walkX[i] = Math.max(
        -0.006,
        Math.min(0.006, walkX[i] + (Math.random() - 0.5) * 0.00025),
      );
      walkY[i] = Math.max(
        -0.006,
        Math.min(0.006, walkY[i] + (Math.random() - 0.5) * 0.00025),
      );
      walkZ[i] = Math.max(
        -0.005,
        Math.min(0.005, walkZ[i] + (Math.random() - 0.5) * 0.0002),
      );

      let ax = driftX[i] + walkX[i] * 0.3;
      let ay = driftY[i] + walkY[i] * 0.3;
      let az = driftZ[i] + walkZ[i] * 0.3;

      // Mouse repulsion
      if (!noMouse) {
        const dx = px - mx,
          dy = py - my,
          dz = pz - mz;
        const distSq = dx * dx + dy * dy + dz * dz * Z_INFLUENCE;
        if (distSq < RADIUS_SQ && distSq > 0.001) {
          const t = 1 - Math.sqrt(distSq) / REPULSION_RADIUS;
          const f = (t * t * REPULSION_STRENGTH) / Math.sqrt(distSq);
          ax += dx * f * 1.2;
          ay += dy * f * 1.2;
          az += dz * f * Z_INFLUENCE * 0.8;
        }
      }

      // Velocity + damping
      velX[i] = (velX[i] + ax * d25) * 0.96;
      velY[i] = (velY[i] + ay * d25) * 0.96;
      velZ[i] = (velZ[i] + az * d25) * 0.96;

      let npx = px + velX[i] * d20;
      let npy = py + velY[i] * d20;
      let npz = pz + velZ[i] * d20;

      // Spring return
      const ox = originalPositions[i3],
        oy = originalPositions[i3 + 1],
        oz = originalPositions[i3 + 2];
      velX[i] +=
        (-(npx - ox) * RETURN_STRENGTH + velX[i] * RETURN_OVERSHOOT) * d25;
      velY[i] +=
        (-(npy - oy) * RETURN_STRENGTH + velY[i] * RETURN_OVERSHOOT) * d25;
      velZ[i] +=
        (-(npz - oz) * RETURN_STRENGTH + velZ[i] * RETURN_OVERSHOOT) * d25;

      npx = px + velX[i] * d20;
      npy = py + velY[i] * d20;
      npz = pz + velZ[i] * d20;

      // Boundary bounce
      if (npx < -9.5) {
        npx = -9.47;
        velX[i] *= -0.3;
      }
      if (npx > 9.5) {
        npx = 9.47;
        velX[i] *= -0.3;
      }
      if (npy < -6) {
        npy = -5.97;
        velY[i] *= -0.3;
      }
      if (npy > 6) {
        npy = 5.97;
        velY[i] *= -0.3;
      }
      if (npz < -16) {
        npz = -15.97;
        velZ[i] *= -0.3;
      }
      if (npz > 8) {
        npz = 7.97;
        velZ[i] *= -0.3;
      }

      posArr[i3] = npx;
      posArr[i3 + 1] = npy;
      posArr[i3 + 2] = npz;

      if (Math.random() < 0.0005) {
        originalPositions[i3] = originalPositions[i3] * 0.999 + npx * 0.001;
        originalPositions[i3 + 1] =
          originalPositions[i3 + 1] * 0.999 + npy * 0.001;
        originalPositions[i3 + 2] =
          originalPositions[i3 + 2] * 0.999 + npz * 0.001;
      }
    }
    posAttr.needsUpdate = true;

    // Camera drift
    cameraDriftT += delta * 0.045;
    camera.position.x = initCamPos.x + Math.sin(cameraDriftT * 0.09) * 0.18;
    camera.position.y =
      initCamPos.y + Math.sin(cameraDriftT * 0.15) * 0.05 + 0.03;
    camera.position.z =
      initCamPos.z + Math.sin(cameraDriftT * 0.055) * 0.22 - 0.08;
    camera.lookAt(0, 0.8, 0);

    effectComposer.render();
  }

  animate();
  return renderer;
}

// ─── Theme switch: full reinit ─────────────────────────────────────────────
function updateParticleTheme() {
  const container = document.getElementById("particle-container");
  if (!container) return;

  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }
  if (renderer) {
    renderer.dispose();
    renderer = null;
  }

  while (container.firstChild) container.removeChild(container.firstChild);
  initBackground(container);
}

// ─── Watch body class ─────────────────────────────────────────────────────
const themeObserver = new MutationObserver((mutations) => {
  for (const m of mutations) {
    if (m.attributeName === "class") {
      updateParticleTheme();
      break;
    }
  }
});

// ─── Boot ─────────────────────────────────────────────────────────────────
function boot() {
  const container = document.getElementById("particle-container");
  if (container) {
    initBackground(container);
    themeObserver.observe(document.body, { attributes: true });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}

export { initBackground, updateParticleTheme };
