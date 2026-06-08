# wd6zn Docker 部署脚本

这个目录保存当前阶段的 Docker 改造脚本。它不是完整最终版；默认只部署 MySQL + Web/PHP/Nginx，用来跑注册页、SDK/API、代理后台等 Web 入口。

`game` 服务保留为手动调试 profile，但默认不会创建、不会启动，也不会由 `deploy.sh` 拉起。之前直接启动游戏进程会大量加载脚本并导致容器 137 退出，所以不要把它放进默认部署链路。

## 默认部署

```bash
cd /root/wd6zn-docker
cp .env.example .env
# 编辑 .env 里的 PUBLIC_IP、MYSQL_ROOT_PASSWORD 等参数
./deploy.sh
```

默认流程：

- 检查 Docker/Compose、源目录、SQL 文件和端口状态。
- 从 `SOURCE_ROOT` 复制 `/home` 和 `/www` 到 `data/rootfs`。
- 替换旧公网 IP、MySQL 密码和本地数据库连接配置。
- 重写 `/www/wwwroot/zc/wd/110001_config_20190415.json` 里的 DES 加密 `SdkConfig`。
- 删除已确认的 PHP RCE 后门文件和函数。
- 启动 MySQL、导入数据库、启动 Web。
- 不启动 game。

## 访问地址

- SDK/API: `http://你的IP:81`
- 代理后台: `http://你的IP:82/admin`
- 注册页: `http://你的IP:82/reg`

根路径 `/` 可能仍是原包自带默认页，不代表业务入口失败。

## 手动调试 game

默认不要启动。确实要单独调试时，先确认机器内存、数据库导入和端口，再手动执行：

```bash
docker compose --profile game up -d --build game
```

如果 `.env` 里 `START_GAME=1`，`deploy.sh` 会直接拒绝继续，避免误启动游戏进程。

## 重要说明

- Web 使用 host 网络，兼容旧 PHP 代码里写死的 `127.0.0.1`。
- MySQL 容器只绑定 `127.0.0.1:3306`，不直接暴露公网。
- 如果宿主机已有服务占用 81/82/3306，需要先处理端口冲突。
- APK 仍需单独改包、重签，客户端才会指向新 IP。
