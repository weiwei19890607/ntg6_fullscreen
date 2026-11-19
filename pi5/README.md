# cp2cl：Raspberry Pi 5 移植方案

本目录提供**针对 Raspberry Pi 5 的 CarPlay → CarLife 桥接方案**，基于 cp2cl v0.16.3 和 ntg6_fullscreen。开发主机为 **Ubuntu 26.04**，树莓派运行 **Raspberry Pi OS Lite 64-bit（Debian 13）**；这不是已适配所有树莓派的通用固件，也不是 Buildroot 镜像。

连接路径：iPhone → 树莓派 5 的 5 GHz Wi-Fi → cp2cl → USB-C gadget → NTG6 CarLife。蓝牙用于发现手机及协商无线连接，媒体通过 Wi-Fi 传输。树莓派应通过支持数据传输的 USB 线连接车机的 CarLife USB 口。

## 已验证功能

2026-11-18 已在奔驰 MBUX NTG6 实车验证无线 CarPlay 和 CarLife 桥接，以及开机自动拉起画面：

- 配置为 1920×720、60 fps，视频直接转发；该配置不等同于独立测量的实际帧率。
- USB 启动直接呈现 `18d1:2d00` accessory。
- 提前连接手机：无需等车机启动 CarLife，先完成手机连接并准备视频通道。
- 视频通道就绪且车机尚未开始握手时，首次立即重连 USB；重新枚举后等待 3 秒仍无握手则重试，每次开机最多 5 次（含首次）。检测到任何握手或会话立即停止，不自动打断。该重试策略仍需实车验证。
- 退出到车机主页后，维持后台会话并支持重新进入。
- 5 GHz 热点、网页状态和日志、维护／普通模式切换、正常关机。
- NVMe 只读基线、内存覆盖层及临时日志，永久修改配置需进入维护模式。

这次实车日志中，USB 自动重连到车机请求视频约 1.57 秒；用户观察完整上电到画面约二十几秒，二者计时范围不同。其他车机和长期可靠性尚未完成验证。自动拉起过程见 [实车验证记录](docs/14-ntg6-startup-replug.md)。

## 构建与部署

在本目录执行（集成在 ntg6_fullscreen 仓库中时，先 `cd pi5`）：

```bash
scripts/checkout.sh
scripts/bootstrap-host.sh
scripts/build.sh native
scripts/test.sh
scripts/bootstrap-cross.sh
scripts/build.sh aarch64-unknown-linux-musl
```

源码版本锁定于 `upstream-lock.json`，可复现补丁保存在 `patches/`。`scripts/checkout.sh` 初始化子模块并应用补丁；不要直接使用未应用补丁的上游源码替代本方案。

部署前阅读 [安装说明](docs/02-installation.md)、[测试报告](docs/08-test-report.md) 和 [只读运行与维护](docs/09-readonly-operation.md)。后两份记录包含阶段性测试历史，最新自动启动结果见 [自动重连说明](docs/14-ntg6-startup-replug.md)。刷写脚本会修改目标存储，必须先确认目标设备。

首次安装的自动重连开关默认关闭；使用本方案的提前连接和自动拉起功能时，按 [提前连接说明](docs/13-early-phone-connection.md) 与 [自动重连说明](docs/14-ntg6-startup-replug.md) 配置 `early_connect` 及 `/etc/cp2cl/startup-replug.json`。辅助服务安装已集成至 release 安装脚本。

管理页默认地址为 `http://192.168.4.1/`，Wi-Fi 名称模板为 `raspberry_NTG6_5G`，蓝牙名为 `raspberry_NTG6_BT`；首次安装会生成热点密码。频段、国家码与信道应按当地法规和设备支持设置。

MFi 证书、私钥及 CarLife 认证材料需要使用者自行准备，仓库不包含这些材料。连接凭据、手机配对、原始日志、工具链、镜像和构建产物也不上传。

## 来源与许可

- [cp2cl](https://github.com/0x5e/cp2cl)
- [ntg6_fullscreen](https://github.com/weiwei19890607/ntg6_fullscreen)
- [LIVI](https://github.com/f-io/LIVI)

源码沿用各自许可（cp2cl 为 GPL-3.0-or-later，LIVI 保留原 NOTICE）；本目录新增脚本和补丁按 GPL-3.0-or-later 发布。
