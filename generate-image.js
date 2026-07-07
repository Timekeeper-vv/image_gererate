const fs = require('fs');
const path = require('path');
const { generateAndSaveImage } = require('./lib');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf-8'));

function parseArgs(argv) {
  const flags = { negative: null, size: config.imageSize, steps: 20, cfg: null, seed: null };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--negative') flags.negative = argv[++i];
    else if (arg === '--size') flags.size = argv[++i];
    else if (arg === '--steps') flags.steps = Number(argv[++i]);
    else if (arg === '--cfg') flags.cfg = Number(argv[++i]);
    else if (arg === '--seed') flags.seed = Number(argv[++i]);
    else positional.push(arg);
  }
  flags.prompt = positional.join(' ');
  return flags;
}

const { prompt, negative, size, steps, cfg, seed } = parseArgs(process.argv.slice(2));
if (!prompt) {
  console.error(
    '用法: node generate-image.js "正向提示词" [--negative "负向提示词"] [--size 1024x1024] [--steps 20] [--cfg 7.5] [--seed 12345]'
  );
  process.exit(1);
}

generateAndSaveImage(config, { prompt, negative, size, steps, cfg, seed })
  .then(({ outPath }) => console.log(`已保存: ${outPath}`))
  .catch((err) => {
    console.error('出错:', err.message);
    process.exit(1);
  });
