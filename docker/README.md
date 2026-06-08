# wd6zn Docker 一键部署

这个目录把当前服务端包做成 Docker 部署：MySQL 5.6、CentOS 7 + PHP 5.x/Nginx、独立 game 容器。

## 部署

```bash
cd /root/wd6zn-docker
cp .env.example .env
# 可选：编辑 .env 里的 PUBLIC_IP、MYSQL_ROOT_PASSWORD、START_GAME
./deploy.sh
```

默认会：

- 从 `/root/wd6zn_extracted` 复制 `/home` 和 `/www` 到 `data/rootfs`。
- 自动探测公网 IP，并替换服务端里的旧 IP。
- 重写 `/www/wwwroot/zc/wd/110001_config_20190415.json` 的 DES 加密 `SdkConfig`。
- 删除已确认的 PHP RCE 后门文件和函数。
- 启动 MySQL、Web，并导入数据库。
- 保持 `game` 容器运行但不启动游戏二进制。

## 启动游戏进程

确认环境后改 `.env`：

```env
START_GAME=1
START_ZONE2=0
```

然后执行：

```bash
docker compose up -d game
```

## 访问地址

- SDK/API: `http://你的IP:81`
- 代理后台: `http://你的IP:82/admin`
- 注册页: `http://你的IP:82/reg`

## 重要说明

- Web 和 game 使用 host 网络，兼容旧代码里写死的 `127.0.0.1`。
- MySQL 容器只绑定 `127.0.0.1:3306`，不直接暴露公网。
- 如果宿主机已有 Nginx/PHP/MySQL 占用 81/82/3306，需要先停掉冲突服务或改端口。
- APK 仍需单独改包、重签，才能让客户端指向新的 IP。
