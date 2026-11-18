# 硬件验证记录（2026-11-17）

以下为实际 Pi 5 测试；基础功能通过不代表真实 CarPlay 或 NTG6 通过。原始输出留在本地 logs/。

| 项目 | 结果与范围 | 证据 |
|---|---|---|
| 主机 | Ubuntu 26.04.1 x86_64 | 主机基线、apt 日志 |
| 安装 | 官方 Lite Trixie ARM64 写入、100% 回读验证；NVMe 根 /dev/nvme0n1p2 | 镜像/刷写日志、pi5-baseline.log |
| NVMe | 指定 SN740 512GB，根分区约 476.4GiB；本次未见持续 NVMe/AER 超时 | pi5-hardware-final.json |
| DWC2/ConfigFS | UDC、libcomposite、FunctionFS 实际可用 | USB/协议日志 |
| Ethernet gadget | Ubuntu 与 Pi 192.168.7.1/2，ping 3/3、平均约 0.122ms；随后卸载 g_ether | ethernet-gadget-ping.log |
| AOA | GET_PROTOCOL=2，六个字符串、START；18d1:4ee1→18d1:2d00，bulk IN81/OUT01，HS maxpacket512 | aoa-upstream-smoke.log、aoa-patched-protocol-smoke.log |
| CarLife 基础协议 | version3.0、HU_INFO、MATCH_STATUS/MD_INFO、1280×720@30 VIDEO_INIT ACK；VIDEO_START 收到向导 H264 | aoa-patched-protocol-smoke.log、pi5-guide-first.h264/png |
| 5GHz AP | CN/channel149/5745MHz，hostapd ENABLED | pi5-iphone-wifi-status.log |
| iPhone/DHCP/管理页 | 真实 AUTH/ASSOC/AUTHORIZED、DHCP 租约；用户确认 Safari 可进入管理页 | pi5-iphone-page-evidence.log、用户反馈 |
| 蓝牙基础 | hci0 Powered、BlueZ D-Bus；HU_INFO 后发布 iAP/CarPlay classic SDP/RFCOMM | pi5-radio-runtime.log |
| BLE/真实配对 | 未测试；此 CarPlay 路径使用 classic，源码另有未调用的 Android Auto BLE 广播函数 | 源码审查；不得当成 BLE CarPlay 验证 |
| 自动启动 | 一次暖重启后 USB/AP/DHCP/cp2cl 均 active，HTTP 可用 | pi5-autostart-after-reboot.log、pi5-autostart-journal.log |
| 故障恢复 | SIGKILL 后 PID 改变，NRestarts0→1，HTTP 恢复 | pi5-crash-restart-test.log |
| 重复安装/部署 | 配置和 AP 文件前后 SHA 相同；完整部署 SHA/进程/HTTP 健康通过 | pi5-bootstrap-idempotence.log、pi5-deploy-full-health.log |
| 供电 | **未通过**：内核记录过 Undervoltage detected；快照 get_throttled=0x50000 | pi5-hardware-final.json、内核日志 |

初期 AP 从 STA 切换会首次启动失败：已增加 hostapd 五次重试，且禁用发行版通用 hostapd 服务，防止竞争。初版 USB 准备脚本无冲突时意外返回 1 已修复。首次模拟主机遗漏 HU_INFO，只有心跳无向导帧；修正主机顺序后成功，失败记录保留为 aoa-patched-incomplete-host-sequence.log。

USB-C Gadget 与 g_ether 不能同时占 UDC，切换测试全程保留以太网 SSH。管理页只绑定 AP 地址。默认密码随机生成，本次按用户要求简化为合法的八位 WPA2 密码，本地凭据文件不入 Git。国家码/信道必须按实际所在地配置。

尚缺：合法 MFi 认证、真实 iPhone CarPlay 配对、BLE 独立验证、NTG6 连接、音频/触摸/Siri、冷启动循环及长期带载。供电需先换为能保留 USB2 device 数据、足额供电且防倒灌的方案，再做稳定性验收。
