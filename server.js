const http = require('http');
const fs = require('fs');
const path = require('path');
const { generateAndSaveImage, generateTripoModel, IMAGES_DIR } = require('./lib');
const { SYSTEM_PROMPT, buildUserMessage, splitBriefAndPrompt } = require('./brief-template');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf-8'));
const PUBLIC_DIR = path.join(__dirname, 'public');
const LEADS_DIR = path.join(__dirname, 'leads');
const PORT = Number(process.env.PORT || 3000);
const PRICING_API_URL = process.env.PRICING_API_URL || 'http://127.0.0.1:8001';
const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
};

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
    req.on('data', (c) => {
      chunks += c;
      if (chunks.length > 2 * 1024 * 1024) {
        reject(new Error('请求体过大'));
        req.destroy();
      }
    });
    req.on('end', () => resolve(chunks));
    req.on('error', reject);
  });
}

function sendJson(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function serveStatic(req, res, filePath, contentType) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

function saveLead(lead) {
  fs.mkdirSync(LEADS_DIR, { recursive: true });
  const record = {
    ...lead,
    createdAt: new Date().toISOString(),
  };
  fs.appendFileSync(path.join(LEADS_DIR, 'leads.jsonl'), JSON.stringify(record) + '\n', 'utf-8');
  return record;
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && req.url.split('?')[0] === '/') {
      serveStatic(req, res, path.join(PUBLIC_DIR, 'index.html'), 'text/html; charset=utf-8');
      return;
    }

    if (req.method === 'GET' && req.url === '/pricing/health') {
      const pricingRes = await fetch(`${PRICING_API_URL}/health`);
      const text = await pricingRes.text();
      res.writeHead(pricingRes.status, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(text);
      return;
    }
    if (req.method === 'GET' && req.url !== '/' && !req.url.startsWith('/images/')) {
      const pathname = req.url.split('?')[0];
      const filename = path.basename(decodeURIComponent(pathname));
      const filePath = path.join(PUBLIC_DIR, filename);
      const contentType = CONTENT_TYPES[path.extname(filename).toLowerCase()] || 'application/octet-stream';
      serveStatic(req, res, filePath, contentType);
      return;
    }

    if (req.method === 'GET' && req.url.startsWith('/images/')) {
      const pathname = req.url.split('?')[0];
      const filename = path.basename(decodeURIComponent(pathname.replace('/images/', '')));
      serveStatic(req, res, path.join(IMAGES_DIR, filename), 'image/png');
      return;
    }

    if (req.method === 'POST' && req.url === '/pricing/quote') {
      const raw = await readBody(req);
      const pricingRes = await fetch(`${PRICING_API_URL}/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: raw,
      });
      const text = await pricingRes.text();
      res.writeHead(pricingRes.status, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(text);
      return;
    }


    if (req.method === 'POST' && req.url === '/lead') {
      const body = JSON.parse(await readBody(req) || '{}');
      const name = String(body.name || '').trim();
      const phone = String(body.phone || '').trim();
      if (!name || !phone) {
        sendJson(res, 400, { error: '请填写姓名和联系方式' });
        return;
      }
      const lead = saveLead({
        name,
        phone,
        company: String(body.company || '').trim(),
        note: String(body.note || '').trim(),
        requirement: String(body.requirement || '').trim(),
        brief: String(body.brief || '').slice(0, 12000),
        images: Array.isArray(body.images) ? body.images.slice(0, 6) : [],
        tripo: body.tripo || null,
      });
      sendJson(res, 200, { ok: true, leadId: lead.createdAt });
      return;
    }

    if (req.method === 'POST' && req.url === '/generate') {
      const body = JSON.parse(await readBody(req) || '{}');
      const requirement = String(body.requirement || '').trim();
      const materials = body.materials || '';
      if (!requirement) {
        sendJson(res, 400, { error: '请输入产品需求' });
        return;
      }

      const { brief, promptData } = await generateBrief(requirement, materials);
      const sizeMatch = /^(\d+)x(\d+)$/.exec(promptData.image_size || '');
      const validSize =
        sizeMatch && Number(sizeMatch[1]) >= 512 && Number(sizeMatch[2]) >= 512
          ? promptData.image_size
          : config.imageSize;

      const sharedSeed = Math.floor(Math.random() * 2 ** 31);
      const images = [];
      for (const view of promptData.views) {
        const { filename } = await generateAndSaveImage(config, {
          prompt: `${promptData.base_prompt}, ${view.angle_prompt}`,
          negative: promptData.negative_prompt,
          size: validSize,
          steps: promptData.steps,
          cfg: promptData.cfg,
          seed: sharedSeed,
        });
        images.push({ angle: view.angle, url: `/images/${filename}` });
      }

      let tripo = null;
      let tripoError = null;
      if (process.env.TRIPO_API_KEY || config.tripoApiKey) {
        try {
          tripo = await generateTripoModel(config, promptData);
        } catch (err) {
          tripoError = err.message;
        }
      }

      sendJson(res, 200, { brief, images, tripo, tripoError });
      return;
    }

    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not found');
  } catch (err) {
    sendJson(res, 500, { error: err.message });
  }
});

server.listen(PORT, () => {
  console.log(`服务已启动: http://localhost:${PORT}`);
});
