# Pi 5 直接以 accessory 身份启动（2026-11-18）

用户要求先单独验证开机呈现18d1:2d00，目标是尝试触发NTG6自动发起CarLife；本次不添加启动延时或自动重新枚举。

## 改动

补丁patches/0004-pi5-direct-accessory.patch在gadget创建时直接采用accessory身份，保留原厂商、产品名和序列号。管理状态中的accessory按真实身份初始化，session_up仍须实际建立协议会话，不能把枚举成功报成CarLife已连接。原有AOA控制请求应答逻辑仍保留，收到53时返回already_accessory。scripts/checkout.sh保存并可重复应用此补丁。

## 等待后连接的缺陷与修正

首次改为直接accessory后，真实USB延迟连接测试发现协议响应无法解析；缓冲区残留000100020801，是MATCH_STATUS消息尾部。原因：上游在USB配置后静默2秒会发送诊断视频心跳，用1秒timeout取消发送。CarLife帧是外层头与内容两次写入，头已排队而内容被取消，主机晚些读取时，会把下一条正常协议响应错误拼入前一帧。

该问题此前常被从4ee1切换2d00的断开/重枚举消除；直接以2d00等待时必须修复。现在等待2秒只记录usb.protocol_wait，不往端点写探测帧；视频建立后的正常心跳保留。新增单测以仅容纳外层头的8字节duplex模拟背压，等待超过原探测超时时间，检查没有残留字节并验证后续协议应答。日志direct-accessory-idle-regression-before.log实际失败，after.log通过。

## 验证方法

在Ubuntu主机执行：

```sh
sudo python3 tests/carlife-auth-smoke.py --accessory --idle-seconds 5
```

此模式必须已存在序列号cp2cl-pi5的18d1:2d00，完全不发送AOA51/52/53；等待5秒后直接发送CarLife2.0及两次认证挑战，并用上游公钥校验返回值。认证成功结果由测试主机发送，仅证明真实Pi USB链路和签名响应，不代表NTG6实车自动启动已经通过。

## 回退与范围

最终版本4a14d00925f586a4；已知实车成功的旧版本27d9e599728f392f保留为/opt/cp2cl/previous，便于维护模式回退。实验中未修正等待问题的c10d3fdc7fd74b53不作为previous。

Wi-Fi/蓝牙名称与手机配对、MFi、1920×720@60保持现有配置。下次实车完全不点CarLife，观察车机是否主动进入；若仍不自动打开，记录该结果即可，不能把此实验描述为自动启动已解决。

## 本次结果

部署4a14d00925f586a4后，Ubuntu实际枚举18d1:2d00。完全不发送AOA51/52/53，在USB已就绪并再等待5秒后，CarLife2.0 MATCH_STATUS及384_1.0.0、1234567890_1.0.0两个认证响应均通过。Rust313项通过，HTTP3、只读3、网页恢复3、密钥防护3项通过。10个配置/蓝牙配对文件前后SHA一致。

已重启回普通protected模式，启动6.565秒日志明确startup mode=accessory、6.574秒创建18d1:2d00；Ubuntu再次直接识别2d00，API accessory=true、session_up=false、aoa_version=null，符合尚未连接真实车机的状态。测试主机程序已退出。证据logs/pi5-direct-accessory-auth-smoke-final.log、pi5-direct-accessory-auth-journal-final.log、pi5-direct-accessory-protected-final.log、direct-accessory-regression-final.log。
