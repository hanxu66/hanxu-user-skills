# 韩叙的七个内容创作助手

把你的选题、观点、文章和视频素材，交给电脑上的 AI，按韩叙的方法完成具体内容任务。

**先选你要做的事，再下载对应助手。** 每个助手都可以单独安装，不需要安装整套经营系统。版本：2026-10-30-mini-v49。

| 助手名称 | 什么时候用 | 安装包 |
|---|---|---|
| [短视频口播文风助手（试用版）](skills/hanxu-script-agent/README.md) | 理清论点、论证和结构；有语料就学习，没有就通过对话和改稿校准口吻。 | [下载 ZIP](packages/hanxu-script-agent.zip) |
| [公众号写作助手](skills/hanxu-public-account-drafting/README.md) | 有观点和零散材料，想整理成一篇有逻辑的公众号文章。 | [下载 ZIP](packages/hanxu-public-account-drafting.zip) |
| [小红书图文制作助手](skills/hanxu-xiaohongshu-visual/README.md) | 逐页文案已经确定，需要制作封面和整套小红书图片。 | [下载 ZIP](packages/hanxu-xiaohongshu-visual.zip) |
| [短视频选题调研助手](skills/hanxu-external-benchmark-research/README.md) | 不知道下一条拍什么，想从指定账号和关键词中寻找选题启发。 | [下载 ZIP](packages/hanxu-external-benchmark-research.zip) |
| [公众号标题助手](skills/hanxu-public-account-title/README.md) | 文章已经写好，想得到清楚、吸引人且符合正文的标题。 | [下载 ZIP](packages/hanxu-public-account-title.zip) |
| [公众号封面制作助手](skills/hanxu-public-account-series-visual/README.md) | 文章标题已定，需要统一风格的公众号封面或正文头图。 | [下载 ZIP](packages/hanxu-public-account-series-visual.zip) |
| [口播视频剪辑助手](skills/hanxu-talking-head-edit/README.md) | 已经录好单人口播，想剪掉重复和停顿，整理字幕并完成包装。 | [下载 ZIP](packages/hanxu-talking-head-edit.zip) |

[一次下载七个助手](packages/hanxu-seven-user-skills-mini-v49.zip) · [文件校验值](packages/SHA256SUMS.txt)

## 短视频口播文风：用户试用版 v0.1

把你想讲的事整理成完整口播稿，一起处理论点、论证、结构和个人表达。有自己的口播、直播转写或亲手改稿就学习；没有历史语料，直接从当前对话与修改逐步校准。作者表达记录保存在本地，新题可以继续回读。

[看用户介绍](skills/hanxu-script-agent/README.md) · [下载独立包](packages/hanxu-script-agent.zip) · [快速上手](skills/hanxu-script-agent/docs/quickstart.md) · [完整虚构演示](skills/hanxu-script-agent/docs/examples.md) · [常见问题](skills/hanxu-script-agent/docs/faq.md)

沿用安装标识 `$hanxu-script-agent`。无需安装其他六个助手；目前完成的是模拟任务与包检查，个人适配仍待真实作者反馈。

## 第一次使用怎么做

1. 你需要一台能够运行 Codex 的电脑和可用账号。
2. 在上面的表格里选一个助手，下载 ZIP 并解压。
3. 把解压后的完整文件夹交给 Codex，说：“请帮我安装这个 Skill，检查所需依赖并告诉我如何调用。”
4. 安装完成后，照着该助手中文介绍中的例子，输入调用名并提供你自己的材料。

也可以手动把每个完整助手文件夹放到 `~/.agents/skills/`，或项目里的 `.agents/skills/`。安装后未出现时重启 Codex。不要只复制 SKILL.md，需要保留参考文件、脚本和模板。[OpenAI 官方安装说明](https://learn.chatgpt.com/docs/build-skills)。

例如使用短视频口播文风助手：

```text
$hanxu-script-agent
请根据我的题目和材料，理清论点、论证和结构，写成完整口播稿。有本人语料就学习，没有则通过对话和改稿逐步校准口吻。
```

## 使用前需要准备什么

写稿和标题助手需要你自己的观点、全文和真实材料；视觉制作需要 Node.js、Sharp 和中文字体，公众号封面另需 Python 3；口播剪辑需要实际可用的 ChatCut、剪映和原片。各助手页面写明具体条件。模型与工具费用按使用者自己的服务计费。

这些是可下载安装的 Skill 文件包，需要在你的 AI 工具中运行。GitHub 页面用于介绍和下载，没有在线运行按钮。

## 文件怎么组织

`skills/` 下是七个独立助手，每项都有中文 README、执行入口 SKILL.md 和必要配套文件。`agents/openai.yaml` 提供中文显示名和提示语。英文目录名是安装与调用标识。`packages/` 保存同版本单项 ZIP、合集和校验值。

## 已验证范围

包结构、文件链接、校验值及 ZIP 完整性已检查。此前公众号封面/头图、小红书文字图文在 Mini 的新用户目录实际渲染并检查；研究格式检查正例和反例按预期运行。

短视频口播文风试用版已做有语料、无历史语料两组隔离模拟任务，覆盖完整写稿、口吻返修及同作者新题接续。模拟输入不计为真实目标用户采用或效果验证。

验证使用 Mini 已有依赖环境，没有在全新机器安装验证。真实口播剪辑、小红书模型图全流程、独立客户效果和平台发布未验证。

## 来源与许可

由韩叙现有方法与必要依赖适配导出，原方法文件仍是维护来源。短视频口播文风试用版整合论点、论证、结构与个人表达校准；每个包的 SOURCE.json 记录来源和版本。使用者提供自己的素材、授权、品牌和输出目录。

可下载并安装使用；当前尚未设定开放源代码许可证、再分发或转售条款。
