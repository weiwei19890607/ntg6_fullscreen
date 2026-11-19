# NTG6 首次启动：手机就绪后有限次数重连 USB

## 首次单次重连的实车证据

用户确认：等 NTG6 启动后再插 USB 仍需手动启动，但网页“重启服务”可自动进入 CarLife。

原始日志 `/home/gawain/Downloads/cp2cl+5.log` 已归档为 `logs/pi5-ntg6-manual-replug-success-20261118.log`：

- 9.651 秒，iPhone 已发出首帧。
- 71.542 秒，`web.restart_requested`，同一时刻 `usb.replug action=disconnect`。
- 72.546 秒，USB 重新枚举。
- 72.846 秒，NTG6 主动发送 CarLife 2.0 协议版本。
- 72.855 秒，认证成功。
- 72.872 秒，CarLife 会话建立，复用已有手机会话。
- 73.230 秒，车机请求开始视频；Pi 请求新关键帧。

“重启服务”按钮实际调用 POST /api/restart，只触发 USB gadget 解绑/重新绑定，并不重启 cp2cl 进程或整机。之前聊天关于该按钮可能重启手机会话的说法过于保守；本次代码与日志确认早连接模式保留该手机会话。

## 自动化（当前策略）

主程序继续使用已实车确认的 `7de006c3c44e81e8`，通过独立的短时辅助服务复用相同 API，不改变 CarLife/MFi 协议实现。

- 程序：`scripts/startup-replug.py`，安装到 `/usr/local/lib/cp2cl/startup-replug.py`。
- 服务：`configs/systemd/cp2cl-startup-replug.service`，由 cp2cl.service 拉起。
- 开关：`/etc/cp2cl/startup-replug.json` 中 `{"enabled":true}`；新安装默认关闭。
- 前提：主配置的 early_connect 开启。
- 等待 USB 已枚举、AirPlay 验证完成且视频通道 active，就绪后立即触发（当前 settle=0，不额外等待）。
- 若已出现 CarLife 协议版本、认证请求、会话建立或编码状态，立即放弃本次开机的自动重连，不打断握手和后台会话。
- 首次就绪立即触发；每次触发前再次检查状态，调用 POST /api/restart。
- 每次 POST 后必须观察到 USB 未枚举，再观察到枚举成功；从枚举成功起等待 3 秒，无握手且手机仍就绪才重试。每次开机最多 5 次（含首次），第五次后再观察 3 秒并结束。
- 状态每 0.1 秒检查一次；USB 枚举使用 `/sys/class/udc/<controller>/state` 的实际内核状态，避免网页缓存标志跨短暂重连保持 true；15 秒内无法确认断开／重新枚举则退出，避免把旧的已枚举状态当作本次完成。
- `/run/cp2cl-startup/attempted` 以原子独占创建保留本次开机重试序列的处理记录。标记在服务重启后保留，整机重启后清除；辅助服务重启不会重新开始五次重试。HTTP 回应不确定时立即停止序列，不自动重试。
- 最多等待手机就绪 180 秒，没有满足条件则退出。不会无限轮询或反复重连。

原有“重启服务”按钮仍可手动使用。辅助服务退出成功而显示 inactive 属于正常状态。

持久安装需维护模式：运行 `scripts/install-startup-replug.sh`；`scripts/install-release.sh` 已集成安装，后续更新保留已有开关。查看日志：`journalctl -b -u cp2cl-startup-replug`。管理页下载的 cp2cl 日志会显示该操作对应的 `web.restart_requested` 和 `usb.replug`。

## 早期单次重连的验证及边界

九项单测通过：稳定等待、USB/手机条件、认证前跳过、已有会话跳过、最后检查时握手到达、HTTP 错误、超时、同次开机辅助服务重启不重复、POST 回应不确定不重试。安装脚本 shell 检查和 Pi 上 systemd 单元检查通过。

Pi 维护模式真实测试：77.263 秒发生唯一一次自动 USB 重连，cp2cl PID 始终为 937，手机首帧仍只有 11.268 秒的一次，AirPlay 连接也只有一次。重启辅助服务后日志为 `skipped=already_handled_this_boot`。

自动重连之后，真实 Pi USB 模拟车机验证两次 RSA 挑战、CarLife 2.0、1920×720@60；三次六秒暂停各收到 60 个后台心跳并恢复视频。测试进程已结束。

证据：`logs/startup-replug-tests.log`、`logs/pi5-startup-replug-first-run.log`、`logs/pi5-startup-replug-maintenance-journal.log`、`logs/pi5-startup-replug-usb-smoke.log`。

此阶段仅验证了手动按钮在真实 NTG6 上有效；自动触发的后续实车验收见本文末尾。

## 最终保护模式启动

当前和下次启动均为 protected，根为 overlay，主程序仍为 `7de006c3c44e81e8`。开机 10.195 秒手机首帧到达，13.294 秒自动触发唯一一次 USB 重连，14.310 秒完成重新枚举。整个启动日志只有一次手机首帧，没有因此重建 AirPlay 会话。辅助服务已持久启用，测试主机程序已退出。

最终证据：`logs/pi5-startup-replug-protected-final.log`。该阶段 USB 接 Ubuntu，属于部署验证；后续实车结果见本文末尾。

## 移除就绪后的额外等待

用户要求手机视频通道就绪后立即重连。`run()` 默认 settle 从 3 秒改为 0 秒；仍需 USB 已枚举、AirPlay 已验证、视频通道 active，而且未出现车机握手。状态每 0.5 秒检查一次，触发前再次确认；不设置额外三秒计时。

新增首次就绪即触发的回归测试，总计十项通过。上述三秒启动时刻为上一版本的历史验证记录。

零等待版本最终已在保护模式重启验证：手机首帧 10.029 秒，自动 USB 重连 10.161 秒，相差约 0.13 秒；11.175 秒完成重新枚举。整个启动只重连一次，手机首帧事件只有一次。证据 `logs/pi5-startup-replug-zero-protected.log`。


## 2026-11-18 实车自动拉起成功

用户提供 `cp2cl+6.log` 并确认通电后自动进入 CarLife 画面，主观总耗时二十几秒。原日志归档为 `logs/pi5-ntg6-auto-start-success-20261118.log`。

| 系统启动计时（秒） | 事件 |
| --- | --- |
| 6.437 | cp2cl 启动 |
| 10.990 | 手机视频通道附着 |
| 11.014 | 自动调用重连 API，USB 断开 |
| 11.032 | 手机首个视频帧到达 |
| 11.926 | USB 重新枚举 |
| 12.164 | NTG6 发出 CarLife 2.0 协议版本 |
| 12.172 | 车机认证成功 |
| 12.181 | CarLife 会话建立，复用手机会话 |
| 12.581 | NTG6 发出 VIDEO_ENCODER_START，Pi 请求关键帧 |

自动重连到车机请求视频相隔 1.567 秒；主程序启动到该请求相隔 6.144 秒。该次启动只有一次 USB 重连、一次手机首帧事件；没有重建手机 AirPlay 会话。

零等待条件是视频通道 active 且 AirPlay 已验证，不要求首帧已经到达。本次重连比首帧早 18 毫秒，符合实现。

日志时间来自 CLOCK_BOOTTIME，不包含内核启动前的固件引导时间；VIDEO_ENCODER_START 也不等同于屏幕实际显示首帧。因此不能把 12.581 秒当作完整的上电到画面耗时，用户观察的二十几秒应作为本次实际体验记录。精确端到端耗时需要外部同步计时。

结论：提前连接手机、视频通道就绪后一次 USB 重连的组合，已获用户实车自动拉起成功确认。本次只归档和更新记录，未修改或部署程序。


## 2026-11-19：3 秒间隔、最多 5 次

用户提供 cp2cl+7.log 并确认约 60 秒时手动点击 CarLife 启动。本次手机首帧 10.337 秒，自动重连 10.422 秒，重新枚举 11.430 秒；车机直到手动操作后 59.787 秒才发出协议版本，60.320 秒请求视频。单次自动重连未稳定触发车机，不能把此前一次成功解释为可靠性已验证；没有证据将失败归因于手机低电量模式。原日志仅本地归档。

用户指定重试策略已实现：首次立即重连，每次实际重新枚举完成后等待 3 秒，仍无握手才重试，最多 5 次（含首次）。任何协议版本、认证挑战、已有会话或编码状态都会立即结束自动序列；重试前仍检查手机认证及视频通道。POST 回应不确定、重新枚举无法确认均停止，不会无限重试。每次开机只启动一个序列。

主程序和六个协议补丁不变，仅更新独立辅助服务。21 项单测通过，涵盖三秒从枚举成功起算、五次上限、枚举中／等待中握手到达、第二次重连后停止、最后检查取消、未见断开边沿、手机失联、状态请求超时、POST 结果不确定和服务重启不重复。证据：logs/startup-replug-five-attempts-tests.log。新重试策略的 NTG6 自动拉起可靠性仍需实车验证。

Pi 维护模式实机验证：同一主进程 PID 940 下，104.729 秒开始本轮测试；第 1 次重新枚举 105.837 秒，第 2 次请求 108.855 秒，其余间隔约 3.02 秒；第 5 次请求 121.267 秒，125.403 秒以 attempt_limit=5 退出。另一次真实 USB 模拟握手通过 CarLife 2.0 及两次 RSA 挑战，辅助服务观察到握手后停止；测试主机程序已经退出。这些测试不代表新重试策略的真实 NTG6 可靠性已验证。证据：logs/pi5-five-replug-maintenance.log、logs/pi5-five-replug-handshake-stop.log。
