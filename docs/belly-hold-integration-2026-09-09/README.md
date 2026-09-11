# 肚子长按动作接入

用户已批准 v6 程序合成候选，并授权接入及制作连贯演示。

## 运行行为

- 按住肚子 400 ms 后进入 `touch_belly_rub_loop`，12 帧、每帧 140 ms，循环播放。
- 从按下时刻开始随机计时 5–10 秒，触发已有 `touch_belly_dislike`，12 帧、8 fps，仅播放一次；完成后回到待机。
- 提前松手、指针取消、拖动或销毁控制器均停止享受循环并清除计时。松手不会截断已经触发的不耐烦动作，也不会覆盖更高优先级动作。
- 肚子单击仍使用原怕痒动作；翅膀触摸逻辑保持现有行为。

## 素材与衔接

- 新循环来源：`output/touch-hold-draft-2026-09-09/candidate-v6-composite/frames`，使用用户认可的同一手型和顺时针轨迹。
- 采用整段相同缩放和位置变换，保留抬头、低头与手脚微动作。基准角色高度 198、脚底 y=215、头部中心 x=159（逻辑像素）。输出 640×456 的 @2x 无损 WebP。
- 肚子不耐烦采用此前用户认可的局部身材修订 candidate-v1，帧序不变。
- 在进入享受动作、不耐烦及回到待机时加入 160 ms 交叉淡化以缓和绘制姿势切换；循环内部保持原 12 帧，不插入叠影帧。这是短淡化衔接，并非新增逐帧绘制的过渡动作。
- 原肚子不耐烦素材、接入前配置与旧可执行程序均保存在 `backup/`。

## 演示

- `demo.html`：可暂停、拖动进度的演示页面。
- `belly-hold-continuous-demo.webm`：实际应用 WebGL 渲染录屏，去掉启动空白。
- `belly-hold-continuous-demo.gif`：同一录屏的 10 fps 便捷预览，没有加速动作或拼接阶段。
- 仅在录制浏览器中固定随机样本 0.32，实际测得按下后 6634 ms 触发不耐烦。正式应用仍随机使用 5–10 秒。

## 验证

- `node scripts/test-touch-reactions.cjs`：25 项通过，覆盖 400 ms 起播、持续循环、5/10 秒边界、松手/取消/拖动/销毁/新指针会话、过期完成事件、更高优先级动作保护和三个显示比例。
- `scripts/validate-touch-reaction-size.py`：原三套反应共 36 帧无裁切，基准高度仍与母版一致。
- 浏览器真实长按录制通过，页面异常与失败资源请求均为 0；详见 `browser-check.json`。尺寸对比见 `alignment.png`。
- TypeScript/Vite 构建通过；Tauri Windows release 构建通过。仅有产物大小提示及链接器创建库提示，无构建失败。
- 新构建已复制到项目根目录 `desktop-pet.exe`，与 release 文件 SHA256 一致。未自动启动或关闭用户运行中的桌宠。

复现脚本：`scripts/install-belly-hold.py`、`scripts/record-belly-hold-demo.cjs`、`scripts/package-belly-demo.py`。
