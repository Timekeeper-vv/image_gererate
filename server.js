const http = require('http');
const fs = require('fs');
const path = require('path');
const { generateAndSaveImage, IMAGES_DIR } = require('./lib');
const { SYSTEM_PROMPT, buildUserMessage, splitBriefAndPrompt } = require('./brief-template');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf-8'));
const PUBLIC_DIR = path.join(__dirname, 'public');
const PORT = 3000;

async function generateBrief(requirement, materials) {
  const res = await fetch('https://api.siliconflow.cn/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: config.chatModel,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: buildUserMessage(requirement, materials) },
      ],
      max_tokens: 2000,
      temperature: 0.7,
    }),
  });

  if (!res.ok) {
    throw new Error(`Brief 生成请求失败: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error(`大模型未返回内容: ${JSON.stringify(data)}`);
  }
  return splitBriefAndPrompt(content);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let chunks = '';
    req.on('data', (c) => (chunks += c));
    req.on('end', () => resolve(chunks));
    req.on('error', reject);
  });
}

function serveStatic(req, res, filePath, contentType) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && req.url === '/') {
    serveStatic(req, res, path.join(PUBLIC_DIR, 'index.html'), 'text/html; charset=utf-8');
    return;
  }

  if (req.method === 'GET' && req.url.startsWith('/images/')) {
    const filename = decodeURIComponent(req.url.replace('/images/', ''));
    serveStatic(req, res, path.join(IMAGES_DIR, filename), 'image/png');
    return;
  }

  if (req.method === 'POST' && req.url === '/generate') {
    try {
      const body = JSON.parse(await readBody(req));
      const requirement = (body.requirement || '').trim();
      const materials = body.materials || '';
      if (!requirement) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: '请输入原始需求' }));
        return;
      }

      const { brief, promptData } = await generateBrief(requirement, materials);
      const sizeMatch = /^(\d+)x(\d+)$/.exec(promptData.image_size || '');
      const validSize =
        sizeMatch && Number(sizeMatch[1]) >= 512 && Number(sizeMatch[2]) >= 512
          ? promptData.image_size
          : config.imageSize;
      const { filename } = await generateAndSaveImage(config, {
        prompt: promptData.positive_prompt,
        negative: promptData.negative_prompt,
        size: validSize,
        steps: promptData.steps,
        cfg: promptData.cfg,
      });

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ brief, imageUrl: `/images/${filename}` }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log(`服务已启动: http://localhost:${PORT}`);
});
