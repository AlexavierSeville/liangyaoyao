# 母版比例微调候选

历史阶段记录：该身材候选的肚子部分已获确认并用于正式接入；翅膀后来由重新创作并统一身材与颜色的素材替代。下文描述的是当时审核状态，当前结果见 `../work-summary-2026-09-11.md`。

用户明确选择“用程序局部调整现有帧的比例，不重新生图”。脚本 `scripts/preview-touch-proportions.py` 读取现有 36 帧，仅写入本目录下的 `candidate-v1`，没有调用图片 API 或修改网络配置。

母版依据：`E:/pet/origin/母版.zip` 内的 `current-runtime/liangyaoyao-v2.webp`；已验证与项目权威图 SHA-256 一致。使用第 0 行第 0 列中性正面作为身体比例基准。

## 本次调整

- 保持头顶、脚底和总体 198 px 高度的基准。
- 肚子、左翅膀、右翅膀分别按 0.91、0.85、0.87 的比例收窄头部；腹部采用 0.89、0.87、0.88 的局部横向比例，平滑过渡到脚掌原宽度。
- 将中性喙位置从约 y=78 / 82.5 / 80 调整到 y=74，面部和颈部一同过渡，避免单独挪动五官。
- 上移腹部与脚掌交界，恢复原先过扁的脚掌厚度。踢脚和转身等原始动作仍保留。
- 手部从角色中独立保留，不做形状拉伸；整组统一向身体方向平移 8 px、向上平移 5 px以跟随新的接触位置。
- 每组使用同一套连续坐标映射，不逐帧重新拟合或改变顺序。透明边缘使用预乘 alpha 插值，避免变形产生白边。

这次校正针对头腹与脚掌比例。原素材的纸纹、眼睛画法、翅膀姿态和动态表情没有重绘，候选不等同于逐像素复刻母版。手部接触处和抬脚姿势也应在确认时查看。

## 对比与动画

[母版 / 当前 / 候选三列对比](candidate-v1/master-current-candidate.png)

[肚子动作预览](candidate-v1/touch_belly_dislike-preview.gif)

[左翅膀动作预览](candidate-v1/touch_flipper_react_screen_left-preview.gif)

[右翅膀动作预览](candidate-v1/touch_flipper_react_screen_right-preview.gif)

测量依据见 `measured-proportions.json`，候选处理参数见 `candidate-v1/manifest.json`，透明孔洞和边界检查见 `candidate-v1/qa.json`。

下一步仅在用户确认体型后，才将候选导入运行素材、复核动作衔接并重新构建程序。
