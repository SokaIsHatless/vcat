import { removeBackground } from './node_modules/@imgly/background-removal/dist/index.mjs';

const UPLOAD_URL = 'http://localhost:8000/upload_cat';

let catPhotoReady = false;
let catObjectUrl = null;

export function isCatPhotoReady() {
  return catPhotoReady;
}

export async function processCatPhoto(file, { onStatus, catImg }) {
  if (!file || !file.type.startsWith('image/')) {
    throw new Error('Please choose an image file (JPEG, PNG, etc.).');
  }

  onStatus('Removing background... (first run may download a model)');
  const previewUrl = URL.createObjectURL(file);

  try {
    const cutoutBlob = await removeBackground(previewUrl);
    if (catObjectUrl) {
      URL.revokeObjectURL(catObjectUrl);
    }
    catObjectUrl = URL.createObjectURL(cutoutBlob);
    catImg.src = catObjectUrl;
    window.dispatchEvent(new Event('cat-layout-changed'));
  } finally {
    URL.revokeObjectURL(previewUrl);
  }

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

  catPhotoReady = true;
  onStatus('');
  window.dispatchEvent(new Event('cat-photo-ready'));
}

window.catPhoto = {
  isReady: isCatPhotoReady,
  processFile: processCatPhoto,
};

window.dispatchEvent(new Event('cat-photo-module-ready'));
