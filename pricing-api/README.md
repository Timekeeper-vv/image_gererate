# 之间味道 · Python 报价系统 MVP

这是一个独立的 Python/FastAPI 服务，用于后续承接“采购生产报价智能体”。当前不替换现有 Node 前端，先作为独立报价 API 运行。

## 已支持品类

| code | 品类 |
|---|---|
| `icecream` | 雪糕/冰品文创 |
| `chocolate` | 巧克力文创 |
| `fridge_magnet` | 冰箱贴/徽章/钥匙扣 |
| `plush` | 毛绒玩具/抱枕/挂件 |
| `stationery` | 文具/纸品周边 |
| `packaging` | 礼盒/手提袋/包装物料 |

## 输出内容

- 成本拆解
- 单件成本
- 建议报价
- 总成本
- MOQ 建议
- 数量阶梯价
- 工期拆解
- 风险预警
- 报价准确度范围
- 下一步建议

## 本地启动

```bash
cd pricing-api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

打开接口文档：

```text
http://localhost:8001/docs
```

## 测试

### 健康检查

```bash
curl http://localhost:8001/health
```

### 查看品类

```bash
curl http://localhost:8001/categories
```

### 巧克力报价

```bash
curl -X POST http://localhost:8001/quote \
  -H "Content-Type: application/json" \
  --data @examples/chocolate.json
```

### 冰箱贴报价

```bash
curl -X POST http://localhost:8001/quote \
  -H "Content-Type: application/json" \
  --data @examples/fridge_magnet.json
```

## 阿里云服务器启动

```bash
cd /www/role_create/pricing-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

后台长期运行推荐：

```bash
pip install -r requirements.txt
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8001" --name pricing-api
pm2 save
```

如果没有开放 8001 端口，建议先只让 Node 后端内网调用，不直接公网暴露。

## 重要说明

当前是 MVP 规则模型，不是最终供应商实时报价。建议按阶段定义准确度：

| 阶段 | 准确度 |
|---|---|
| 概念粗估 | ±25%-35% |
| 结构化估算 | ±12%-18% |
| 打样校准 | ±8%-15% |
| 供应商最终核价 | ±3%-8% |

后续要提高准确度，需要逐步补充：

1. 历史订单成本数据
2. 供应商报价数据
3. 原材料价格表
4. 工艺费率表
5. 不同品类的 MOQ 和损耗率
6. 实际延期/质检问题记录

## 食品类精算模型 v1

巧克力、雪糕已融合食品类成本公式：

```text
总成本 = 原材料成本 + 模具摊销费 + 包装费 + 工艺费 + 冷链/特殊存储费 + 认证检测费 + 版费/开机费 + 管理利润 + 税费
```

支持字段包括：

- `raw_material_price_per_kg`：主料单价，元/kg
- `auxiliary_material_cost_per_unit`：辅料单件成本
- `loss_rate`：损耗率
- `mold_type`：silicone / abs / metal / 3d_print
- `mold_fee`：模具费
- `mold_life_units`：模具寿命产量
- `amortization_strategy`：order / lifecycle / hybrid
- `color_process`：single / dual / multi / hand_painted
- `complexity_factor`：复杂系数
- `inner_packaging_cost` / `single_packaging_cost` / `outer_packaging_cost` / `transport_packaging_cost`
- `cold_chain_cost_per_unit`
- `detection_fee`
- `certification_fee`
- `setup_fee`
- `management_profit_rate`
- `tax_rate`

参考示例：

```bash
curl -X POST http://localhost:8001/quote \
  -H "Content-Type: application/json" \
  --data @examples/chocolate_detailed.json
```

注意：如果同时计入 15% 管理利润和 13% 税费，最终总额会明显高于只计算制造成本的小计。报价系统会严格按上述公式计算。
