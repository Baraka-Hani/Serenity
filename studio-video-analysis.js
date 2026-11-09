/* Small browser-media boundary: bounded decoding, frame sampling, and worker inference. */
(() => {
  const MAX_SIZE = 50 * 1024 * 1024;
  function isVideo(file) { return /\.(mp4|mov|m4v|webm)$/i.test(file.name) && (!file.type || file.type.startsWith('video/')); }
  async function fingerprint(file) {
    const bytes = await file.arrayBuffer();
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map(x => x.toString(16).padStart(2, '0')).join('');
  }
  function waitFor(video, event, action, signal) {
    return new Promise((resolve, reject) => {
      const finish = error => {
        clearTimeout(timer); video.removeEventListener(event, loaded); video.removeEventListener('error', failed); signal?.removeEventListener('abort', aborted);
        error ? reject(error) : resolve();
      };
      const loaded = () => finish();
      const failed = () => finish(new Error('This browser could not decode the video. Try exporting it as MP4 (H.264).'));
      const aborted = () => finish(new DOMException('Cancelled', 'AbortError'));
      const timer = setTimeout(() => finish(new Error('This video took too long to read.')), 20000);
      video.addEventListener(event, loaded, { once: true }); video.addEventListener('error', failed, { once: true }); signal?.addEventListener('abort', aborted, { once: true });
      if (signal?.aborted) return aborted();
      action();
    });
  }
  async function sample(file, signal) {
    const url = URL.createObjectURL(file), video = document.createElement('video');
    video.muted = true; video.playsInline = true; video.preload = 'auto';
    try {
      await waitFor(video, 'loadeddata', () => { video.src = url; }, signal);
      if (!Number.isFinite(video.duration) || !video.duration || !video.videoWidth) throw new Error('The video has no readable frames.');
      const scale = Math.min(1, 320 / Math.max(video.videoWidth, video.videoHeight));
      const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.round(video.videoWidth * scale)); canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
      const context = canvas.getContext('2d', { willReadFrequently: true });
      const frames = []; let thumbnail;
      for (const ratio of [.12, .5, .85]) {
        const time = Math.max(0, Math.min(video.duration - .001, video.duration * ratio));
        if (Math.abs(video.currentTime - time) > .0001) await waitFor(video, 'seeked', () => { video.currentTime = time; }, signal);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        if (!thumbnail) thumbnail = canvas.toDataURL('image/jpeg', .65);
        frames.push({ buffer: context.getImageData(0, 0, canvas.width, canvas.height).data.buffer, width: canvas.width, height: canvas.height });
      }
      return { frames, thumbnail, duration: video.duration };
    } finally { video.pause(); video.removeAttribute('src'); video.load(); URL.revokeObjectURL(url); }
  }
  class Vision {
    constructor(onProgress) {
      this.worker = new Worker('studio-vision-worker.js', { type: 'module' });
      this.pending = new Map(); this.serial = 0;
      this.worker.onmessage = ({ data }) => {
        if (data.type === 'model-progress') return onProgress(data.progress);
        const task = this.pending.get(data.id); if (!task) return;
        clearTimeout(task.timer); this.pending.delete(data.id);
        data.type === 'error' ? task.reject(new Error(data.error)) : task.resolve(data);
      };
      this.worker.onerror = () => this.fail(new Error('The local vision worker could not start. Check your connection or use manual grouping.'));
    }
    request(type, frames = []) {
      return new Promise((resolve, reject) => {
        const id = ++this.serial;
        const timer = setTimeout(() => { this.pending.delete(id); reject(new Error('Vision analysis timed out. You can retry or group these clips manually.')); }, type === 'init' ? 300000 : 120000);
        this.pending.set(id, { resolve, reject, timer });
        this.worker.postMessage({ id, type, frames }, frames.map(frame => frame.buffer));
      });
    }
    fail(error) { for (const task of this.pending.values()) { clearTimeout(task.timer); task.reject(error); } this.pending.clear(); }
    stop() { this.worker.terminate(); this.fail(new DOMException('Cancelled', 'AbortError')); }
  }
  window.SerenityVideoAnalysis = { MAX_SIZE, isVideo, fingerprint, sample, Vision };
})();
