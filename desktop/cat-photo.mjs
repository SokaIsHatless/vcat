import { removeBackground } from './node_modules/@imgly/background-removal/dist/index.mjs';

const UPLOAD_URL = 'http://localhost:8000/upload_cat';

let catPhotoReady = false;
let catObjectUrl = null;

export function isCatPhotoReady() {
  return catPhotoReady;
}

export function markCatReady(cutoutUrl) {
  if (catObjectUrl && catObjectUrl.startsWith('blob:')) {
    URL.revokeObjectURL(catObjectUrl);
  }
  catObjectUrl = cutoutUrl;
  catPhotoReady = true;
}

export async function processCatPhoto(file, { onStatus, catImg }) {
  if (!file || !file.type.startsWith('image/')) {
    throw new Error('Please choose an image file (JPEG, PNG, etc.).');
  }

  onStatus('Removing background... (first run may download a model)');
  const previewUrl = URL.createObjectURL(file);

  let cutoutBlob;
  try {
    cutoutBlob = await removeBackground(previewUrl);
  } finally {
    URL.revokeObjectURL(previewUrl);
  }

  const savedUrl = await window.catStorage.saveCutout(await cutoutBlob.arrayBuffer());
  markCatReady(savedUrl);
  catImg.src = savedUrl;
  window.dispatchEvent(new Event('cat-layout-changed'));

  onStatus('Analyzing your cat...');
  const formData = new FormData();
  formData.append('file', file, file.name);

  const response = await fetch(UPLOAD_URL, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed (HTTP ${response.status})`);
  }

  const data = await response.json();
  console.log('Cat personality:', data.personality);

  onStatus('');
  window.dispatchEvent(new Event('cat-photo-ready'));
}

export function resetCatPhoto() {
  if (catObjectUrl && catObjectUrl.startsWith('blob:')) {
    URL.revokeObjectURL(catObjectUrl);
  }
  catObjectUrl = null;
  catPhotoReady = false;
}

window.catPhoto = {
  isReady: isCatPhotoReady,
  processFile: processCatPhoto,
  markReady: markCatReady,
  reset: resetCatPhoto,
};

window.dispatchEvent(new Event('cat-photo-module-ready'));
