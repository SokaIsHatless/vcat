import { removeBackground } from './node_modules/@imgly/background-removal/dist/index.mjs';

const UPLOAD_URL = 'http://localhost:8000/upload_cat';
const PLACEHOLDER_SRC = 'cat.png';

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

async function cleanupRejectedUpload(catImg) {
  await window.catStorage.deleteCutout();
  resetCatPhoto();
  if (catImg) {
    catImg.src = PLACEHOLDER_SRC;
  }
  window.dispatchEvent(new Event('cat-layout-changed'));
}

function displayCutout(catImg, savedUrl) {
  const displayUrl = `${savedUrl}${savedUrl.includes('?') ? '&' : '?'}v=${Date.now()}`;
  markCatReady(displayUrl);
  catImg.src = displayUrl;
}

export async function processCatPhoto(file, { onStatus, catImg }) {
  if (!file || !file.type.startsWith('image/')) {
    throw new Error('Please choose an image file (JPEG, PNG, etc.).');
  }

  onStatus('Analyzing your cat...');
  const formData = new FormData();
  formData.append('file', file, file.name);

  let response;
  try {
    response = await fetch(UPLOAD_URL, {
      method: 'POST',
      body: formData,
    });
  } catch (error) {
    await cleanupRejectedUpload(catImg);
    throw new Error("Can't reach my brain right now, human. Is the backend running on :8000?");
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok || data?.is_cat === false) {
    await cleanupRejectedUpload(catImg);
    throw new Error(
      (data && data.error) || `Upload failed (HTTP ${response.status})`,
    );
  }

  onStatus('Removing background... (first run may download a model)');
  const previewUrl = URL.createObjectURL(file);

  let cutoutBlob;
  try {
    cutoutBlob = await removeBackground(previewUrl);
  } catch (error) {
    await cleanupRejectedUpload(catImg);
    throw error;
  } finally {
    URL.revokeObjectURL(previewUrl);
  }

  try {
    const savedUrl = await window.catStorage.saveCutout(await cutoutBlob.arrayBuffer());
    displayCutout(catImg, savedUrl);
    window.dispatchEvent(new Event('cat-layout-changed'));
  } catch (error) {
    await cleanupRejectedUpload(catImg);
    throw error;
  }

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
