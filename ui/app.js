import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { MindMap } from '/static/js/map-view.js';
import { MusicPlayer } from '/static/js/music-player.js';

// ─── Clock ───
const clockEl = document.getElementById('clock');
function updateClock() {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString('es-ES', { hour12: false });
}
updateClock();
setInterval(updateClock, 1000);

// ─── Scene Setup ───
const container = document.getElementById('globe-container');
const scene = new THREE.Scene();

function createNebulaTexture() {
  const c = document.createElement('canvas');
  c.width = 2048;
  c.height = 1024;
  const ctx = c.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, c.height);
  grad.addColorStop(0, '#05050f');
  grad.addColorStop(0.15, '#0a0018');
  grad.addColorStop(0.3, '#080818');
  grad.addColorStop(0.5, '#0c0820');
  grad.addColorStop(0.7, '#080818');
  grad.addColorStop(0.85, '#0a0018');
  grad.addColorStop(1, '#05050f');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, c.width, c.height);
  const blobs = [
    { x: 0.2, y: 0.3, r: 0.15, color: [100, 0, 200] },
    { x: 0.5, y: 0.5, r: 0.2, color: [0, 50, 180] },
    { x: 0.8, y: 0.4, r: 0.12, color: [150, 0, 100] },
    { x: 0.3, y: 0.7, r: 0.18, color: [0, 80, 150] },
    { x: 0.7, y: 0.6, r: 0.1, color: [80, 0, 160] },
    { x: 0.15, y: 0.55, r: 0.08, color: [120, 0, 80] },
  ];
  for (const b of blobs) {
    const cx = b.x * c.width, cy = b.y * c.height, r = b.r * c.width;
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    const [br, bg, bb] = b.color;
    g.addColorStop(0, `rgba(${br},${bg},${bb},0.35)`);
    g.addColorStop(0.4, `rgba(${br},${bg},${bb},0.12)`);
    g.addColorStop(1, `rgba(${br},${bg},${bb},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
  }
  for (let i = 0; i < 1200; i++) {
    const x = Math.random() * c.width, y = Math.random() * c.height;
    const s = 0.5 + Math.random() * 2, a = 0.15 + Math.random() * 0.6;
    ctx.fillStyle = `rgba(255,255,255,${a})`;
    ctx.beginPath(); ctx.arc(x, y, s, 0, Math.PI * 2); ctx.fill();
  }
  for (let i = 0; i < 60; i++) {
    const x = Math.random() * c.width, y = Math.random() * c.height;
    const s = 0.3 + Math.random() * 0.5, a = 0.1 + Math.random() * 0.2;
    ctx.fillStyle = `rgba(100,150,255,${a})`;
    ctx.beginPath(); ctx.arc(x, y, s, 0, Math.PI * 2); ctx.fill();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  return tex;
}

const camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.1, 200);
camera.position.set(0, 1.2, 4.5);

const renderer = new THREE.WebGLRenderer({
  antialias: true, alpha: false, powerPreference: 'high-performance',
});
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
renderer.shadowMap.enabled = false;
container.appendChild(renderer.domElement);

scene.background = createNebulaTexture();

const pmremGenerator = new THREE.PMREMGenerator(renderer);
scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;

scene.fog = new THREE.FogExp2(0x050510, 0.035);

// ─── Bloom ───
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(container.clientWidth, container.clientHeight), 0.6, 0.3, 0.05
);
composer.addPass(bloomPass);

// ─── Lights ───
scene.add(new THREE.AmbientLight(0x222244, 0.2));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
keyLight.position.set(3, 4, 5);
scene.add(keyLight);
const rimBlue = new THREE.DirectionalLight(0x4488ff, 0.8);
rimBlue.position.set(-3, 1, -4);
scene.add(rimBlue);
const rimGold = new THREE.DirectionalLight(0xff8844, 0.4);
rimGold.position.set(2, -1, -3);
scene.add(rimGold);
const rimTop = new THREE.DirectionalLight(0x00ddff, 0.3);
rimTop.position.set(0, 5, 0);
scene.add(rimTop);

// ─── Floor Grid ───
const FLOOR_Y = -0.75;

const discGeo = new THREE.RingGeometry(0.15, 2.8, 64);
const discMat = new THREE.MeshBasicMaterial({
  color: 0x0044ff, transparent: true, opacity: 0.025, side: THREE.DoubleSide, depthWrite: false,
});
const disc = new THREE.Mesh(discGeo, discMat);
disc.rotation.x = -Math.PI / 2;
disc.position.y = FLOOR_Y;
scene.add(disc);

const RING_COUNT = 12;
const rings = [];
for (let i = 1; i <= RING_COUNT; i++) {
  const r = i * 0.22;
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(r, 0.002, 8, 48),
    new THREE.MeshBasicMaterial({ color: 0x0066ff, transparent: true, opacity: 0.06, depthWrite: false })
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = FLOOR_Y + 0.01;
  scene.add(ring);
  rings.push(ring);
}

const RADIAL_COUNT = 32;
const radPos = [];
for (let i = 0; i < RADIAL_COUNT; i++) {
  const a = (i / RADIAL_COUNT) * Math.PI * 2;
  const x = Math.cos(a) * 2.6, z = Math.sin(a) * 2.6;
  radPos.push(0, FLOOR_Y + 0.01, 0, x, FLOOR_Y + 0.01, z);
}
const radGeo = new THREE.BufferGeometry();
radGeo.setAttribute('position', new THREE.Float32BufferAttribute(radPos, 3));
const radMat = new THREE.LineBasicMaterial({ color: 0x0044ff, transparent: true, opacity: 0.04 });
scene.add(new THREE.LineSegments(radGeo, radMat));

// ─── Light Rays ───
const RAY_COUNT = 8;
const rays = [];
const rayMat = new THREE.MeshBasicMaterial({
  color: 0x4488ff, transparent: true, opacity: 0.02, blending: THREE.AdditiveBlending,
  depthWrite: false, side: THREE.DoubleSide,
});
for (let i = 0; i < RAY_COUNT; i++) {
  const a = (i / RAY_COUNT) * Math.PI * 2;
  const ray = new THREE.Mesh(new THREE.PlaneGeometry(0.04, 5), rayMat.clone());
  ray.position.set(Math.cos(a) * 1.8, 0.8, Math.sin(a) * 1.8);
  ray.lookAt(0, 0.8, 0);
  ray.userData.baseAngle = a;
  scene.add(ray);
  rays.push(ray);
}

// ─── Thoth Ankh ───
function createAnkhShape() {
  const s = new THREE.Shape();
  const sw = 0.035, ch = 0.05, cl = 0.22, lr = 0.22, ly = 0.5, bot = -0.72;
  s.moveTo(-sw, bot);
  s.bezierCurveTo(-sw, ly - lr * 0.75, -sw - lr * 1.2, ly - lr * 0.25, -sw - lr * 1.2, ly + lr * 0.25);
  s.bezierCurveTo(-sw - lr * 1.2, ly + lr * 0.75, -sw, ly + lr * 1.1, 0, ly + lr * 1.15);
  s.bezierCurveTo(sw, ly + lr * 1.1, sw + lr * 1.2, ly + lr * 0.75, sw + lr * 1.2, ly + lr * 0.25);
  s.bezierCurveTo(sw + lr * 1.2, ly - lr * 0.25, sw, ly - lr * 0.75, sw, bot);
  s.lineTo(sw, -0.08 + ch);
  s.lineTo(cl, -0.08 + ch);
  s.lineTo(cl, -0.08);
  s.lineTo(sw, -0.08);
  s.lineTo(sw, bot);
  s.lineTo(-sw, bot);
  s.lineTo(-sw, -0.08);
  s.lineTo(-cl, -0.08);
  s.lineTo(-cl, -0.08 + ch);
  s.closePath();
  return s;
}

const ankhShape = createAnkhShape();
const ankhGeo = new THREE.ExtrudeGeometry(ankhShape, {
  depth: 0.06, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.012, bevelSegments: 6,
});
ankhGeo.center();

const ankhMat = new THREE.MeshStandardMaterial({
  color: 0x00ccff, emissive: 0x004466, emissiveIntensity: 0.5,
  metalness: 0.9, roughness: 0.12, envMapIntensity: 2.5,
});
const ankh = new THREE.Mesh(ankhGeo, ankhMat);

const ankhGroup = new THREE.Group();
ankhGroup.add(ankh);
ankhGroup.position.y = 0.15;
scene.add(ankhGroup);

const glowMat = new THREE.MeshBasicMaterial({
  color: 0x00ddff, transparent: true, opacity: 0.04, side: THREE.BackSide,
});
const ankhGlow = new THREE.Mesh(ankhGeo.clone(), glowMat);
ankhGlow.scale.set(1.5, 1.5, 1.5);
ankhGroup.add(ankhGlow);

const rimMat = new THREE.MeshBasicMaterial({
  color: 0x44eeff, transparent: true, opacity: 0.06, side: THREE.FrontSide, wireframe: true,
});
const ankhWire = new THREE.Mesh(ankhGeo.clone(), rimMat);
ankhWire.scale.set(1.02, 1.02, 1.02);
ankhGroup.add(ankhWire);

// ─── Moon ───
const moonGroup = new THREE.Group();
moonGroup.position.set(0.8, 1.0, 0);

const cresShape = new THREE.Shape();
cresShape.absarc(0, 0, 0.14, -Math.PI * 0.5, Math.PI * 0.5, false);
cresShape.absarc(0, 0.045, 0.11, Math.PI * 0.5, -Math.PI * 0.5, true);
const cresGeo = new THREE.ExtrudeGeometry(cresShape, {
  depth: 0.04, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.005, bevelSegments: 4,
});
cresGeo.center();

const cresMat = new THREE.MeshStandardMaterial({
  color: 0xffbb55, emissive: 0xff6600, emissiveIntensity: 0.3,
  metalness: 0.8, roughness: 0.2, envMapIntensity: 2.0, side: THREE.DoubleSide,
});
const crescent = new THREE.Mesh(cresGeo, cresMat);
crescent.rotation.x = -0.1;
crescent.rotation.z = -0.35;
moonGroup.add(crescent);

const auraMat = new THREE.MeshBasicMaterial({
  color: 0xff8800, transparent: true, opacity: 0.04, side: THREE.BackSide,
});
const aura = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 16), auraMat);
aura.position.z = -0.05;
moonGroup.add(aura);

const moonPCount = 50;
const moonPPos = new Float32Array(moonPCount * 3);
const moonPAngles = new Float32Array(moonPCount);
const moonPRads = new Float32Array(moonPCount);
for (let i = 0; i < moonPCount; i++) {
  moonPAngles[i] = (i / moonPCount) * Math.PI * 2;
  moonPRads[i] = 0.2 + Math.random() * 0.15;
  moonPPos[i*3] = Math.cos(moonPAngles[i]) * moonPRads[i];
  moonPPos[i*3+1] = Math.sin(moonPAngles[i]) * moonPRads[i] * 0.4;
  moonPPos[i*3+2] = (Math.random() - 0.5) * 0.05;
}
const moonPGeo = new THREE.BufferGeometry();
moonPGeo.setAttribute('position', new THREE.BufferAttribute(moonPPos, 3));
const moonPMat = new THREE.PointsMaterial({
  color: 0xffaa44, size: 0.015, transparent: true, opacity: 0.5,
  blending: THREE.AdditiveBlending, depthWrite: false,
});
const moonPParticles = new THREE.Points(moonPGeo, moonPMat);
moonGroup.add(moonPParticles);

const moonRing = new THREE.Mesh(
  new THREE.TorusGeometry(0.22, 0.003, 8, 32),
  new THREE.MeshBasicMaterial({ color: 0xff8800, transparent: true, opacity: 0.1 })
);
moonRing.rotation.x = Math.PI / 2.5;
moonGroup.add(moonRing);
scene.add(moonGroup);

// ─── Energy Rings ───
function createEnergyRing(radius, color, tiltX, tiltZ, yOff, speed) {
  const group = new THREE.Group();
  group.position.y = yOff || 0;

  const core = new THREE.Mesh(
    new THREE.TorusGeometry(radius, 0.01, 24, 64),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.55 })
  );
  group.add(core);

  const glow = new THREE.Mesh(
    new THREE.TorusGeometry(radius, 0.06, 24, 64),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.06, side: THREE.DoubleSide })
  );
  group.add(glow);

  const pCount = 60;
  const pPos = new Float32Array(pCount * 3);
  const pAngles = new Float32Array(pCount);
  for (let i = 0; i < pCount; i++) {
    const a = (i / pCount) * Math.PI * 2;
    pAngles[i] = a;
    pPos[i*3] = Math.cos(a) * radius;
    pPos[i*3+1] = Math.sin(a) * 0.005;
    pPos[i*3+2] = Math.sin(a) * radius;
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  const ringP = new THREE.Points(
    pGeo,
    new THREE.PointsMaterial({
      color, size: 0.025, transparent: true, opacity: 0.5,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
    })
  );
  group.add(ringP);
  group.rotation.x = tiltX;
  group.rotation.z = tiltZ;
  group.userData = { ringP, pAngles, radius, speed };

  const outerGlow = new THREE.Mesh(
    new THREE.TorusGeometry(radius * 1.2, 0.1, 16, 48),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.02, side: THREE.DoubleSide })
  );
  group.add(outerGlow);

  return group;
}

const ring1 = createEnergyRing(1.2, 0x00ddff, Math.PI / 3, 0, 0, 0.004);
scene.add(ring1);
const ring2 = createEnergyRing(1.45, 0x4488ff, Math.PI / 2.3, Math.PI / 5, 0, -0.0025);
scene.add(ring2);
const ring3 = createEnergyRing(0.95, 0x8844ff, Math.PI / 1.6, -Math.PI / 3.5, -0.25, 0.005);
scene.add(ring3);

// ─── Glow Pillars ───
const pillarMat = new THREE.MeshBasicMaterial({
  color: 0x0066ff, transparent: true, opacity: 0.02, side: THREE.DoubleSide,
  blending: THREE.AdditiveBlending, depthWrite: false,
});
for (let i = 0; i < 6; i++) {
  const angle = (i / 6) * Math.PI * 2 + Math.PI / 6;
  const pillar = new THREE.Mesh(new THREE.PlaneGeometry(0.03, 3), pillarMat);
  pillar.position.set(Math.cos(angle) * 1.7, 0.3, Math.sin(angle) * 1.7);
  pillar.rotation.y = -angle;
  scene.add(pillar);
}

// ─── Particles ───
function makeGlowSprite() {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 64;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.15, 'rgba(180,220,255,0.8)');
  g.addColorStop(0.4, 'rgba(80,150,255,0.3)');
  g.addColorStop(0.7, 'rgba(30,80,200,0.1)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

const glowTex = makeGlowSprite();
const PCOUNT = 1200;
const pGeoBg = new THREE.BufferGeometry();
const pPosBg = new Float32Array(PCOUNT * 3);
const pSizesBg = new Float32Array(PCOUNT);
const pBasePos = new Float32Array(PCOUNT * 3);
const pOffsetsBg = new Float32Array(PCOUNT);
const pSpeedsBg = new Float32Array(PCOUNT);
const pColorsBg = new Float32Array(PCOUNT * 3);

for (let i = 0; i < PCOUNT; i++) {
  const r = 0.8 + Math.random() * 4;
  const theta = Math.random() * Math.PI * 2;
  const phi = Math.acos(2 * Math.random() - 1);
  pBasePos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
  pBasePos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.5;
  pBasePos[i * 3 + 2] = r * Math.cos(phi);
  pPosBg[i * 3] = pBasePos[i * 3];
  pPosBg[i * 3 + 1] = pBasePos[i * 3 + 1];
  pPosBg[i * 3 + 2] = pBasePos[i * 3 + 2];
  pSizesBg[i] = 0.3 + Math.random() * 0.8;
  pOffsetsBg[i] = Math.random() * Math.PI * 2;
  pSpeedsBg[i] = 0.1 + Math.random() * 0.3;
  const c = Math.random();
  pColorsBg[i * 3] = c < 0.33 ? 0.2 : c < 0.66 ? 0.4 : 0.6;
  pColorsBg[i * 3 + 1] = c < 0.33 ? 0.6 : c < 0.66 ? 0.8 : 0.3;
  pColorsBg[i * 3 + 2] = c < 0.33 ? 1.0 : c < 0.66 ? 1.0 : 1.0;
}

pGeoBg.setAttribute('position', new THREE.BufferAttribute(pPosBg, 3));
pGeoBg.setAttribute('size', new THREE.BufferAttribute(pSizesBg, 1));
pGeoBg.setAttribute('color', new THREE.BufferAttribute(pColorsBg, 3));

const pMatBg = new THREE.PointsMaterial({
  size: 0.06, map: glowTex, vertexColors: true, transparent: true, opacity: 0.7,
  blending: THREE.AdditiveBlending, sizeAttenuation: true, depthWrite: false,
});
const particles = new THREE.Points(pGeoBg, pMatBg);
scene.add(particles);

let particleReaction = 0;

// ─── News data ───
let newsItems = [];
async function loadNews() {
  try {
    const res = await fetch('/news');
    const data = await res.json();
    if (data.news) newsItems = data.news;
    renderNews();
  } catch { /* silent */ }
}

function renderNews() {
  const el = document.getElementById('news-list');
  const count = document.getElementById('news-count');
  if (!el) return;
  if (!newsItems.length) {
    el.innerHTML = '<div class="news-item"><span class="news-title" style="color:var(--text-dim)">Sin noticias</span></div>';
    if (count) count.textContent = '0';
    return;
  }
  el.innerHTML = newsItems.map((n, i) =>
    `<div class="news-item" style="animation-delay:${i * 0.06}s">
      <span class="news-source">${n.source}</span>
      <span class="news-title">${n.title}</span>
    </div>`
  ).join('');
  if (count) count.textContent = newsItems.length;
}

// Background stars
const bgStarCount = 1500;
const bgStarGeo = new THREE.BufferGeometry();
const bgStarPos = new Float32Array(bgStarCount * 3);
const bgStarCol = new Float32Array(bgStarCount * 3);
for (let i = 0; i < bgStarCount; i++) {
  const r = 30 + Math.random() * 100;
  const theta = Math.random() * Math.PI * 2;
  const phi = Math.acos(2 * Math.random() - 1);
  bgStarPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
  bgStarPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
  bgStarPos[i * 3 + 2] = r * Math.cos(phi);
  const b = 0.15 + Math.random() * 0.35;
  bgStarCol[i * 3] = b;
  bgStarCol[i * 3 + 1] = b;
  bgStarCol[i * 3 + 2] = b + Math.random() * 0.15;
}
bgStarGeo.setAttribute('position', new THREE.BufferAttribute(bgStarPos, 3));
bgStarGeo.setAttribute('color', new THREE.BufferAttribute(bgStarCol, 3));
scene.add(new THREE.Points(
  bgStarGeo,
  new THREE.PointsMaterial({
    size: 0.05, vertexColors: true, transparent: true, opacity: 0.4,
    sizeAttenuation: true, blending: THREE.AdditiveBlending,
  })
));

function advanceRingParticles(ring) {
  const data = ring.userData;
  if (!data || !data.ringP) return;
  const pos = data.ringP.geometry.attributes.position.array;
  const angles = data.pAngles;
  const r = data.radius;
  for (let i = 0; i < angles.length; i++) {
    angles[i] += 0.01 + (i % 5) * 0.001;
    pos[i*3] = Math.cos(angles[i]) * r;
    pos[i*3+1] = Math.sin(angles[i]) * 0.008;
    pos[i*3+2] = Math.sin(angles[i]) * r;
  }
  data.ringP.geometry.attributes.position.needsUpdate = true;
}

// ─── Controls ───
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.04;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.35;
controls.enablePan = false;
controls.minDistance = 2.5;
controls.maxDistance = 8;
controls.zoomSpeed = 0.5;
controls.target.set(0, 0.15, 0);

// ─── Resize ───
function resize() {
  const w = container.clientWidth, h = container.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer.setSize(w, h);
}
window.addEventListener('resize', resize);

// ─── Animation ───
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  ankhGroup.position.y = 0.15 + Math.sin(t * 0.25) * 0.04;
  ankhGroup.rotation.y = Math.sin(t * 0.08) * 0.06;
  const pulseVal = Math.sin(t * 1.2) * 0.5 + 0.5;
  ankhMat.emissiveIntensity = 0.3 + pulseVal * 0.5;
  glowMat.opacity = 0.025 + pulseVal * 0.035;
  rimMat.opacity = 0.04 + Math.sin(t * 2.0) * 0.025;

  cresMat.emissiveIntensity = 0.25 + Math.sin(t * 0.5 + 1) * 0.15;
  moonGroup.rotation.y = t * 0.015;
  moonGroup.position.y = 1.0 + Math.sin(t * 0.2) * 0.03;
  const mp = moonPParticles.geometry.attributes.position.array;
  for (let i = 0; i < moonPCount; i++) {
    moonPAngles[i] += 0.008 + (i % 3) * 0.002;
    mp[i*3] = Math.cos(moonPAngles[i]) * moonPRads[i];
    mp[i*3+1] = Math.sin(moonPAngles[i]) * moonPRads[i] * 0.4;
  }
  moonPParticles.geometry.attributes.position.needsUpdate = true;

  ring1.rotation.y += ring1.userData.speed;
  advanceRingParticles(ring1);
  ring2.rotation.y += ring2.userData.speed;
  advanceRingParticles(ring2);
  ring3.rotation.y += ring3.userData.speed;
  ring3.position.y = -0.25 + Math.sin(t * 0.12) * 0.04;
  advanceRingParticles(ring3);

  const pulse = Math.sin(t * 0.8) * 0.5 + 0.5;
  ring1.children[0].material.opacity = 0.35 + pulse * 0.3;
  ring2.children[0].material.opacity = 0.2 + (1-pulse) * 0.35;
  ring3.children[0].material.opacity = 0.25 + Math.sin(t * 0.6 + 1) * 0.2;

  for (let i = 0; i < RING_COUNT; i++) {
    const phase = i / RING_COUNT;
    rings[i].material.opacity = 0.04 + Math.sin(t * 0.3 + phase * Math.PI * 2) * 0.03 + 0.03;
  }

  for (let i = 0; i < RAY_COUNT; i++) {
    const base = rays[i].userData.baseAngle;
    const a = base + t * 0.04;
    rays[i].position.x = Math.cos(a) * 2;
    rays[i].position.z = Math.sin(a) * 2;
    rays[i].lookAt(0, 0.8, 0);
    rays[i].material.opacity = 0.015 + Math.sin(t * 0.5 + i) * 0.01 + 0.01;
  }

  const pArr = particles.geometry.attributes.position.array;
  for (let i = 0; i < PCOUNT; i++) {
    const idx = i * 3;
    const driftX = Math.cos(t * pSpeedsBg[i] * 0.7 + pOffsetsBg[i]) * 0.00015;
    const driftY = Math.sin(t * pSpeedsBg[i] + pOffsetsBg[i]) * 0.0002;
    if (particleReaction > 0.01) {
      const dx = pArr[idx] - 0;
      const dy = pArr[idx + 1] - 0.15;
      const dz = pArr[idx + 2] - 0;
      const dist = Math.sqrt(dx*dx + dy*dy + dz*dz) + 0.1;
      const force = particleReaction * 0.03;
      pArr[idx] += (dx / dist) * force + driftX;
      pArr[idx + 1] += (dy / dist) * force + driftY;
      pArr[idx + 2] += (dz / dist) * force;
      pArr[idx] += (pBasePos[idx] - pArr[idx]) * 0.02;
      pArr[idx + 1] += (pBasePos[idx + 1] - pArr[idx + 1]) * 0.02;
      pArr[idx + 2] += (pBasePos[idx + 2] - pArr[idx + 2]) * 0.02;
    } else {
      pArr[idx] = pBasePos[idx] + driftX * 20;
      pArr[idx + 1] = pBasePos[idx + 1] + driftY * 20;
      pArr[idx + 2] = pBasePos[idx + 2];
    }
  }
  particles.geometry.attributes.position.needsUpdate = true;

  if (particleReaction > 0.01) {
    particleReaction *= 0.96;
    pMatBg.size = 0.06 + particleReaction * 0.15;
    bloomPass.strength = 0.6 + particleReaction * 0.4;
  } else {
    particleReaction = 0;
    pMatBg.size = 0.06;
    bloomPass.strength = 0.6;
  }

  controls.update();
  composer.render();
}
animate();

// ─── Chat ───
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');
const chatPanel = document.getElementById('chat-panel');
const chatToggle = document.getElementById('chat-toggle');
const chatToast = document.getElementById('chat-toast');
const toastContent = chatToast.querySelector('.toast-content');
let chatCollapsed = false;

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  const existing = chatMessages.querySelector('.typing');
  if (existing) existing.remove();
  const div = document.createElement('div');
  div.className = 'message typing';
  div.textContent = '...';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
  const el = chatMessages.querySelector('.typing');
  if (el) el.remove();
}

function showToast(text) {
  toastContent.textContent = text;
  chatToast.classList.add('visible');
  chatToast.classList.remove('hidden');
  clearTimeout(chatToast._hideTimer);
  chatToast._hideTimer = setTimeout(() => {
    chatToast.classList.remove('visible');
    chatToast.classList.add('hidden');
  }, 5000);
}

function triggerReaction() {
  particleReaction = 1;
}

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg) return;
  addMessage('user', msg);
  chatInput.value = '';
  chatInput.disabled = true;
  showTyping();
  let fullReply = '';
  let assistantDiv = null;
  try {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, session_id: 'default' }),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n');
      buffer = parts.pop() || '';
      for (const line of parts) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (currentEvent === 'token' && data.token) {
            fullReply += data.token;
            if (!assistantDiv) {
              hideTyping();
              assistantDiv = document.createElement('div');
              assistantDiv.className = 'message assistant';
              chatMessages.appendChild(assistantDiv);
            }
            assistantDiv.textContent = fullReply;
            chatMessages.scrollTop = chatMessages.scrollHeight;
          } else if (currentEvent === 'done' && data.reply) {
            if (!assistantDiv) {
              hideTyping();
              addMessage('assistant', data.reply);
            } else {
              assistantDiv.textContent = data.reply;
            }
            fullReply = data.reply;
            triggerReaction();
            if (chatCollapsed) showToast(data.reply);
          } else if (currentEvent === 'tool_calls_start' && data.interim) {
            const toolMsg = data.interim || '[usando herramientas...]';
            hideTyping();
            addMessage('assistant', toolMsg + ' 🔧');
            fullReply = toolMsg;
          } else if (currentEvent === 'error' && data.error) {
            hideTyping();
            addMessage('assistant', '[Error: ' + data.error + ']');
          }
        }
      }
    }
  } catch {
    hideTyping();
    if (!fullReply) addMessage('assistant', '[Error de conexión]');
  }
  chatInput.disabled = false;
  chatInput.focus();
}

chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });

// ─── Chat Toggle ───
chatToggle.addEventListener('click', () => {
  chatCollapsed = !chatCollapsed;
  chatPanel.classList.toggle('collapsed', chatCollapsed);
  document.body.classList.toggle('chat-hidden', chatCollapsed);
  if (!chatCollapsed) {
    chatToast.classList.remove('visible');
    chatToast.classList.add('hidden');
    chatInput.focus();
  }
});

chatToast.addEventListener('click', () => {
  chatCollapsed = false;
  chatPanel.classList.remove('collapsed');
  chatToast.classList.remove('visible');
  chatToast.classList.add('hidden');
  chatInput.focus();
});

// ─── HUD ───
async function updateHUD() {
  try {
    const res = await fetch('/api/sysinfo');
    const data = await res.json();
    const memEl = document.getElementById('hud-memory-count');
    const sessEl = document.getElementById('hud-sessions');
    const uptimeEl = document.getElementById('hud-uptime');
    const memText = data.memories + ' <span class="hud-unit">' + (data.memories === 1 ? 'registro' : 'registros') + '</span>';
    if (memEl.innerHTML !== memText) {
      memEl.innerHTML = memText;
      memEl.classList.remove('update');
      void memEl.offsetWidth;
      memEl.classList.add('update');
    }
    const sessText = String(data.sessions);
    if (sessEl.textContent !== sessText) {
      sessEl.textContent = sessText;
      sessEl.classList.remove('update');
      void sessEl.offsetWidth;
      sessEl.classList.add('update');
    }
    uptimeEl.textContent = data.uptime;
  } catch { /* silent */ }
}

updateHUD();
setInterval(updateHUD, 5000);

// ─── Memory ───
const memoryList = document.getElementById('memory-list');
const memoryCount = document.getElementById('memory-count');

async function loadMemories() {
  try {
    const res = await fetch('/memories');
    const data = await res.json();
    memoryList.innerHTML = '';
    if (data.facts && data.facts.length > 0) {
      memoryCount.textContent = data.facts.length;
      data.facts.forEach((f) => {
        const div = document.createElement('div');
        div.className = 'memory-item';
        div.innerHTML = `<span class="category">[${f.category}]</span>${f.fact}`;
        memoryList.appendChild(div);
      });
    } else {
      memoryCount.textContent = '0';
      const empty = document.createElement('div');
      empty.className = 'memory-item';
      empty.textContent = 'Aún no tengo recuerdos';
      empty.style.color = 'var(--text-muted)';
      memoryList.appendChild(empty);
    }
  } catch { /* silent */ }
}

document.getElementById('memory-header-click').addEventListener('click', () => {
  memoryList.classList.toggle('collapsed');
  document.querySelector('.memory-arrow').classList.toggle('open');
});

// ─── Stats ───
const statsProvider = document.getElementById('stats-provider');
const statsModel = document.getElementById('stats-model');
const statsMessages = document.getElementById('stats-messages');
const statsRam = document.getElementById('stats-ram');

async function updateStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (statsProvider) statsProvider.textContent = data.provider || 'groq';
    if (statsModel) statsModel.textContent = data.model || '--';
    if (statsMessages) statsMessages.textContent = data.messages;
    if (statsRam) statsRam.textContent = data.memory_usage_pct != null ? data.memory_usage_pct + '%' : '--';
  } catch { /* silent */ }
}

// ─── Mind Map ───
let mindMap;

function initMindMap() {
  const container = document.getElementById('map-canvas-container');
  if (!container) return;
  mindMap = new MindMap(container);
  loadMapData();
}

async function loadMapData() {
  try {
    const res = await fetch('/memories');
    const data = await res.json();
    if (mindMap) mindMap.buildTree(data.facts || []);
  } catch { /* silent */ }
}

// ─── Music Player ───
let musicPlayer;

function initMusicPlayer() {
  const container = document.getElementById('music-player');
  if (!container) return;
  musicPlayer = new MusicPlayer(container);
}

// ─── WebSocket ───
let ws;

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'stats_update') {
        if (statsMessages && msg.data.messages != null) statsMessages.textContent = msg.data.messages;
        if (mindMap) loadMapData();
      }
      if (msg.event === 'message' && msg.data.reply && chatCollapsed) {
        showToast(msg.data.reply);
      }
    } catch { /* silent */ }
  };
  ws.onclose = () => setTimeout(connectWS, 3000);
}

// ─── History ───
async function loadHistory() {
  try {
    const res = await fetch('/api/history/default');
    const data = await res.json();
    if (!data.messages || data.messages.length === 0) return;
    chatMessages.innerHTML = '';
    for (const m of data.messages) {
      const div = document.createElement('div');
      div.className = 'message ' + (m.role === 'user' ? 'user' : 'assistant');
      div.textContent = m.content;
      chatMessages.appendChild(div);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch { /* silent */ }
}

// ─── Init ───
loadHistory();
loadMemories();
setInterval(loadMemories, 30000);
loadNews();
setInterval(loadNews, 120000);
updateStats();
setInterval(updateStats, 10000);
initMindMap();
setInterval(loadMapData, 15000);
initMusicPlayer();
connectWS();
