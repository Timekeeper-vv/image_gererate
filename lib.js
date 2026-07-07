const fs = require('fs');
const path = require('path');

const IMAGES_DIR = path.join(__dirname, 'images');
const TRIPO_BASE_URL = 'https://openapi.tripo3d.com/v3';

async function generateAndSaveImage(config, { prompt, negative, size, steps, cfg, seed }) {
  const body = {
    model: config.model,
    prompt,
    image_size: size || config.imageSize,
    batch_size: 1,
    num_inference_steps: steps || 20,
  };
  if (negative) body.negative_prompt = negative;
  if (cfg) body.guidance_scale = cfg;
  if (seed !== undefined && seed !== null) body.seed = seed;

  const res = await fetch('https://api.siliconflow.cn/v1/images/generations', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`图片生成请求失败: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  const imageUrl = data.images?.[0]?.url;
  if (!imageUrl) {
    throw new Error(`未获取到图片链接: ${JSON.stringify(data)}`);
  }

  const imgRes = await fetch(imageUrl);
  const buffer = Buffer.from(await imgRes.arrayBuffer());

  fs.mkdirSync(IMAGES_DIR, { recursive: true });
  const filename = `image_${Date.now()}_${Math.floor(Math.random() * 1e6)}.png`;
  const outPath = path.join(IMAGES_DIR, filename);
  fs.writeFileSync(outPath, buffer);

  return { filename, outPath };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getTripoApiKey(config) {
  return process.env.TRIPO_API_KEY || config.tripoApiKey;
}

async function tripoRequest(config, apiPath, { method = 'GET', body } = {}) {
  const apiKey = getTripoApiKey(config);
  if (!apiKey) {
    throw new Error('未配置 Tripo API Key：请在 config.json 的 tripoApiKey 中填写，或设置环境变量 TRIPO_API_KEY');
  }

  const res = await fetch(`${config.tripoBaseUrl || TRIPO_BASE_URL}${apiPath}`, {
    method,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const message = data?.message || data?.error || text;
    throw new Error(`Tripo 请求失败: ${res.status} ${message}`);
  }

  if (data && typeof data.code === 'number' && data.code !== 0) {
    throw new Error(`Tripo 返回错误: ${data.code} ${data.message || JSON.stringify(data)}`);
  }

  return data?.data || data;
}

function compactPrompt(text, maxLength = 1000) {
  return String(text || '')
    .replace(/\s+/g, ' ')
    .replace(/\b(product photography|e-commerce product shot|white background|neutral background|studio lighting)\b/gi, '')
    .replace(/\s*,\s*,+/g, ',')
    .trim()
    .slice(0, maxLength);
}

function buildTripoPrompt(promptData) {
  const basePrompt = compactPrompt(promptData.base_prompt, 850);
  return compactPrompt(
    [
      basePrompt,
      'single complete textured 3D product model',
      'accurate material, clean geometry, production-ready shape',
      'no background, no text labels, no people, no scene',
    ].join(', '),
    1000
  );
}

function collectUrls(value, parentKey = '', out = []) {
  if (!value) return out;
  if (typeof value === 'string') {
    if (/^https?:\/\//i.test(value)) out.push({ url: value, key: parentKey });
    return out;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => collectUrls(item, `${parentKey}[${index}]`, out));
    return out;
  }
  if (typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      collectUrls(item, parentKey ? `${parentKey}.${key}` : key, out);
    }
  }
  return out;
}

function pickUrl(urls, patterns) {
  for (const pattern of patterns) {
    const found = urls.find((item) => pattern.test(`${item.key} ${item.url}`));
    if (found) return found.url;
  }
  return null;
}

function normalizeTripoTask(task) {
  const output = task?.output || task?.result || task || {};
  const urls = collectUrls(output);
  const previewUrl = pickUrl(urls, [
    /(render|preview|thumbnail|cover|image|picture).*\.(png|jpe?g|webp)(\?|$)/i,
    /\.(png|jpe?g|webp)(\?|$)/i,
  ]);
  const modelUrl = pickUrl(urls, [
    /(pbr|model|mesh|asset).*\.(glb|gltf|fbx|obj|stl|zip)(\?|$)/i,
    /\.(glb|gltf|fbx|obj|stl|zip)(\?|$)/i,
  ]);

  return {
    taskId: task?.task_id || task?.taskId || task?.id,
    status: task?.status,
    progress: task?.progress,
    previewUrl,
    modelUrl,
    urls: urls.map((item) => item.url),
  };
}

async function createTripoTextToModelTask(config, prompt) {
  const body = {
    prompt,
    model: config.tripoModel || config.tripoModelVersion || 'v3.1-20260211',
  };
  if (config.tripoTaskOptions && typeof config.tripoTaskOptions === 'object') {
    Object.assign(body, config.tripoTaskOptions);
  }

  const data = await tripoRequest(config, '/generation/text-to-model', { method: 'POST', body });
  const taskId = data?.task_id || data?.taskId || data?.id;
  if (!taskId) {
    throw new Error(`Tripo 未返回 task_id: ${JSON.stringify(data)}`);
  }
  return taskId;
}

async function getTripoTask(config, taskId) {
  return tripoRequest(config, `/tasks/${encodeURIComponent(taskId)}`);
}

async function waitForTripoTask(config, taskId) {
  const maxWaitMs = Number(config.tripoMaxWaitMs || 10 * 60 * 1000);
  const intervalMs = Number(config.tripoPollIntervalMs || 5000);
  const startedAt = Date.now();
  let lastTask = null;

  while (Date.now() - startedAt < maxWaitMs) {
    lastTask = await getTripoTask(config, taskId);
    const status = String(lastTask?.status || '').toLowerCase();

    if (['success', 'succeeded', 'finished', 'completed', 'done'].includes(status)) {
      return normalizeTripoTask(lastTask);
    }
    if (['failed', 'failure', 'error', 'cancelled', 'canceled'].includes(status)) {
      throw new Error(`Tripo 生成失败: ${lastTask?.message || lastTask?.error || JSON.stringify(lastTask)}`);
    }

    await sleep(intervalMs);
  }

  throw new Error(`Tripo 生成超时，task_id=${taskId}，最后状态=${lastTask?.status || 'unknown'}`);
}

async function generateTripoModel(config, promptData) {
  const prompt = promptData.tripo_prompt ? compactPrompt(promptData.tripo_prompt) : buildTripoPrompt(promptData);
  const taskId = await createTripoTextToModelTask(config, prompt);
  const result = await waitForTripoTask(config, taskId);
  return { ...result, prompt };
}

module.exports = { generateAndSaveImage, generateTripoModel, IMAGES_DIR };
