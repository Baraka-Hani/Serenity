/* All image inference runs here on the device. Only model files are fetched. */
import './studio-grouping.js';
let ready;
let classifier;
let RawImage;
const { themes, classify } = globalThis.SerenityStudioGrouping;
async function initialize() {
  if (!ready) ready = (async () => {
    const library = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js');
    library.env.allowLocalModels = false;
    library.env.backends.onnx.wasm.numThreads = 1;
    RawImage = library.RawImage;
    classifier = await library.pipeline('zero-shot-image-classification', 'Xenova/clip-vit-base-patch32', {
      dtype: 'q8', device: 'wasm',
      progress_callback: progress => self.postMessage({ type: 'model-progress', progress: { status: progress.status, file: progress.file, progress: progress.progress } })
    });
  })();
  return ready;
}
self.onmessage = async ({ data }) => {
  try {
    await initialize();
    if (data.type === 'init') return self.postMessage({ id: data.id, type: 'ready' });
    const totals = new Map(themes.map(theme => [theme.prompt, 0]));
    for (const frame of data.frames) {
      const image = new RawImage(new Uint8ClampedArray(frame.buffer), frame.width, frame.height, 4);
      const scores = await classifier(image, themes.map(theme => theme.prompt));
      for (const score of scores) totals.set(score.label, totals.get(score.label) + score.score / data.frames.length);
    }
    const scores = [...totals].map(([label, score]) => ({ label, score }));
    self.postMessage({ id: data.id, type: 'result', theme: classify(scores) });
  } catch (error) {
    ready = null;
    self.postMessage({ id: data.id, type: 'error', error: error.message || 'The vision model could not run on this device.' });
  }
};
