# 阿里云服务器一键部署/启动说明

上传代码到服务器后，进入项目目录执行：

```bash
cd /www/role_create
bash scripts/deploy-start.sh
```

这个脚本会自动做：

1. 检查并安装 Node.js
2. 检查并安装 Python3
3. 安装 PM2
4. 安装 Python 报价服务依赖
5. 启动 Python 报价服务：`127.0.0.1:8001`
6. 启动 Node 前端服务：`0.0.0.0:3000`
7. 执行 `pm2 save` 保存进程

## 日常重启

以后只改代码、不需要重新安装依赖时，执行：

```bash
cd /www/role_create
bash scripts/restart.sh
```

## 查看状态

```bash
pm2 list
```

## 查看日志

```bash
pm2 logs role-create
pm2 logs pricing-api
```

## 访问地址

```text
http://服务器公网IP:3000
```

## 阿里云安全组

需要在 ECS 安全组入方向开放：

```text
TCP 3000/3000
```

Python 报价服务端口 `8001` 默认只监听 `127.0.0.1`，不需要对公网开放。

## 如果端口被占用

```bash
lsof -i:3000
kill -9 PID
bash scripts/restart.sh
```

## 如果没有 config.json

脚本会自动从 `config.example.json` 复制一份，但你必须编辑：

```bash
nano config.json
```

填入硅基流动和 Tripo 的 API Key 后再正式使用。
