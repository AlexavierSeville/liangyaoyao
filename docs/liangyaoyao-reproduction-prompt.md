# 梁峣峣企鹅高一致性复现提示词

## 使用方式

本文件面向生成单个桌宠精灵帧，而不是生成角色海报或角色设定表。请同时使用以下图像参考：

1. **主参考**：`public/assets/animations/liangyaoyao-v2.webp`，只取第 0 行第 0 列的正面中性帧作为角色身份和几何基准。
2. **辅助参考**：`docs/references/liangyaoyao-persona-template-02.png` 和 `docs/references/liangyaoyao-persona-template-03.png`，只用于补充材质、喙眼关系、翅膀体块和表情。

不要把整张 8×11 图集当作构图参考，也不要生成多格图、转面表或新的精灵图排版。最稳定的做法是先从 `liangyaoyao-v2.webp` 裁出 192×208 的第 0 行第 0 列单帧，再把该单帧作为主图像参考。

## 正向提示词

以下整段可直接复制到支持图像参考的绘图工具中：

```text
以 Liangyaoyao 企鹅权威参考帧为唯一角色身份基准，生成一只与参考帧完全同一角色的单个桌宠精灵帧；主体特征：圆润、短小、胖乎乎的 Q 版企鹅，头部和后背是一整块连续的圆形深灰褐色轮廓，头身无明显颈部，脸部与腹部为同一块温暖奶油色区域，双侧各一只短而厚的深色鳍状翅膀，恰好两只小黑点眼睛、一个小型橙色椭圆喙、两只分开的短小橙色脚掌，保持参考帧的原始轮廓、部件数量和部件位置；体型比例：正面可见主体约宽 149 像素、高 198 像素，整体为宽头、短身、上窄下宽的饱满梨形，身体中心位于画布 x=96，头部轮廓约 x=22..169、y=5..97，奶油色腹部约 x=51..139、y=72..189，左右翅膀分别约 x=21..51 和 x=139..170、y=91..171，不能拉长、变瘦、变高、变成真实鸟类比例；姿态动作：正面直立中性站姿，身体垂直，头部正对镜头，左右翅膀自然向下并略向外，双脚平放在同一条基线上，脚掌完整且左右分离，除非另行描述动作，否则不改变身体中心、头顶位置、脚基线和头身比例；面部表情：中性、温和、略带亲切感，左眼中心约位于 (70.5,55)，右眼中心约位于 (117,55)，两眼为大小相近的黑色小椭圆，喙中心约位于 (95,61.5)，喙为小型橙色扁椭圆并带自然的上下喙分界线，不增加大眼、眼白、睫毛、眉毛或人类五官；服装配件：不穿衣服，不戴帽子、围巾、领结、眼镜、首饰或鞋子，不携带任何道具，不添加手、手指、尾巴或第三只翅膀；主配色：身体深灰褐约 #635245，脸部和腹部暖奶油色约 #FDF2D1，喙和脚掌柔和橙色约 #EEA95A，轮廓线深棕色约 #2F2923，眼睛和细节约 #2B251F，保持灰褐、奶油、橙色之间的原始比例，不使用纯黑纯白或蓝紫色；材质细节：二维手绘插画，柔和深色描边，哑光纸张和彩色铅笔颗粒，细微暖色纸纤维纹理，填色柔和且略有手工不规则感，轮廓清楚但不是硬边矢量，不要真实羽毛逐根刻画，不要塑料、金属或玻璃质感；背景场景：透明 RGBA 背景，无地面、无背景物、无渐变、无雪地、无冰山、无文字，角色边缘必须完整抠出；光影氛围：均匀柔和的低对比度漫射光，只保留参考帧中的轻微体积明暗，不添加强烈投影、发光、镜头光晕或戏剧性轮廓光；构图视角：单只企鹅、完整全身、正面平视、近似正交视角，画布严格为 192×208 像素，透明安全边距左 21 像素、右 22 像素、顶部 5 像素、底部 5 像素，脚掌最后不透明行约为 y=202，锚点固定为 (96,208)，不得裁切、旋转整张贴图或改变画布尺寸；画面风格：与权威图集一致的温暖儿童绘本式 2D 吉祥物插画，简洁色块、柔和手绘线稿、轻微纸张纹理，保持原角色的宽头、奶油脸腹、短翅膀、小橙喙和橙脚识别特征；色彩倾向：暖色、中低饱和度、低对比度，深灰褐与奶油色占主体，橙色只用于喙和脚掌，整体干净、柔和、亲切；输出质量要求：透明 PNG 或等效 RGBA 输出，边缘抗锯齿但不产生半透明脏边，单帧无文字无水印无 logo，人物轮廓、眼睛、喙、腹部和双脚清晰可辨，生成后不得自动重绘成另一只企鹅。
```

## 负面提示词

```text
new character design, different penguin, realistic bird, emperor penguin, photorealistic, 3D render, anime character, vector icon, glossy plastic, metallic, individual feathers, long neck, long beak, thin body, tall body, narrow head, small head, huge eyes, white eyeballs, eyelashes, eyebrows, human face, human hands, human fingers, extra wing, third wing, extra foot, long legs, tail, clothes, hat, scarf, bow tie, glasses, jewelry, shoes, backpack, props, multiple penguins, duplicate character, character sheet, turnaround sheet, contact sheet, sprite sheet, collage, multiple panels, full atlas layout, wrong camera angle, side view, back view, three-quarter view, rotated sprite, cropped feet, cropped wings, cut-off body, missing feet, asymmetrical eyes, misplaced beak, malformed beak, deformed wings, broken outline, transparent holes inside body, opaque background, white background, colored background, snow, ice, scenery, text, subtitle, watermark, logo, harsh shadow, dramatic lighting, glow, lens flare, blur, low resolution, oversharpening, noise
```

## 推荐固定参数

适用于支持图像参考的 SDXL/ComfyUI 类流程：

```text
模型：固定同一个 checkpoint、VAE 和角色 LoRA
主参考帧：liangyaoyao-v2.webp 第 0 行第 0 列，建议先裁成 192×208
辅助参考：persona-template-02、persona-template-03
图像参考强度：0.85
画布：192×208，比例约 12:13
输出：PNG，RGBA，透明背景
随机种子：284731
采样器：DPM++ 2M Karras
采样步数：32
CFG / Guidance：5.5–6.5
img2img 去噪强度：0.18–0.25
随机变化：0
批量大小：1
```

## 动作帧变体规则

如果要生成摸头、眨眼、走路或其他动作，只修改“姿态动作”和必要的“面部表情”句子，其余内容保持原样。普通动作中身体缩放保持在 97%–103%，身体中心偏移不超过 3 像素，头顶偏移不超过 4 像素，面部关键点偏移不超过 4 像素，脚基线偏移不超过 1 像素。

如果目标是大尺寸预览图而不是运行时精灵帧，可将画布改为 768×832 或 1536×1664，但必须保持 192×208 基准帧的宽高比、部件比例、脸腹轮廓和脚掌间距；不要改成 4:5 海报、角色设定表或多视图排版。

## 复现限制

纯文本提示词不能保证跨模型 100% 一致。要达到项目级稳定复现，必须固定模型版本、参考图裁切方式、图像参考权重、采样器、采样步数、随机种子、透明边缘处理和放大流程；批量动作资产还应在生成后检查 alpha 边界、脚基线和面部关键点。
