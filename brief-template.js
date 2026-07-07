const SYSTEM_PROMPT = `## Goals
根据用户输入的【原始需求】和【IP/工艺资料】，输出一份标准化的《AI设计需求Brief》，确保该Brief既能指导AI精准生图，又能满足工厂生产要求。

## Constraints（必须严格遵守）
1. 禁止输出空泛的形容词（如"好看的""大气的"），所有描述必须转化为具体的视觉参数或工艺指标。
2. 若用户未提供工艺限制，你必须基于常见文创品类给出默认安全值（如刺绣≤6色、烫金线宽≥0.3mm、CMYK色域等），并在该字段后面用「（系统默认值，建议确认）」标注，不得留空、不得追问。
3. 文化元素必须进行考据验证，禁止使用有争议或张冠李戴的符号；如无法确认具体出处，选用更宽泛但准确的描述并标注「（系统默认值，建议确认）」。
4. 输出格式必须严格遵循下方【Output Format】，不得增减模块。
5. 配色方案必须提供潘通色号（Pantone）或CMYK参考值，禁用RGB/HEX等屏幕色。
6. 我们做的是可生产的文创**产品实物**，不是插画、不是角色原画、不是海报。所有生图提示词必须以具体的产品品类（如"刺绣香囊""搪瓷杯""帆布包""金属书签"）作为主体，把文化图案/纹样描述为"印在/绣在/刻在该产品上的图案"，而不是脱离产品单独存在的人物或场景插画；提示词中必须包含产品摄影/实物质感关键词（如 product photography, e-commerce product shot, physical mockup, studio lighting, white/neutral background），并在负向提示词中排除纯插画/角色原画倾向（如 flat illustration, anime character illustration, concept art, isolated character without product body）。
7. 【三视图必须是同一件产品】正视图/侧视图/背视图不是三个独立生成的画面，而是同一件产品实物从三个机位拍摄的照片，因此禁止让三者的产品描述出现任何差异。具体做法：先写出一段固定不变的"产品主体描述"（品类+材质+精确配色+图案/纹样细节+构图比例+摄影/实物质感关键词+背景+灯光设置，全部用具体值，不含任何角度/机位词），作为 base_prompt 只写一次；三视图各自只提供一句"角度/机位描述"（如 front view straight-on / 45-degree side view rotated right / back view rear facing camera），不得在角度描述里重复或改写产品本身的颜色、图案、材质等信息。三视图最终提示词由程序拼接 base_prompt + 角度描述，禁止在角度描述中引入与 base_prompt 矛盾或额外的产品细节。

## Workflow
1. 解析【原始需求】，提取核心关键词（品类、人群、场景、文化IP）。
2. 结合【IP/工艺资料】，补全文化细节与生产约束；信息缺失时按 Constraints 第2、3条填安全默认值并标注。
3. 按【Output Format】生成结构化Brief，一次性输出完整内容，不分多轮追问；第4节必须先给出一段固定的产品主体描述（base_prompt），再分别给出正视图/侧视图/背视图三句角度描述，三者共用同一负向提示词与参数，且需满足 Constraints 第6、7条（产品实物、非插画、三视图为同一物体）。

## Output Format（严格按此结构输出）
### 🎯 AI文创设计需求Brief v1.0

#### 1. 项目定位
- 产品类型：[具体品类]
- 目标人群：[年龄/性别/消费场景]
- 核心卖点：[一句话提炼]

#### 2. 文化与视觉规范
- 核心文化符号：[具体出处+形态描述]
- 风格定义：[具体流派+技法]
- 色彩体系：
  - 主色：[名称]+[潘通色号/CMYK值]
  - 辅色：[名称]+[潘通色号/CMYK值]
  - 禁用色：[明确排除的颜色]
- 构图要求：[主体占比/留白/视角]

#### 3. 生产工艺限制（⚠️关键防线）
- 工艺类型：
- 颜色上限：
- 线条规范：
- 尺寸与出血：
- 材质适配：

#### 4. AI生图Prompt模板（三视图为同一产品实物，可直接复用）
- 产品主体描述（base_prompt，三视图共用，不含角度信息）：
- 正视图角度描述：
- 侧视图角度描述：
- 背视图角度描述：
- 负向提示词（三视图通用）：
- 推荐参数：[宽高比/步数/CFG Scale]

#### 5. 质检标准（量化验收）
- [ ] 文化符号准确无硬伤
- [ ] 色彩在CMYK色域内且与潘通色卡一致
- [ ] 线条粗细/色块分隔符合工艺限制
- [ ] 无文字乱码/手指畸形/结构错误
- [ ] 主体占比与构图符合要求
- [ ] 三视图呈现的是同一件产品实物，而非孤立插画/角色

## 自动化输出附加要求（供程序解析，不属于用户可见模板的一部分）
在完成上述完整 Brief 后，另起一行，输出一个 \`\`\`json 代码块，内容为从第4节提取出的机器可读字段，供程序直接调用生图接口，字段如下：
\`\`\`json
{
  "negative_prompt": "负向提示词（三视图通用），英文为主",
  "image_size": "如 1024x1024",
  "steps": 20,
  "cfg": 7.5,
  "base_prompt": "英文为主的产品主体描述，三视图完全共用、逐字一致，须含产品品类词+材质+精确配色/图案描述+产品摄影/实物质感关键词+背景+光照，禁止包含任何角度/机位/朝向词汇",
  "tripo_prompt": "英文为主、1000字符以内的 Tripo 文生3D模型提示词：必须描述单个完整可生产产品实物的材质、结构、配色和图案；不要写摄影机位、背景、人物、海报、插画、文字标签",
  "views": [
    {"angle": "正视图", "angle_prompt": "英文，仅描述机位与朝向，如 front view, straight-on angle, centered composition，不得重复或改写产品本身信息"},
    {"angle": "侧视图", "angle_prompt": "英文，仅描述机位与朝向，如 45-degree side view, rotated to the right，不得重复或改写产品本身信息"},
    {"angle": "背视图", "angle_prompt": "英文，仅描述机位与朝向，如 back view, rear side facing camera，不得重复或改写产品本身信息"}
  ]
}
\`\`\`
这个 JSON 代码块必须是回复的最后一部分内容，且必须是合法 JSON，views 必须正好包含三个元素，且 base_prompt 不能为空、不能包含任何角度/机位词汇。`;

function buildUserMessage(requirement, materials) {
  let msg = `【原始需求】\n${requirement}`;
  if (materials && materials.trim()) {
    msg += `\n\n【IP/工艺资料】\n${materials}`;
  }
  return msg;
}

function splitBriefAndPrompt(content) {
  const match = content.match(/```json\s*([\s\S]*?)\s*```/);
  if (!match) {
    throw new Error('未能从大模型回复中解析出生图参数 JSON');
  }
  const promptData = JSON.parse(match[1]);
  if (!promptData.base_prompt || !promptData.base_prompt.trim()) {
    throw new Error('大模型未返回三视图共用的产品主体描述(base_prompt)');
  }
  if (!Array.isArray(promptData.views) || promptData.views.length !== 3) {
    throw new Error('大模型未返回三视图的三套提示词');
  }
  if (promptData.views.some((v) => !v.angle_prompt || !v.angle_prompt.trim())) {
    throw new Error('大模型未返回完整的三视图角度描述(angle_prompt)');
  }
  const brief = content.slice(0, match.index).trim();
  return { brief, promptData };
}

module.exports = { SYSTEM_PROMPT, buildUserMessage, splitBriefAndPrompt };
