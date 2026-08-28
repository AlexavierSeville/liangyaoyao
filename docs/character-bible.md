# 梁峣峣企鹅角色圣经

这份文件是后续桌宠图片、动作和表情的唯一角色标准。用户在 2026-08-26 提供的第一张整套企鹅图（8×11、1536×2288）是动作图集与方向结构的最高权威；仓库中的 `public/assets/animations/liangyaoyao-v2.webp` 已与该图逐像素一致。第二、第三张附件已登记为辅助人设模板，用于补充大比例外形、三分之四视角、侧身轮廓、五官和材质细节，但不能覆盖第一张图的图集几何与方向顺序。

## 唯一权威来源

- 权威图：`public/assets/animations/liangyaoyao-v2.webp`
- 图集规格：8 列 × 11 行，每格 `192×208`，透明 RGBA
- 图集语义：标准动作行 0–8；视角行 9–10
- 辅助人设模板 02：`docs/references/liangyaoyao-persona-template-02.png`，补充正面、三分之四、屏幕右侧身、表情和材质细节
- 辅助人设模板 03：`docs/references/liangyaoyao-persona-template-03.png`，补充正面、三分之四、屏幕右侧身、喙眼关系、翅膀体块和材质细节
- 生成动作时，先锁定本文件与权威图中的角色，再单独描述动作；任何动作候选与本文件冲突，都判定为候选错误。
- `idle_breathe.webp`、`idle_blink.webp`、摸头、推开手、咬手和其他旧动作不参与角色身份定义；它们不能覆盖权威图集或辅助模板。

The machine-readable source is `src/config/character-spec.json`.

## Canvas And Anchor

- Every runtime frame is exactly `192x208` pixels.
- The sprite anchor is `(0.5, 1.0)`, equivalent to pixel `(96, 208)`.
- The standard visible body bounds are approximately `x=21..170`, `y=5..203` using an alpha threshold of 12.
- The last opaque foot row is approximately `y=202`; preserve five transparent rows below it.
- The standard body center is approximately `x=96`.
- Keep at least 21 px left, 22 px right, 5 px top, and 5 px bottom transparent margin for the unextended body.

An action may extend above the head when its semantics require it, such as a hand touching the head, but the penguin body and feet must still obey the standard bounds and baseline.

## Proportions

The canonical front pose is round, short, and chubby. Its visible height is about 198 px and visible width about 149 px.

- The head silhouette reaches from about `y=5` to `y=97`.
- The cream belly contour is about `x=51..139`, `y=72..189`.
- Flippers are short and tapered, beginning around `y=91` and ending around `y=171`.
- Each foot is about 48 px wide and 28 px high. Foot centers are approximately `x=56` and `x=134`, with a 30 px inner gap.
- Eye centers are approximately `(70.5, 55)` and `(117, 55)`.
- The beak is a small orange oval centered near `(95, 61.5)`.

For ordinary action deformation, keep body scale within 97%-103%, body center within 3 px, head top within 4 px, and facial landmarks within 4 px. These are animation tolerances, not permission to redesign the character.

## Visual Identity

The five strongest recognition signals are:

1. A large round charcoal head and back.
2. A warm cream face and belly patch.
3. A small orange oval beak.
4. Short orange feet with fixed spacing.
5. Short tapered flippers and a wide, upright front silhouette.

The rendering is a soft illustrated 2D character with a warm paper-like texture and a dark soft outline. Do not turn it into a vector icon, glossy 3D model, realistic bird, or a newly designed mascot.

## 四个主视角

以下视角以权威图的视角行与侧身动作行为几何标准；辅助模板只用于补充体块、材质和五官细节。

### 正面（front）

- 参考：图集标准正面行（row 0）的中性帧，以及视角行中正面/近正面帧。
- 头、脸、腹部和双脚整体近似左右对称；双眼都可见，喙位于中轴附近。
- 双翅从身体两侧向下展开，不能遮住腹部中央；双脚在同一基线附近左右分布。
- 闭眼、眨眼、恼怒、微笑、张嘴等只改变表情，不改变头身比例。

### 右侧（screen-right profile）

- 参考：权威图中企鹅朝屏幕右方的侧身行（row 1）及视角行的 090° 附近。
- 喙尖明确朝右，近侧眼可见，远侧眼逐渐隐藏；奶油色脸腹区域向右形成连续的胸腹轮廓。
- 背部深色轮廓在左侧形成完整弧线；近侧翅膀覆盖在背部外侧，远侧翅膀可减少但不能断裂。
- 两只脚按动作自然前后错位，但仍是两只完整橙色脚；不能把侧身画成单脚或长腿。

### 左侧（screen-left profile）

- 参考：权威图中企鹅朝屏幕左方的侧身行（row 2）及视角行的 270° 附近。
- 与右侧视角形成严格镜像关系：喙尖朝左，近侧眼保留，奶油色胸腹朝左，深色背部向右收束。
- 不能把左侧视角误画成正面歪头；头部、喙、腹部和翅膀必须共同转向左方。
- 保持与右侧相同的体量、头身比例、脚大小和描边材质。

### 背面（back / up-facing）

- 参考：视角行 000° 附近的背向帧。这里的“背面”是企鹅背部朝向观察者，不是把角色翻转或裁掉身体。
- 主要可见深灰褐色圆背和连续的后脑轮廓；奶油色腹部应大幅隐藏，只允许在转向过渡时保留窄边。
- 喙和双眼应隐藏或只保留极少侧向线索；不能在纯背面重新画一张正脸。
- 双翅从背部两侧形成自然的深色轮廓，必须与身体相连；双脚仍为橙色、短小、同一角色的脚。

## 中间视角与方向连续性

- 视角行按固定顺序使用 16 个方向：`000°、022.5°、045°、067.5°、090°、112.5°、135°、157.5°、180°、202.5°、225°、247.5°、270°、292.5°、315°、337.5°`。
- 方向变化应通过头部、喙、脸腹边界、背部轮廓、眼睛可见程度和翅膀遮挡共同完成；不能只移动瞳孔，也不能旋转整个贴图来假装转身。
- 从正面到侧面：远侧眼逐步隐藏，喙沿转向方向移动，奶油色腹部变窄，深色背部占比增加。
- 从侧面到背面：喙和眼睛继续离开可见面，奶油色腹部收窄并消失，深色背部成为主轮廓。
- 左右方向必须保持视觉一致：同角度的左、右视图在体量、基线、描边、脚部大小上相互对应。
- 相邻方向不能出现突然换头、跳宽、跳高、脚基线断裂、翅膀数量变化或颜色/纹理切换。

## 固定外形补充

- 头部和背部为连续的大块深灰褐色圆弧；头顶宽、侧面饱满，不能拉长成尖头或瘦长体型。
- 脸和腹部是同一块温暖奶油色区域，脸颊向下自然过渡到腹部；不能变成窄胸或分离的白色贴片。
- 喙是小型橙色椭圆，张嘴时只能沿自然上下结构开合，不能变成长鸟喙或夸张大嘴。
- 双翅短而厚、末端圆钝；不能变成长臂、手掌、第三只翅膀或独立漂浮部件。
- 双脚橙色、扁圆、短小，左右分开且间距稳定；不能增加脚趾数量或变成长腿。

## 生成前硬性检查

1. 挂载权威图集和两个辅助人设模板作为角色参考；权威图集负责帧几何与方向顺序，辅助模板负责外形细节，不要把任何咬手、摸头或其他旧动作作为人设参考。
2. 先描述视角和角色外形，再描述动作轨迹；不要让图片模型自行推断企鹅的正面、侧面或背面结构。
3. 一次生成一整行动作帧，保持同一角色、同一体量、同一基线；不要拼接独立单帧。
4. 在白底、灰底和透明背景上检查：轮廓完整、没有断裂或内部透明洞、没有第三只翅膀、没有手部残片、没有脚基线跳动。
5. 正面、背面、左侧、右侧四个方向先通过硬门槛，再检查中间角度的连续性。

Approximate palette anchors are cream `#FDF2D1`, charcoal `#635245`, outline `#2F2923`, orange `#EEA95A`, and eye/detail dark `#2B251F`. These are reference colors; preserve the visual relationship and texture rather than applying flat fills.

## Reference Frames

| Role | Source |
| --- | --- |
| Front standard | `liangyaoyao-v2.webp`, row 0 column 0 |
| Front closed eyes | `liangyaoyao-v2.webp`, row 0 column 3 |
| Right walk standard | `liangyaoyao-v2.webp`, row 1 column 0; runtime clip `walking-right` |
| Left walk standard | `liangyaoyao-v2.webp`, row 2 column 0; runtime clip `walking-left` |

## Generation And Review Rules

Before generating an action, provide the character spec as the invariant reference and describe the action separately. Do not ask an image model to invent a new character sheet.

For every generated frame:

- preserve `192x208`, alpha, anchor, body scale, face landmarks, belly contour, flipper length, foot size, and foot baseline;
- compare the neutral start/end frames against the front standard in the authoritative atlas;
- reject any frame whose neutral penguin looks shorter, taller, wider, or narrower than the canonical body;
- inspect the result on a solid background as well as transparent compositing;
- measure alpha bounds and baseline before runtime integration.

任何生成动作与本文件冲突时，动作图必须被丢弃并重新生成；不得为了迁就动作图而修改企鹅人设。若权威图集与辅助模板出现几何冲突，以权威图集为准；若只是材质、表情或三分之四体块细节，则综合两个辅助模板的共同特征。
