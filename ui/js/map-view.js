export class MindMap {
  constructor(container) {
    this.container = container;
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.container.appendChild(this.canvas);
    this.nodes = [];
    this.edges = [];
    this.hovered = null;
    this.animId = null;
    this._onResize = () => this.resize();
    window.addEventListener('resize', this._onResize);
    this.resize();
    this.animate();
  }

  resize() {
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    this.w = rect.width;
    this.h = rect.height;
  }

  buildTree(facts) {
    const cats = {};
    for (const f of facts) {
      const cat = f.category || 'general';
      if (!cats[cat]) cats[cat] = [];
      cats[cat].push(f.fact);
    }
    const entries = Object.entries(cats);
    if (entries.length === 0) {
      this.nodes = [];
      this.edges = [];
      return;
    }
    const cx = this.w / 2;
    const cy = this.h / 2;
    const radius = Math.min(this.w, this.h) * 0.3;
    this.nodes = [{ x: cx, y: cy, label: 'Thoth', r: 8, isCenter: true, phase: 0 }];
    this.edges = [];
    const colors = ['#00c8ff', '#ffaa44', '#00ff88', '#8844ff', '#ff4488', '#44ffcc'];
    entries.forEach(([cat, items], i) => {
      const angle = (i / entries.length) * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      const color = colors[i % colors.length];
      const idx = this.nodes.length;
      this.nodes.push({ x, y, label: cat, r: 6, count: items.length, items, color, isCenter: false, phase: i * 0.5, ox: x, oy: y });
      this.edges.push({ from: 0, to: idx });
      items.slice(0, 5).forEach((item, j) => {
        const subAngle = angle + (j - 2) * 0.25;
        const subRadius = 40 + Math.random() * 20;
        const sx = x + Math.cos(subAngle) * subRadius;
        const sy = y + Math.sin(subAngle) * subRadius;
        const sidx = this.nodes.length;
        this.nodes.push({ x: sx, y: sy, label: item, r: 3, color, isLeaf: true, phase: i * 0.5 + j, ox: sx, oy: sy });
        this.edges.push({ from: idx, to: sidx });
      });
    });
  }

  animate() {
    this.draw();
    this.animId = requestAnimationFrame(() => this.animate());
  }

  draw() {
    const ctx = this.ctx;
    const w = this.w;
    const h = this.h;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const t = performance.now() / 1000;

    for (const node of this.nodes) {
      if (node.ox != null) {
        const drift = Math.sin(t * 0.5 + node.phase) * 2;
        node.x = node.ox + drift;
      }
    }

    for (const edge of this.edges) {
      const from = this.nodes[edge.from];
      const to = this.nodes[edge.to];
      if (!from || !to) continue;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.strokeStyle = to.color || 'rgba(0,180,255,0.1)';
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }

    const centerPulse = Math.sin(t * 1.5) * 0.5 + 0.5;
    for (const node of this.nodes) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      if (node.isCenter) {
        ctx.fillStyle = '#00c8ff';
        ctx.shadowColor = '#00c8ff';
        ctx.shadowBlur = 10 + centerPulse * 8;
      } else if (node.isLeaf) {
        ctx.fillStyle = node.color || 'rgba(0,180,255,0.3)';
        ctx.shadowBlur = 0;
      } else {
        ctx.fillStyle = node.color || 'rgba(0,180,255,0.5)';
        ctx.shadowColor = node.color || '#00c8ff';
        ctx.shadowBlur = 5 + (1 - centerPulse) * 4;
      }
      ctx.fill();
      ctx.shadowBlur = 0;

      if (node.isCenter) {
        ctx.fillStyle = '#fff';
        ctx.font = '7px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + 14);
      } else if (!node.isLeaf && node.label) {
        ctx.fillStyle = 'rgba(200,200,216,0.6)';
        ctx.font = '6px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + 10);
      }
    }
  }

  destroy() {
    if (this.animId) cancelAnimationFrame(this.animId);
    window.removeEventListener('resize', this._onResize);
    this.container.removeChild(this.canvas);
  }
}
