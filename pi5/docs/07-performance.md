# 性能与可靠性测量

这是无真实 CarPlay 流量的一次暖重启和 20 秒空闲采样，不能外推为实车性能。

| 指标 | 实测 | 限制 |
|---|---|---|
| systemd 启动 | kernel1.440s + userspace11.562s =13.002s；multi-user 约在内核计时7.391s | 一次暖重启，非冷启动；default target 和 multi-user 时刻不同 |
| 蓝牙服务 active | 约4.470s | 不代表手机配对完成 |
| AP active | 约7.386s | 不代表手机已入网 |
| cp2cl 进程 | 约7.391s | ExecMainStartTimestampMonotonic |
| 管理接口/bridge 日志 | 约7.443s | 不代表 CarPlay/NTG6 首帧 |
| cp2cl RSS | 6048KiB | 无真实 CarPlay；MemoryCurrent 不可用，使用 /proc |
| CPU | 20.00054s 内 ticks 从1到1，低于本次采样分辨率 | 不能声称运行 CPU 恒为0 |
| 整盘 I/O | 同期 NVMe 读0、写53248字节 | 整盘所有进程，不是 cp2cl 独占指标 |
| 温度 | 47.95°C | 单次空闲窗口，不是负载稳态 |
| 欠压/节流 | get_throttled=0x50000，历史欠压及节流位；快照当前位未置位 | 内核确有欠压记录，供电可靠性未通过 |
| CarPlay 连接/NTG6 首帧 | NOT_MEASURED | 无认证/车机 |

证据：logs/pi5-autostart-journal.log、pi5-runtime-resources.json、pi5-hardware-final.json。可用 scripts/measure-pi.py 重复采样；scripts/collect-hardware.py 提供未自动判定的原始输出。

SIGKILL 故障恢复和一次暖重启自动启动已通过；二进制回滚代码已实现，实际回滚尚未测试。未进行强制断电、冷启动10次、2h/8h带载、内存增长或真实流延迟测量。应先解决供电，再在相同供电/固件/手机条件下分别记录系统、USB、AP/蓝牙、CarPlay 连接、NTG6 首帧，保留失败样本。异常断电试验涉及数据风险，需要备份和明确授权。
