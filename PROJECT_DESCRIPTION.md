# Liangyaoyao Desktop Pet 项目说明

## 项目概述

这是一个运行在 Windows 上的透明桌面企鹅宠物。项目使用 Tauri 2 承载原生窗口，React 和 TypeScript 负责前端组合，PixiJS 负责透明精灵渲染与逐帧动画播放。

当前版本聚焦于稳定的桌宠基础体验：透明无边框窗口、置顶显示、窗口拖拽、配置驱动的动画资源、Idle 呼吸/眨眼，以及头部触摸互动。

## 核心能力

- 透明、无边框、固定尺寸、始终置顶的桌宠窗口。
- 鼠标拖拽移动窗口，原生 Tauri 命令负责窗口控制。
- 基于 `192x208` 帧的 WebP 精灵图播放。
- 动画目录与动画注册表分离：目录描述资源和帧参数，注册表描述语义动作、优先级和完成后的状态转换。
- PixiJS 播放器支持帧数、帧尺寸、FPS、循环、锚点和播放完成回调。
- 本地行为调度器按时间间隔触发轻量 Idle 动作。
- 开发环境支持数字快捷键测试动作，数字 `8` 触发 `touch_head_pat_bite`。

## 当前动画资源

正式运行资源位于 `public/assets/animations/`：

- `liangyaoyao-v2.webp`：原始兼容精灵图，保留用于既有方向和移动动作。
- `idle_breathe.webp`、`idle_blink.webp`：独立 Idle 呼吸与眨眼资源。
- `emote_tilt_head.webp`、`emote_puff_angry.webp`：头部倾斜和生气情绪。
- `touch_head_pat*.webp`：摸头开始、循环、结束、普通反应和咬手反应。
- `touch_head_pat_bite.webp`：16 帧、16 列、`192x208` 单帧的完整咬手动作。

咬手动作的姿态帧经过确定性拆帧、方向修正、基线校正和尺寸归一化。固定手部属于画面中的独立外部道具；运行时只加载最终精灵图，不在前端重新绘制手部。

## 运行时结构

```text
src/
|-- animation/      动画目录、注册表和 Pixi 播放器
|-- behavior/       状态机、拖拽、互动和本地行为调度
|-- character/      角色与画布配置
|-- config/         JSON 动画、行为和角色规格
|-- platform/       Tauri 窗口服务桥接
`-- App.tsx         应用初始化和事件转发

src-tauri/
`-- src/             原生窗口、托盘、拖拽和退出命令

public/assets/animations/
`-- *.webp           正式运行精灵图
```

关键配置：

- `src/config/animations.json`：文件路径、帧数、帧大小、FPS、循环和锚点。
- `src/config/animation-registry.json`：语义动作、分类、触发方式、优先级、状态和完成规则。
- `src/config/behavior.json`：拖拽方向阈值、Idle 调度和窗口缩放限制。
- `src/config/character.json`：角色画布、窗口内精灵位置和缩放。

## 开发与验证

环境要求：Node.js、npm、Rust 和 Tauri 2 工具链。

```powershell
npm.cmd install
npm.cmd run build
npm.cmd run tauri dev
```

开发模式下可以使用数字快捷键检查已注册动作：

```text
1  idle breathe
2  idle blink
3  walk left
4  walk right
5  tilt head
6  puff angry
7  head pat
8  head pat bite
9  push away
Esc  return to idle
```

提交前至少执行 `npm.cmd run build`。动画资源变更还应检查：

- 精灵图尺寸和帧列数是否匹配配置；
- 每帧是否为 `192x208`；
- 脚掌、翅膀和手部是否完整；
- 落地帧基线是否一致；
- 动作完成后是否回到 Idle；
- 速度是否与动作表现一致。

## 设计约束

- 企鹅身份以原版人设、canonical front 和 Idle 资源为准。
- 保持小黑点双眼、两只深色短翅膀、原版头身比、腹部、嘴巴和脚掌。
- 生成动作不能用机械平移替代完整姿态变化。
- 手部必须是独立外部道具，不得成为企鹅附肢或与翅膀融合。
- 生成候选、失败版本、拆帧缓存和运行时截图不进入正式资源目录。

## 当前范围与后续方向

当前版本不包含 AI 对话、记忆、插件系统、数据库、天气、服装系统或完整 Codex Pet 打包流程。相关目录和类型仅保留扩展接口。

后续新增动作应先更新角色规格和动画设计，再生成一条完整 coherent 动作条，经过确定性拆帧、透明/白底审查、GIF/WebP 预览和运行时验证后，才复制到 `public/assets/animations/` 并更新两份配置。
