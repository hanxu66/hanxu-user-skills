# 韩叙方法：七项用户 Skill 包

版本：2026-10-10-mini-v1。由现有方法文件适配导出，原方法文件仍是维护来源。

## 下载与调用

| 能力 | 包 | 调用 |
|---|---|---|
| 短视频脚本 | [hanxu-script-agent.zip](hanxu-script-agent.zip) | `$hanxu-script-agent` |
| 公众号成稿 | [hanxu-public-account-drafting.zip](hanxu-public-account-drafting.zip) | `$hanxu-public-account-drafting` |
| 小红书视觉制作 | [hanxu-xiaohongshu-visual.zip](hanxu-xiaohongshu-visual.zip) | `$hanxu-xiaohongshu-visual` |
| 外部对标研究 | [hanxu-external-benchmark-research.zip](hanxu-external-benchmark-research.zip) | `$hanxu-external-benchmark-research` |
| 公众号标题生成 | [hanxu-public-account-title.zip](hanxu-public-account-title.zip) | `$hanxu-public-account-title` |
| 公众号系列双图 | [hanxu-public-account-series-visual.zip](hanxu-public-account-series-visual.zip) | `$hanxu-public-account-series-visual` |
| 口播剪辑 | [hanxu-talking-head-edit.zip](hanxu-talking-head-edit.zip) | `$hanxu-talking-head-edit` |

[下载七项合集](hanxu-seven-user-skills-mini-v1.zip) · [文件校验值](SHA256SUMS.txt)

## 安装

解压单项包，将包含 SKILL.md 的目录放入用户 ~/.agents/skills/，或项目根目录 .agents/skills/。
已有同名目录时先备份并比较。用 $技能名直接调用，或用对应任务描述触发。卸载时移除安装目录，保留用户材料和输出。

两项视觉制作需要 Node.js、Sharp 和中文字体；在对应目录运行 npm install。公众号双图另需 Python 3。
研究检查脚本需要 Python 3。口播剪辑需要实际可用的 ChatCut、剪映及素材，安装 Skill 不包含剪辑引擎。

使用者提供自己的观点、证据、素材、授权、品牌和输出目录；包不依赖作者的私人知识库或客户资料。每个包内 SOURCE.json 记录来源和版本。

## 已验证范围

七包结构、链接、文件校验及 ZIP 完整性已检查。
公众号封面/头图、小红书文字图文在 Mini 的新用户目录实际渲染并检查；研究格式检查正例和反例按预期运行。

验证使用 Mini 已有依赖环境，没有在全新机器安装验证。真实口播剪辑、小红书模型图全流程、独立客户效果和平台发布未验证。

## 许可与费用

尚未设定开放源代码许可、商业授权或价格。Codex、平台及剪辑工具的使用费用按使用者实际服务计费。

安装参考：[Codex 官方说明](https://learn.chatgpt.com/docs/build-skills)。
