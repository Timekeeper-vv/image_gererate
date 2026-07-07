# Node 与 Python 报价服务联调

现有 Node 服务已增加两个代理接口：

```text
GET  /pricing/health
POST /pricing/quote
```

默认转发到：

```text
http://127.0.0.1:8001
```

如需修改 Python 服务地址，启动 Node 前设置：

```bash
export PRICING_API_URL=http://127.0.0.1:8001
node server.js
```

或 PM2：

```bash
PRICING_API_URL=http://127.0.0.1:8001 pm2 restart role-create --update-env
```

## 调用示例

当 Python 服务已启动后，可以通过 Node 访问：

```bash
curl http://localhost:3000/pricing/health
```

```bash
curl -X POST http://localhost:3000/pricing/quote \
  -H "Content-Type: application/json" \
  -d '{
    "category": "fridge_magnet",
    "quantity": 2000,
    "mode": "structured",
    "material": "锌合金",
    "length_mm": 65,
    "width_mm": 48,
    "height_mm": 4,
    "colors": 6,
    "process": ["压铸", "电镀", "滴胶"],
    "packaging": "standard"
  }'
```
