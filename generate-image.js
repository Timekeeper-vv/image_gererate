const fs = require('fs');
const path = require('path');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf-8'));

const prompt = process.argv.slice(2).join(' ');
if (!prompt) {
  console.error('用法: node generate-image.js "你的提示词"');
  process.exit(1);
}

async function main() {
  const res = await fetch('https://api.siliconflow.cn/v1/images/generations', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: config.model,
      prompt,
      image_size: config.imageSize,
      batch_size: 1,
      num_inference_steps: 20,
    }),
  });

  if (!res.ok) {
    console.error(`请求失败: ${res.status} ${await res.text()}`);
    process.exit(1);
  }

  const data = await res.json();
  const imageUrl = data.images?.[0]?.url;
  if (!imageUrl) {
    console.error('未获取到图片链接:', JSON.stringify(data));
    process.exit(1);
  }

  const imgRes = await fetch(imageUrl);
  const buffer = Buffer.from(await imgRes.arrayBuffer());

  const outDir = path.join(__dirname, 'images');
  fs.mkdirSync(outDir, { recursive: true });
  const filename = `image_${Date.now()}.png`;
  const outPath = path.join(outDir, filename);
  fs.writeFileSync(outPath, buffer);

  console.log(`已保存: ${outPath}`);
}

main().catch((err) => {
  console.error('出错:', err);
  process.exit(1);
});
