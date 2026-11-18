# NTG6 返回主目录后恢复 CarLife（2026-11-18）

## 本次实车证据

用户提供cp2cl+4.log（134行），确认直接accessory仍需手动启动；回到车机主目录数秒后再点CarLife，等待后报连接失败。

6.972秒USB配置，7.475秒仅AOA版本查询，69.509秒才开始CarLife协议，69.519秒认证通过，72.844秒手机首帧。113.136秒KEYCODE_MAIN，113.275秒VIDEO_ENCODER_PAUSE及VR idle，然后日志停止。文件没有后续START、认证拒绝或USB断开记录，不能把失败直接宣称为重新认证失败，也不能证明用户第二次点击后NTG6是否真的发过恢复请求。

直接2d00实验未达到自动打开CarLife界面的目标；自动启动仍未解决。

## 确定的实现缺项与本次修正

原代码收到PAUSE将started_at清空，tick在started_at为空时立即返回，所以暂停画面同时停止视频通道心跳。与源码“后台仍发送心跳”的注释不一致。其他独立实现也记录了暂停时仍需要VIDEO_HEARTBEAT，否则部分车机会在数秒后判定对端失活，但这些观察不能直接代替NTG6实车验证。

参考：[协议观察记录](https://github.com/FF1239/Limo-carlife/blob/main/docs/carlife-proto-messages.md)、[开发者暂停保活问题记录](https://habr.com/en/articles/1104086/)。

新增独立video_paused状态；对日志确认的DAIMLER渠道20062105，PAUSE后立即发送一次心跳，随后每100毫秒保活，停止图像数据；START时退出暂停，沿用原前台通知和请求关键帧流程。RESET停止背景保活。未对未建会话或其他渠道启用背景心跳，保留此前不发送初始探测半帧的修正。

新增回归测试执行三轮PAUSE/START，检查后台心跳持续、encoding=false且session_up=true，以及恢复后encoding=true、整个过程只有一轮会话up/down。实际修前失败、修后通过。独立补丁0005接在0004之后，checkout脚本可重复应用。

## 真实 USB 验证方法

```sh
sudo python3 tests/carlife-auth-smoke.py --accessory --pause-resume
```

模拟DAIMLER渠道和1920×720@60握手，验证认证后连续三次PAUSE，每次停留6秒并接收心跳，检查后台不发送视频，发送前台命令并验证响应，再START并等待视频数据恢复。模拟测试的成功不等于真实NTG6复测通过。

本次保留直接2d00身份，不叠加延时重新枚举实验，优先验证退出后恢复的稳定性。

## 本次完成的验证

部署66208fae6dc77fab。真实Pi USB三轮测试每轮暂停6秒，均收到60次背景心跳，期间不再输出视频帧；前台命令能得到响应，START之后视频数据恢复。测试期间真实iPhone通过BT/Wi-Fi iAP2及MFi认证，并收到手机首帧；恢复时原有关键帧请求流程运行。此处主机是模拟器，没有NTG6显示/解码验收。

Rust314项及HTTP/只读/网页恢复/密钥防护各3项通过；10个配置和配对文件前后SHA一致。测试程序已退出，previous保留实车成功基线27d9e599728f392f。待用户实车复验返回主目录后恢复，不将本次模拟成功宣称为已解决真实车机故障。

证据logs/pi5-ntg6-pause-usb-smoke.log、pi5-ntg6-pause-usb-journal.log、ntg6-pause-regression-before.log、ntg6-pause-regression-after.log、ntg6-pause-regression-full.log。

最终重启已确认protected/overlay，current=66208fae6dc77fab，previous=27d9e599728f392f；USB仍为18d1:2d00，未保留模拟器。证据logs/pi5-ntg6-pause-protected-final.log。
