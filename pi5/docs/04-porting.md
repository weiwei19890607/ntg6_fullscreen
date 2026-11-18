# 移植实现与构建

所有源码通过 Git submodule 锁定，独立补丁保存在 patches/。工作树已应用补丁；全新检出执行 `scripts/checkout.sh`，幂等检测 apply/reverse，遇未知冲突即退出。不要将 Orange Pi 固件刷入 Pi。

- `scripts/bootstrap-host.sh`：Ubuntu 26.04 系统依赖，已满足的包不重装，需要用户本机 sudo 认证。
- `scripts/build.sh native`：主机增量调试构建。
- `scripts/build.sh aarch64-unknown-linux-musl`：静态 ARM64 release，Rust target+Zig 编译 C/ASM+rust-lld 链接。工具链版本记录在日志。不会把 x86 ELF 误部署到 Pi。
- `scripts/test.sh`：已有 Rust workspace 测试、脚本语法、真实离线 HTTP 测试。
- `scripts/bootstrap-pi5.sh`：目标依赖/ConfigFS/设备树/AP/systemd 配置，需 Pi 5 ARM64、Pi OS，以太网 SSH。
- `scripts/deploy.sh user@pi [binary]`：SSH/SCP→SHA256 校验→版本目录→current 链接切换→服务/HTTP 健康验证；失败回滚原 current。SSH host key 必须正常校验，禁止自动绕过。
- `scripts/rollback.sh`：Pi root 运行，恢复 previous，保留配置/配对数据。回滚二进制不是配置数据库快照，未来涉及 schema 变更需另设迁移方案。

## 补丁

1. LIVI CpConfig now_playing 兼容及 musl ioctl 参数转换。保留所有其他订阅，Bluetooth 只不请求 now-playing，Wi-Fi/iAP2 media 保持请求。
2. cp2cl 新增 `--check`，仅加载配置和解析现有认证文件，不创建文件、不启用无线、不绑定 USB；报告 parsed_unverified 不代表证书真实有效。
3. `--offline-web` 仅监听 127.0.0.1:18080，使用实际嵌入页面/GET 状态和配置，不提供保存/重启/复位/重启设备路由，不运行硬件任务。页面数据是未连接状态。
4. 日志颜色单测显式启用 ANSI，修正 NO_COLOR=1 的测试环境依赖；生产日志行为不变。

## 服务

cp2cl-usb 预加载 dwc2/libcomposite 和 ConfigFS、拒绝其他 gadget 占用。cp2cl-ap 创建 192.168.4.1 并运行 hostapd，精确保留上游 `/run/hostapd.pid`。cp2cl-dhcp 使用独立 dnsmasq 配置，cp2cl 等这些服务和 Bluetooth 后启动；失败重启，不依赖图形界面。不假设 systemd active 表示 iPhone 已连接。

上游 mount/ConfigFS/BlueZ/设备访问需要 root，本阶段未添加会破坏 namespace/设备访问的过度沙箱。DHCP 服务显式保持 root 以保证 runtime leases 权限；后续可按 Pi 验证结果收敛权限。AP 配置文件 root-only、首次随机生成 WPA2 密码；已有密码在重复安装时保留。Web 原接口可修改配对/重启，无认证，生产只绑定 AP 地址并仅在受信网络使用。

持久配对和设置位于 /etc/cp2cl，BlueZ 数据位于 /var/lib/bluetooth，禁止每次启动清空。上游文件日志限制单份约 4MiB（见 logging.rs 实际常量）并保留一份轮转；Pi journald 使用 volatile/32MiB 上限，减少 SSD 写入。断电仍可能损坏尚未同步的数据，应实测恢复；暂不启用只读根文件系统。

实际结果见 docs/08-test-report.md 与 logs。ARM64 构建成功/QEMU 启动都不能证明 UDC/AP 或真实协议通过。

## Buildroot 后续

已有上游 Buildroot 基础，协议代码静态可交叉编译，具备准备条件；尚不具备迁移验收条件。需先完成 Pi OS 上 Pi5 内核/固件、brcmfmac/BT、dwc2/FunctionFS、NVMe/供电、认证和车机稳定性验证，再新增独立 Pi5 defconfig/overlay/服务，不直接移用其他板卡配置。

## Pi 实测后的修正

USB 准备无冲突时显式返回成功；AP 从 STA 切换时在服务内最多重试5次；通用 hostapd 先 unmask 再 disable，避免两个实例竞争。cp2cl 的 PartOf 关系使 AP/DHCP/蓝牙重启传播到主程序。CPU/内存/I/O accounting 已开启，内核不支持的指标仍标不可用。

bootstrap 重复执行保留配置与热点密码，实际 SHA 对比通过。默认 deploy 已在 Pi 执行 SHA/预检/原子链接切换/进程和 HTTP 健康检查；首次 HTTP 连接可能在重试中暂不可用，最终健康通过才报告完成。`CP2CL_STAGE_ONLY=1` 可只预置版本，`CP2CL_SSH_CONFIG` 可指定专用 SSH 配置。回滚逻辑尚未做目标机故障注入验证。

早期只有 Wi-Fi SSH 时使用 --prepare-only 和带自动恢复的 pi5-ap-window.sh；目前以太网已接入，正常安装不需要该临时窗口。Pi 服务及启动配置均已实际部署并经过暖重启验证。
