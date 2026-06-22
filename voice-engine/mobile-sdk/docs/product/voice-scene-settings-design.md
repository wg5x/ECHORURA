# 音色场景与设置设计

本文基于当前代码里的音色、模型、角色提示词和场景模板整理，不把外部音色表或未来克隆音色当成已支持能力。

## 1. 当前边界

当前前端暴露两类实时语音模型：

| 模式 | 实际模型 | 适合场景 | 主要配置入口 |
| --- | --- | --- | --- |
| O2.0 默认模式 | `1.2.1.1` | 助手、陪练、问候、播报、轻陪伴 | `botName`、`systemRole`、`speakingStyle` |
| SC2.0 角色扮演 | `2.2.0.0` | 强人设角色、剧情对话、虚拟角色体验 | `characterManifest` |

O2.0 更适合稳定业务场景。它的提示词由基础人设、背景人设、对话风格组成，便于做安全边界、报告口径和任务目标。

SC2.0 更适合角色资产。当前每个 SC2 音色都绑定一段较长的 `characterManifest`，里面包含姓名、年龄、职业、故事背景、喜好、常用表达和回复要求。它更像角色卡，不适合作为普通客服、医疗、法律、金融等严肃场景的默认模型。

## 2. 已有场景

当前代码已内置 3 个 O2.0 场景，都是可直接用于产品演示的稳定场景。

| 场景 | 用户 | 音色 | 设置重点 | 不做事项 |
| --- | --- | --- | --- | --- |
| 晚间复盘 | 独居青年、轻压力人群 | Vivi 2.0 `zh_female_vv_jupiter_bigtts` | 温和、短句确认、睡前梳理今天和明日小计划；语速 `-4` | 不做心理诊断，不承诺治疗，不制造陪伴依赖 |
| 口语陪练 | 学生、职场学习者 | 小何 2.0 `zh_female_xiaohe_jupiter_bigtts` | 先问语言和主题；轻量纠错；语速 `-2` | 不频繁打断，不承诺考试或面试结果 |
| 适老问候 | 老年人、家庭陪伴试点 | 云舟 2.0 `zh_male_yunzhou_jupiter_bigtts` | 句子清楚、慢语速、一次只问一个问题；语速 `-10`、音量 `8` | 不做医疗诊断，不替代照护或紧急救援 |

这 3 个场景都开启：

- `strictAudit=true`
- `enableLoudnessNorm=true`
- `enableConversationTruncate=true`
- `enableUserQueryExit=true`
- `enableWebSearch=false`
- `enableMusic=false`
- `memoryPolicy=local_compressed_memory_v1`

## 3. 建议场景分层

### 3.1 稳定业务场景

这层优先使用 O2.0。场景目标明确，提示词短，安全策略容易管理。

| 场景 | 推荐音色 | 推荐设置 | 场景提示词方向 |
| --- | --- | --- | --- |
| 日常问候 | Vivi 2.0 / 云舟 2.0 | 慢语速、响度均衡、不开联网 | 问候近况、承接轻提醒、异常表达提示联系人 |
| 口语陪练 | 小何 2.0 / 小天 2.0 | 语速略慢、不开唱歌、可按主题开启联网 | 鼓励多说，纠错少而具体，给下一轮练习建议 |
| 工作复盘 | 云舟 2.0 | 默认语速或 `-2`，可开启联网摘要 | 梳理目标、阻塞、下一步，不替用户做重大决策 |
| 睡前陪伴 | Vivi 2.0 | 语速 `-4` 到 `-10`，不开联网 | 倾听、复述、轻计划，明确不是心理咨询 |
| 内容播报 / 短讲解 | 云舟 2.0 / 小天 2.0 | 默认语速、响度均衡，可按内容开启联网 | 结构化解释，不模拟真人主播身份 |

### 3.2 角色体验场景

这层使用 SC2.0。每个音色需要绑定角色卡，适合做沉浸式体验、剧情试玩、虚拟角色 Demo。

| 场景 | 推荐音色 | 设置重点 | 风险边界 |
| --- | --- | --- | --- |
| 恋爱风格角色试玩 | 傲娇女友、醋精男友、磁性男嗓、病娇姐姐、病娇白莲 | 保留角色语气和动作描写，限制每轮过长输出 | 不做未成年人恋爱陪伴；拒绝成人、控制、跟踪、胁迫内容 |
| 古风 / 剧情角色 | 温柔文雅、腹黑公子、傲娇公子 | `characterManifest` 保留时代感、口头禅和动作补充 | 不把剧情暴力变成现实建议 |
| 职场 / 成熟角色 | 成熟姐姐、成熟总裁、霸道少爷 | 强化成熟、可靠、目标拆解；减少暧昧表达 | 不做金融、法律、医疗结论 |
| 活力陪伴角色 | 风发少年、性感御姐 | 强化鼓励、运动、行动建议 | 健身和健康只做泛建议，不给诊断或治疗 |
| 强势反差角色 | 傲气凌人、傲慢少爷、妩媚御姐 | 用作剧情或短互动，不作为默认长期陪伴 | 控制欲、威胁、依赖表达需要安全策略兜底 |

### 3.3 运营配置场景

这层不是一个具体用户场景，而是管理员调参入口。

| 配置动作 | 适用对象 | 推荐规则 |
| --- | --- | --- |
| 切换模型模式 | 管理员 | O2.0 用于业务场景；SC2.0 用于角色体验 |
| 切换音色 | 管理员 | 只能选当前模式下的音色；SC2.0 切换音色时同步切换 `characterManifest` |
| 编辑开场白 | 管理员 | 用一句话进入场景，不写功能说明 |
| 编辑提示词 | 管理员 | O2.0 改 `systemRole` / `speakingStyle`；SC2.0 改 `characterManifest` |
| 调整高级设置 | 管理员 | 优先调整语速、音量、联网；谨慎开启唱歌和 web_agent |

## 4. 音色资产清单

### 4.1 前端当前可选音色

O2.0 当前可选 4 个音色：

| 音色 | speaker | 声音定位 | 推荐场景 |
| --- | --- | --- | --- |
| Vivi 2.0 | `zh_female_vv_jupiter_bigtts` | 平稳、柔和、治愈 | 晚间复盘、睡前陪伴、日常问候 |
| 小何 2.0 | `zh_female_xiaohe_jupiter_bigtts` | 甜美、有活力 | 口语陪练、轻学习、年轻用户陪伴 |
| 小天 2.0 | `zh_male_xiaotian_jupiter_bigtts` | 清澈、温润、有朝气 | 口语陪练、内容讲解、轻运动陪伴 |
| 云舟 2.0 | `zh_male_yunzhou_jupiter_bigtts` | 磁性、成熟、理性 | 适老问候、工作复盘、说明型助手 |

SC2.0 当前前端可选 16 个音色，并且都有角色提示词：

| 音色 | speaker | 角色定位 | 推荐场景 |
| --- | --- | --- | --- |
| 傲娇女友 | `saturn_zh_female_aojiaonvyou_tob` | 傲娇、甜美、口是心非 | 恋爱风格角色试玩 |
| 病娇姐姐 | `saturn_zh_female_bingjiaojiejie_tob` | 柔弱、深情、依赖 | 情绪张力角色试玩 |
| 成熟姐姐 | `saturn_zh_female_chengshujiejie_tob` | 知性、干练、可靠 | 职场陪伴、成熟角色 |
| 温柔文雅 | `saturn_zh_female_wenrouwenya_tob` | 古典、温婉、老师感 | 古风、文学、温柔陪伴 |
| 妩媚御姐 | `saturn_zh_female_wumeiyujie_tob` | 自信、时尚、妩媚 | 风格化角色展示 |
| 性感御姐 | `saturn_zh_female_xingganyujie_tob` | 健身、活力、直接 | 运动鼓励、活力角色 |
| 傲气凌人 | `saturn_zh_male_aiqilingren_tob` | 高傲、强势、冷酷 | 强势剧情角色 |
| 傲娇公子 | `saturn_zh_male_aojiaogongzi_tob` | 清亮、傲娇、少年感 | 校园、古风轻角色 |
| 傲慢少爷 | `saturn_zh_male_aomanshaoye_tob` | 强势、自负、少爷感 | 反差角色试玩 |
| 霸道少爷 | `saturn_zh_male_badaoshaoye_tob` | 低沉、霸道、保护欲 | 剧情角色，不做现实建议 |
| 病娇白莲 | `saturn_zh_male_bingjiaobailian_tob` | 轻柔、偏执、依赖 | 情绪张力角色试玩 |
| 成熟总裁 | `saturn_zh_male_chengshuzongcai_tob` | 低沉、稳重、权威 | 成熟角色、目标拆解 |
| 磁性男嗓 | `saturn_zh_male_cixingnansang_tob` | 磁性、体贴、可靠 | 陪伴、朗读、成熟男友感角色 |
| 醋精男友 | `saturn_zh_male_cujingnanyou_tob` | 少年感、吃醋、撒娇 | 恋爱风格角色试玩 |
| 风发少年 | `saturn_zh_male_fengfashaonian_tob` | 开朗、运动、积极 | 运动陪伴、活力角色 |
| 腹黑公子 | `saturn_zh_male_fuheigongzi_tob` | 古风、谋略、清雅 | 古风剧情、策略型角色 |

### 4.2 后端已放行但前端未展示的音色

后端白名单还包含以下 SC2.0 speaker，但当前前端没有出现在 `voiceOptions` 中，也没有对应 `characterManifest`：

| speaker | 当前状态 | 使用前需要补齐 |
| --- | --- | --- |
| `saturn_zh_female_keainvsheng_tob` | 后端放行，前端未展示 | label、meta、previewText、avatarVideoUrl、characterManifest |
| `saturn_zh_female_nuanxinxuejie_tob` | 后端放行，前端未展示 | label、meta、previewText、avatarVideoUrl、characterManifest |
| `saturn_zh_female_tiexinnvyou_tob` | 后端放行，前端未展示 | label、meta、previewText、avatarVideoUrl、characterManifest |
| `saturn_zh_male_aojiaojingying_tob` | 后端放行，前端未展示 | label、meta、previewText、avatarVideoUrl、characterManifest |
| `saturn_zh_male_bujiqingnian_tob` | 后端放行，前端未展示 | label、meta、previewText、avatarVideoUrl、characterManifest |
| `en_male_tim_uranus_bigtts` | 后端放行，前端未展示 | 英文场景、label、meta、previewText、avatarVideoUrl、characterManifest |
| `en_female_dacey_uranus_bigtts` | 后端放行，前端未展示 | 英文场景、label、meta、previewText、avatarVideoUrl、characterManifest |
| `en_female_stokie_uranus_bigtts` | 后端放行，前端未展示 | 英文场景、label、meta、previewText、avatarVideoUrl、characterManifest |

这些音色不能直接写进产品场景文案里当作“已可选”，除非同步补齐前端展示和角色提示词。

## 5. 设置项说明

### 5.1 场景基础设置

| 设置项 | 当前字段 | 建议 |
| --- | --- | --- |
| 场景 ID | `scene.id` | 使用稳定英文 ID，作为记忆卡和报告归属键 |
| 场景标题 | `scene.title` | 用户能理解的短名称 |
| 适用用户 | `scene.audience` | 写清楚目标人群，不做泛化 |
| 能力要求 | `requiredCapabilities` | 只写当前场景真正依赖的能力 |
| 安全策略 | `safetyPolicy` | 陪伴、学习、适老分别绑定不同策略 |
| 记忆策略 | `memoryPolicy` | 当前只使用本地压缩记忆 |
| 报告策略 | `reportPolicy` | 和会后报告字段保持一致 |

### 5.2 模型和音色设置

| 设置项 | O2.0 | SC2.0 |
| --- | --- | --- |
| `mode` | `o2` | `sc2` |
| `model` | `1.2.1.1` | `2.2.0.0` |
| `speaker` | 4 个通用音色 | 16 个前端角色音色 |
| `botName` | 生效，最长 20 字 | 不作为主要入口 |
| `systemRole` | 生效，适合写任务和边界 | 不作为主要入口 |
| `speakingStyle` | 生效，适合写语气和互动规则 | 不作为主要入口 |
| `characterManifest` | 不作为主要入口 | 生效，适合完整角色卡 |

### 5.3 高级设置

| 设置项 | 默认值 | 规则 |
| --- | --- | --- |
| `strictAudit` | `true` | 默认保持开启 |
| `enableWebSearch` | `false` | 只有需要事实查询、新闻、资料检索时开启 |
| `webSearchType` | `web` | `web_agent` 必须配置 `webSearchBotId` |
| `webSearchResultCount` | `5` | 后端允许 1 到 10 |
| `enableMusic` | `false` | 只支持 O2.0，SC2.0 会自动关闭 |
| `enableLoudnessNorm` | `true` | 默认开启，适合多数语音场景 |
| `enableConversationTruncate` | `true` | 默认开启，避免上下文过长 |
| `enableUserQueryExit` | `true` | 默认开启，用于识别退出意图 |
| `speechRate` | `0` | 后端允许 `-50` 到 `100`；适老、睡前建议降低 |
| `loudnessRate` | `0` | 后端允许 `-50` 到 `100`；适老场景可略提高 |
| `explicitDialect` | 空 | 当前类型支持东北、四川、陕西，但前端参数面板尚未暴露 |

## 6. 新增场景模板建议

新增场景时先按下面结构写，不要只选一个音色就上线。

| 字段 | 示例 | 检查点 |
| --- | --- | --- |
| `id` | `workday_wrapup` | 不和已有场景冲突 |
| `title` | 工作日收尾 | 用户一眼能懂 |
| `audience` | 职场用户 / 项目成员 | 目标人群具体 |
| `mode` | `o2` | 业务任务默认选 O2.0 |
| `speaker` | `zh_male_yunzhou_jupiter_bigtts` | 和人群、语气匹配 |
| `systemRole` | 帮用户复盘今天的目标、阻塞和下一步 | 明确任务和禁止事项 |
| `speakingStyle` | 简洁、理性、少追问，每轮最多一个问题 | 可听、可执行 |
| `openingLine` | 今天收尾前，我们先看三个问题：完成了什么、卡在哪里、下一步是什么？ | 一句话进入任务 |
| `safetyPolicy` | `daily_companion_safe_v1` 或新增策略 | 高风险话题有兜底 |
| `reportPolicy` | 新增或复用报告策略 | 会后报告知道看什么 |

SC2.0 新增角色时必须同时补：

- `voiceOptions`：前端可选音色、试听文案和视频。
- `sc2CharacterManifests`：完整角色卡。
- 后端白名单：确认 `speaker` 已在对应语言服务里放行。
- 安全策略：尤其是恋爱、病娇、强势、威胁、依赖类角色。

## 7. 当前优先级

1. 先把 O2.0 的业务场景做稳：晚间复盘、口语陪练、适老问候、工作复盘、内容播报。
2. 再把 SC2.0 当角色资产库管理：每个角色有角色卡、可用场景、风险边界和试听。
3. 最后再考虑英文音色和未展示音色：先补前端展示和角色提示词，再进入场景配置。

