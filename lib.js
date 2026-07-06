const fs = require('fs');
const path = require('path');

const IMAGES_DIR = path.join(__dirname, 'images');

async function generateAndSaveImage(config, { prompt, negative, size, steps, cfg }) {
  const body = {
    model: config.model,
    prompt,
    image_size: size || config.imageSize,
    batch_size: 1,
    num_inference_steps: steps || 20,
  };
  if (negative) body.negative_prompt = negative;
  if (cfg) body.guidance_scale = cfg;

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

module.exports = { generateAndSaveImage, IMAGES_DIR };
