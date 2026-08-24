# Liangyaoyao Desktop Pet 项目记忆文件

> 这不是营销文案，也不是单纯的 README。本文件用于在开启新对话、切换模型或中断开发后，快速恢复项目上下文。继续工作前应先读完本文件，再查看代码和 Git 状态。

## 0. 当前结论

- 项目是 Windows 透明桌面企鹅宠物，技术栈为 Tauri 2 + React 19 + TypeScript + PixiJS 8。
- 当前工作分支是 `main`，远端是 `https://github.com/AlexavierSeville/liangyaoyao.git`。
- 最近一次已推送提交为 `ea0a458`，主题是交互动作、动画资源和项目文档。
- 正式运行资源只在 `public/assets/animations/`；`output/` 是本地生成/QA 中间目录，已加入 `.gitignore`，不能当作运行时输入。
- 当前最重要的正式动作是 `touch_head_pat_bite`，即“摸头后企鹅跳起咬手”。它已经从旧的 12 帧素材切换为修复后的 16 帧素材。
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
7. 咬手动作的 16 帧跳跃、咬合、撤退、落地和回到 Idle。
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
2. `public/assets/animations/idle_breathe.webp`。
3. `public/assets/animations/idle_blink.webp`。
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
| `touch_head_pat_bite` | `touch_head_pat_bite.webp` | 16 / 16 | 5 | 否 | 跳起咬手，当前重点资产 |
| `touch_head_pat_push_away` | `touch_head_pat_push_away.webp` | 8 / 8 | 4 | 否 | 推开反应 |
| `walking-right` | `liangyaoyao-v2.webp` row 1 | 8 | 6 | 是 | 向右走 |
| `walking-left` | `liangyaoyao-v2.webp` row 2 | 8 | 6 | 是 | 向左走 |
| `walking-up/down` | `liangyaoyao-v2.webp` row 7 | 6 | 6 | 是 | 纵向移动兼容片段 |
| `hover-jump` | `liangyaoyao-v2.webp` row 4 | 5 | 5 | 否 | 悬停跳 |
| `waiting/review/wave` | `liangyaoyao-v2.webp` rows 6/8/3 | 4–6 | 4–5 | 依配置 | 旧 atlas 微动作 |

### 咬手动作的历史决策

咬手动作经历过多轮生成和确定性修复。新对话不要把旧 Action A/B、旧 F07/F08/F09、失败素材或旧 12 帧横条重新接回运行时。

最终采用的原则是：

1. 企鹅姿态先作为完整 16 帧动作固定下来。
2. 固定手部是独立外部道具，不从企鹅身体或翅膀长出来。
3. 手部轨迹必须使用同一套形状和同一目标手指，不让模型逐帧重新发明手。
4. 用确定性拆帧、翻转、基线校正和尺寸归一化修复几何问题。
5. 正式运行时只绑定最终横向 16 帧精灵图。

动作语义顺序是：

`享受摸头 → 注意手 → 厌烦 → 下蹲蓄力 → 蹬地起跳 → 腾空前探 → 轻咬 → 保持咬合并留下浅红咬印 → 松口撤手 → 下降 → 落地回弹 → 哼/得意 → 回到 Idle`。

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
6  emote_puff_angry
7  touch_head_pat
8  touch_head_pat_bite
9  touch_head_pat_push_away
Esc  强制回到 Idle
```

按键触发后，应检查控制台是否出现：

```text
[animation-test] accepted touch_head_pat_bite
```

咬手动作在 5 FPS 下约 3.2 秒完成 16 帧，然后应返回 Idle。至少观察手是否出现、F05 下蹲、F06 起跳、F07/F08 腾空咬合、F10/F11 撤手方向、F12 落地和 F16 Idle 桥接。

### 提交前检查

1. `npm.cmd run build` 必须成功。
2. `git diff --check` 不得有空白错误。
3. 检查精灵图尺寸、透明度、帧数和列数。
4. 检查动作使用了正确的 `runtimeClipId`，没有绑定旧文件。
5. 检查非循环动作完成后是否回到 Idle。
6. 不要把 `output/`、截图、GIF、临时 manifest 或失败候选加入 Git。

## 6. 资源制作与 QA 规则

### 生成层与确定性层分开

图片生成只负责绘制新的完整角色姿态；确定性脚本负责拆帧、统一 `192x208`、保持身体中心和脚基线、必要时翻转完整帧、合成 review sheet、生成 GIF/WebP 和输出几何报告。

禁止用脚、脸、翅膀或手的局部拼贴修复单帧。禁止用机械平移同一只企鹅伪造完整跳跃。

### 咬手动作特有规则

- 手从画面上方进入，掌心和四个浅圆手指突起保持一致。
- 只有一根目标手指接近嘴巴；其他手指只构成掌缘轮廓。
- 不出现手腕、前臂、长白色连接段。
- 手不能连接企鹅身体、翅膀或腹部。
- F01–F03 手在头顶接触；F07–F08 目标手指到达嘴边；F09 开始出现浅红咬印；F13 之后不再有咬印。
- 允许局部遮挡表现嘴巴夹住手指，但不能把手简单盖在嘴上层。
- 若手与嘴接触不自然，应调整遮挡/企鹅姿态，不重新设计手掌。

### QA 重点

- 透明底和白底都要看，避免只看单一背景。
- 检查脚掌是否完整、是否被切掉一部分。
- 检查落地基线，避免起跳前后整体高度跳变。
- 检查 F10/F11 是否保持修正后的撤退方向。
- 检查小眼睛、两只翅膀和无额外附肢。
- 检查动作速度是否有足够的表演时间，而不是只看资源能否播放。

## 7. 目录与文件责任

```text
desktop-pet/
|-- public/assets/animations/   正式运行精灵图，只放已批准资源
|-- src/config/                 运行时目录、注册表、行为、角色规格
|-- src/animation/              Pixi 播放器和配置加载
|-- src/behavior/               状态机、互动、拖拽、Idle 调度
|-- src/character/              角色与画布加载器
|-- src/platform/               Tauri 窗口服务
|-- src-tauri/                  原生窗口、托盘、命令和权限
|-- scripts/                    可重复的本地资源构建/验证脚本
|-- docs/                       稳定角色规范和人工说明
|-- PROJECT_DESCRIPTION.md      本项目记忆文件
|-- PROJECT_STRUCTURE.md        目录职责概览
`-- README.md                   快速开始
```

### `output/` 的地位

`output/` 仅用于生成候选、拆帧缓存、QA 预览、运行时测试和历史备份，已经被 `.gitignore` 排除。新对话不要把其中的旧候选当成正式素材，也不要为了恢复上下文重新把整个 output 目录提交进 Git。

如果历史 output 已被清理，则不要假设旧候选仍可恢复；应以已提交的正式 WebP、配置和文档为准。

## 8. 历史问题与已解决问题

### 已解决

- 运行时曾绑定旧 12 帧咬手资源，现已改为 16 帧横条并同步配置。
- 咬手动作曾播放过快，active 动作 FPS 已整体下调并在 registry/catalog 中对齐。
- 旧拆帧曾出现脚掌被裁切和落地位置不一致，现已通过确定性提取、共享基线和边界安全检查修正。
- F10/F11 曾方向反了，已对完整帧做确定性水平翻转。
- 新咬手角色曾明显偏矮，已按稳定摸头动作高度做尺寸归一化；随后又做约 94% 横向压缩，使其更瘦高，同时保持垂直高度和基线。
- 生成中间目录曾非常庞大，正式提交已排除 output 和缓存。

### 仍需人工留意

- 咬手动作虽然几何和运行时绑定已修复，但部分生成姿态的风格、手部比例和动作情绪仍应由人工视觉审查决定是否最终保留。
- F13 的情绪效果、F08/F09 的咬合层次和红色咬印强度属于视觉判断，不要仅凭 JSON 报告自动宣布通过。
- 新动作若需要修改企鹅身份、手部设计或固定比例，必须重新经过角色规格审查，不要直接在正式 WebP 上做不可追溯的覆盖。

## 9. 新对话接手顺序

新模型接手本项目时按以下顺序执行：

1. 读取本文件、`README.md`、`PROJECT_STRUCTURE.md` 和 `docs/character-bible.md`。
2. 执行 `git status --short`，确认是否有用户未提交的变更；不要重置或覆盖它们。
3. 检查 `src/config/animations.json` 与 `src/config/animation-registry.json` 的帧数/FPS/运行时 ID 是否一致。
4. 检查 `public/assets/animations/` 中实际存在的文件，不从 output 推断正式状态。
5. 如果任务涉及图片生成，先确认用户是否明确要求生成；如果只是绑定、裁剪、缩放、翻转或 QA，优先使用确定性处理。
6. 如果任务涉及咬手动作，先锁定 `touch_head_pat_bite` 的 16 帧约束和本文件第 3、6 节规则。
7. 修改后运行构建和最小运行时验证，再更新文档/manifest。
8. 只有在用户明确要求时才提交、推送或删除正式资源；删除 output 等中间物可以清理，但不要误删 `public/assets/animations/`。

## 10. 变更记录

| 提交 | 内容 |
| --- | --- |
| `99db2ea` | 整理项目结构并补充运行时文档 |
| `777b32a` | 调整 Idle 呼吸速度 |
| `b3870a1` | 增加开发动画快捷键 |
| `ea0a458` | 增加互动动作、动画资源、角色规格和项目说明 |

当前分支：`main`。推送前先确认远端和最新提交，避免把新对话中的实验修改误推到正式分支。
