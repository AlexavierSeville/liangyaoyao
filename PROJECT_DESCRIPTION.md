# Liangyaoyao Desktop Pet 项目记忆文件

> 这不是营销文案，也不是单纯的 README。本文件用于在开启新对话、切换模型或中断开发后，快速恢复项目上下文。继续工作前应先读完本文件，再查看代码和 Git 状态。

## 0. 当前结论

- 项目是 Windows 透明桌面企鹅宠物，技术栈为 Tauri 2 + React 19 + TypeScript + PixiJS 8。
- 当前工作分支是 `main`，远端是 `https://github.com/AlexavierSeville/liangyaoyao.git`。
- 最近一次已推送提交为 `ea0a458`，主题是交互动作、动画资源和项目文档。
- 正式运行资源只在 `public/assets/animations/`；`output/` 是本地生成/QA 中间目录，已加入 `.gitignore`，不能当作运行时输入。
- 当前正在重做的正式动作是 `touch_head_pat_nip`，即“摸头后企鹅跳起轻咬指尖”；旧咬手素材已永久删除，不再作为参考。
- 当前没有完整 Codex Pet 打包、AI 对话、记忆、插件、数据库、天气或服装系统。这些目录或类型即使存在，也只是预留接口。

## 1. 项目目标与边界

### 目标

做一个可长期运行的 Windows 桌面宠物：企鹅显示在透明、无边框、置顶窗口中，可以被摸头、拖动和触发小动作；动画由精灵图和配置驱动，行为由状态机管理。

### 当前已实现

1. 透明、无边框、固定尺寸、始终置顶的 Tauri 窗口。
2. 原生窗口拖拽和托盘/退出控制。
3. PixiJS 精灵图加载、切帧、播放、循环和完成回调。
4. Idle 呼吸、眨眼、随机微动作。
5. 鼠标头部互动和长按触摸反应。
6. 触摸动作的 start/loop/end/reaction 语义注册。
7. 摸头后轻咬手指动作的 16 帧设计与运行时接入正在进行中。
8. 开发模式数字快捷键，用于快速查看已注册动作。

### 明确不在当前范围

- AI 对话、LLM 调用、长期记忆和联网能力。
- 插件系统、服装系统、数据库、天气、日历、IDE/Git 联动。
- 完整 9 行标准动作、16 方向 look atlas 和 Codex pet v2 打包。
- 自动把生成候选发布为正式素材。

如果新需求要求上述能力，应先单独拆任务，不要把它们默认为当前版本已经存在。

## 2. 角色身份与不可变视觉契约

角色 ID 是 `liangyaoyao_penguin`，角色名为“梁峣峣”。最终视觉身份由稳定旧资产决定，不由任何一次新生成的动作重新定义。

### 参考优先级

按以下顺序判断角色是否正确：

1. `public/assets/animations/liangyaoyao-v2.webp` 的第 0 行第 0 帧。
2. `idle_breathe.webp`。
3. `idle_blink.webp`。
4. 旧 atlas 第 1 行第 0 帧（右走）和第 2 行第 0 帧（左走）。
5. 已批准的动作只能表达动作，不得反过来成为角色身份参考。

机器可读规格在 `src/config/character-spec.json`，人工说明在 `docs/character-bible.md`。

### 必须保持

- 恰好两只小黑点眼睛，大小自然一致，不新增眼白或大眼。
- 恰好两只深色短翅膀，不得出现第三只翅膀、黑色手臂或附肢。
- 大圆深灰头部和背部、暖白脸部/腹部、小橙色椭圆嘴、橙色脚掌。
- 原版头身比、腹部轮廓、脚掌大小和脚掌间距。
- 柔和插画线条和纸张纹理；不要改成硬边矢量、写实鸟或 glossy 3D。

### 几何基准

- 每帧：`192x208`，RGBA/透明底。
- 精灵锚点：`x=0.5, y=1.0`，对应像素 `(96,208)`。
- 标准可见区域约为 `x=21..170, y=5..203`，宽约 `149px`、高约 `198px`。
- 脚最后不透明行约为 `y=202`，底部保留约 5px 透明边。
- 身体中心约为 `x=96`，脚基线容差约 1px。
- 普通动作身体缩放应保持在约 `97%–103%`，身体中心偏差不超过 3px，头顶偏差不超过 4px。

动作可以让外部道具伸出画布主体边界，但不能借此裁掉企鹅身体、脚掌或翅膀。

## 3. 当前正式动画资产

所有正式运行资源位于 `public/assets/animations/`，不要从 `output/` 直接运行。

| 运行时 ID | 文件 | 帧数/列数 | FPS | 循环 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `idle_breathe` | `idle_breathe.webp` | 8 / 8 | 2 | 是 | 默认 Idle 呼吸 |
| `idle_blink` | `idle_blink.webp` | 4 / 4 | 6 | 否 | 随机眨眼 |
| `emote_tilt_head` | `emote_tilt_head.webp` | 4 / 4 | 3 | 否 | 头部倾斜 |
| `emote_puff_angry` | `emote_puff_angry.webp` | 6 / 6 | 4 | 否 | 生气鼓气 |
| `touch_head_pat` | `touch_head_pat.webp` | 8 / 8 | 5 | 否 | 普通摸头反应 |
| `touch_head_pat_start` | `touch_head_pat_start.webp` | 6 / 6 | 5 | 否 | 摸头开始 |
| `touch_head_pat_loop` | `touch_head_pat_loop.webp` | 12 / 12 | 3 | 是 | 摸头循环 |
| `touch_head_pat_end` | `touch_head_pat_end.webp` | 6 / 6 | 5 | 否 | 摸头结束 |
| `touch_head_pat_nip` | `touch_head_pat_nip.webp` | 16 / 16 | 5 | 否 | 摸头后跳起轻咬指尖，重新设计中 |
| `touch_head_pat_push_away` | `touch_head_pat_push_away.webp` | 8 / 8 | 4 | 否 | 推开反应 |
| `walking-right` | `liangyaoyao-v2.webp` row 1 | 8 | 6 | 是 | 向右走 |
| `walking-left` | `liangyaoyao-v2.webp` row 2 | 8 | 6 | 是 | 向左走 |
| `walking-up/down` | `liangyaoyao-v2.webp` row 7 | 6 | 6 | 是 | 纵向移动兼容片段 |
| `hover-jump` | `liangyaoyao-v2.webp` row 4 | 5 | 5 | 否 | 悬停跳 |
| `waiting/review/wave` | `liangyaoyao-v2.webp` rows 6/8/3 | 4–6 | 4–5 | 依配置 | 旧 atlas 微动作 |

### 摸头后轻咬手指动作

动作设计、帧语义、参考关系和生成门槛记录在 `docs/touch-head-pat-nip-design.md`。旧咬手图、诊断图、修复图、候选图和旧提示词均已删除，不能恢复或复用。

最终采用的原则是：

1. 四组连续 2x2 storyboard 先锁定完整动作弧线。
2. 固定手部是独立外部道具，不从企鹅身体或翅膀长出来。
3. 同一根食指沿同一条右上方轨迹移动，只有 F09-F10 接触喙尖。
4. 用确定性拆帧、基线校正和尺寸归一化保持 192x208 运行时帧。
5. 正式运行时只绑定最终横向 16 帧精灵图。

动作语义顺序是：

`摸头 → 注意食指 → 蓄力 → 起跳 → 接近 → F09/F10 两拍轻咬 → 松口撤手 → 下落 → 无特效落地 → 得意地回到 Idle`。

## 4. 配置与运行时契约

### 两份配置必须同步

`src/config/animations.json` 是资源目录，定义文件路径、帧数、帧尺寸、FPS、循环、行列和锚点。

`src/config/animation-registry.json` 是语义注册表，定义动作 ID、分类、帧数、默认 FPS、触发方式、优先级、完成规则、状态和运行时 clip 映射。

对于 active 动作，以下关系必须成立：

```text
registry.frameCount == catalog.frames
registry.defaultFps == catalog.fps
registry.runtimeClipId == catalog.id
catalog.sheetColumns >= catalog.frames
```

改帧数、列数或速度时，必须同时修改两份配置。只改其中一份会导致旧资源被加载、帧越界或动作速度与注册表不一致。

### 播放链路

```text
App.tsx
  -> loadAnimationCatalog / loadAnimationRegistry
  -> PixiPetRuntime.create
  -> SpriteSheetAnimationPlayer.load
  -> PetStateMachine.requestAnimation
  -> player.play(runtimeClipId)
  -> onAnimationComplete
  -> PetStateMachine.handleAnimationComplete
  -> return_idle / transition_to / stay
```

`SpriteSheetAnimationPlayer` 使用 `1000 / fps` 计算帧间隔，非循环动作播放完毕后停在最后一帧，并通过完成监听器通知状态机。

### 状态与交互

- `PetStateMachine` 负责优先级、状态切换、动作完成规则和拖拽中断。
- `PetInteractionController` 负责指针命中区域、头部触摸、长按和拖拽。
- `LocalBehaviorScheduler` 每 `30–120s` 随机触发一次 Idle 微动作，并避免连续重复。
- `src/config/pet-hit-zones.json` 定义头部、腹部、翅膀和脚部的相对命中区域。
- active Touch/Emote 动作通常完成后回到 Idle；loop 动作不会自动结束。

## 5. 开发运行与测试

### 环境与命令

要求 Windows、Node.js/npm、Rust stable/Cargo 和 Tauri 2 CLI。

```powershell
cd E:\pet\desktop-pet
npm.cmd install
npm.cmd run build
npm.cmd run tauri dev
```

如果提示 1420 端口被占用，先检查残留的 Vite/Tauri 进程；不要直接启动第二个运行时造成旧资源和新资源混用。

### 开发快捷键

仅在 `import.meta.env.DEV` 下注册：

```text
1  idle_breathe
2  idle_blink
3  walk_waddle_left
4  walk_waddle_right
5  emote_tilt_head
