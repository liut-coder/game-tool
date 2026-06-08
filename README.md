# 游戏工具管理端

本目录是一个本机 Web 管理端，用来操作 `/root/wd6zn-docker` 里的 Docker 部署包。

启动：

```bash
cd /root/game-tool
python3 server.py
```

默认端口是 `8088`，启动日志会打印带 token 的访问地址。

已接入的动作：

- 保存部署参数到 `/root/wd6zn-docker/.env`
- 准备服务端 payload
- 重写公网 IP、MySQL 密码和 SDK 配置
- 一键执行 Docker 部署
- 启停 Web/Game 容器
- 查看 Docker Compose 状态和任务日志
