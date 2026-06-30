export class MusicPlayer {
  constructor(container) {
    this.container = container;
    this.audioCtx = null;
    this.playing = false;
    this.volume = 0.15;
    this.nodes = [];
    this._disposed = false;
    this.buildUI();
  }

  buildUI() {
    this.container.innerHTML = `
      <div class="player-header">
        <span class="player-label">&#9835; Ambiente</span>
        <span class="player-status" id="player-status">detenido</span>
      </div>
      <div class="player-controls">
        <button class="player-btn" id="player-play" title="Play/Pause">&#9654;</button>
        <input type="range" class="player-volume" id="player-volume" min="0" max="1" step="0.05" value="0.15">
        <span class="player-vol-label" id="player-vol-label">15%</span>
      </div>
    `;

    this.playBtn = this.container.querySelector('#player-play');
    this.volSlider = this.container.querySelector('#player-volume');
    this.volLabel = this.container.querySelector('#player-vol-label');
    this.statusEl = this.container.querySelector('#player-status');

    this._onClick = () => this.toggle();
    this._onVolume = (e) => {
      this.volume = parseFloat(e.target.value);
      this.volLabel.textContent = Math.round(this.volume * 100) + '%';
      if (this.masterGain) this.masterGain.gain.value = this.volume;
    };
    this.playBtn.addEventListener('click', this._onClick);
    this.volSlider.addEventListener('input', this._onVolume);
  }

  _stopAllNodes() {
    for (const n of this.nodes) {
      try {
        if (n.osc && n.osc.stop) n.osc.stop();
        if (n.noise && n.noise.stop) n.noise.stop();
        if (n.gain) n.gain.disconnect();
        if (n.filter) n.filter.disconnect();
      } catch { }
    }
    this.nodes = [];
  }

  initAudio() {
    if (this.audioCtx && this.audioCtx.state !== 'closed') return;
    this._stopAllNodes();
    if (this.audioCtx) {
      try { this.audioCtx.close(); } catch { }
    }
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this.masterGain = this.audioCtx.createGain();
    this.masterGain.gain.value = this.volume;
    this.masterGain.connect(this.audioCtx.destination);
    this.createAmbient();
  }

  createAmbient() {
    const ctx = this.audioCtx;
    const master = this.masterGain;

    const makeOsc = (freq, type, gainVal, detune = 0) => {
      const osc = ctx.createOscillator();
      osc.type = type;
      osc.frequency.value = freq;
      osc.detune.value = detune;
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(gainVal, ctx.currentTime + 2);
      osc.connect(gain);
      gain.connect(master);
      osc.start();
      return { osc, gain, baseFreq: freq };
    };

    this.nodes.push(makeOsc(55, 'sine', 0.04));
    this.nodes.push(makeOsc(65.41, 'sine', 0.03));
    this.nodes.push(makeOsc(82.41, 'sine', 0.025));
    this.nodes.push(makeOsc(110, 'sine', 0.015));
    this.nodes.push(makeOsc(130.81, 'sine', 0.012));
    this.nodes.push(makeOsc(55, 'triangle', 0.02, 5));
    this.nodes.push(makeOsc(220, 'sine', 0.008));

    const noiseLen = ctx.sampleRate * 4;
    const buf = ctx.createBuffer(1, noiseLen, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < noiseLen; i++) {
      data[i] = (Math.random() * 2 - 1) * 0.3;
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buf;
    noise.loop = true;
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0, ctx.currentTime);
    noiseGain.gain.linearRampToValueAtTime(0.006, ctx.currentTime + 2);
    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = 'lowpass';
    noiseFilter.frequency.value = 400;
    noise.connect(noiseGain);
    noiseGain.connect(noiseFilter);
    noiseFilter.connect(master);
    noise.start();
    this.nodes.push({ noise, gain: noiseGain, filter: noiseFilter });
  }

  toggle() {
    if (this.playing) {
      this.stop();
    } else {
      this.play();
    }
  }

  play() {
    if (this._disposed) return;
    this.initAudio();
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    this.playing = true;
    this.playBtn.innerHTML = '&#9646;&#9646;';
    this.statusEl.textContent = 'sonando';
    this.statusEl.style.color = '#00ff88';
  }

  stop() {
    this.playing = false;
    this.playBtn.innerHTML = '&#9654;';
    this.statusEl.textContent = 'detenido';
    this.statusEl.style.color = '#585878';
    if (this.audioCtx && this.audioCtx.state !== 'closed') {
      this.audioCtx.suspend();
    }
  }

  destroy() {
    this._disposed = true;
    this.stop();
    this._stopAllNodes();
    if (this.audioCtx) {
      try { this.audioCtx.close(); } catch { }
      this.audioCtx = null;
    }
    this.playBtn.removeEventListener('click', this._onClick);
    this.volSlider.removeEventListener('input', this._onVolume);
  }
}
