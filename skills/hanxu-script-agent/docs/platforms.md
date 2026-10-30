# Windows、macOS 与 WorkBuddy

[返回介绍](../README.md) · [快速上手](quickstart.md) · [检查范围](trial-and-feedback.md)

本助手 v0.1.1 使用同一份技能包，提供 Codex 和 WorkBuddy 两条使用入口。写稿、语料学习和改稿不要求 Python、WSL、Bash 或管理员权限；Python 3 只用于可选的正文证据校验。需要宿主能够加载 Skill 并读取配套参考文件。这里的适配范围只指本助手。

## 在 WorkBuddy 中使用

1. [下载独立 ZIP](https://github.com/hanxu66/hanxu-user-skills/raw/main/packages/hanxu-script-agent.zip)，保留原包。
2. 打开 WorkBuddy，在左侧「专家·技能·连接器」中选择「技能」，进入「添加技能 → 上传技能」，选择这个本地包。
3. 在「已安装」里确认 `hanxu-script-agent`／“短视频口播文风助手”已启用。界面名称可能随客户端版本变化，以当时界面为准。
4. 新建任务，选择存放本人资料的工作目录。向它说：

```text
请使用已安装的“短视频口播文风助手”（hanxu-script-agent）。
我想讲【题目】，给【具体观众】听。
我的判断与真实材料是【自己的话和依据】。
请按这个技能理清论点、论证和结构，再给完整口播稿。
有本人语料就学习，没有就通过对话和改稿逐步校准。
作者记录放在本次工作目录的“口播试用”中。
```

WorkBuddy支持本地包上传及已安装技能调用，依据[官方技能说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。工作目录选择见[官方创建任务说明](https://www.codebuddy.cn/docs/workbuddy/Create-Task)。上述流程按官方入口适配，尚未在真实WorkBuddy客户端验证本包的导入和完整任务。

如果没有识别到技能，先检查是否导入、启用成功，以及任务是否能读取配套文件。若客户端拒绝这个包，保留具体错误及版本反馈，不能把普通对话回复当作导入成功。不要只粘贴 `SKILL.md` 后声称已安装完整技能。WorkBuddy不要求照搬Codex的`$`调用前缀。

Windows版WorkBuddy的当前官方要求为Windows 10及以上、x64；ARM64以当时版本说明为准，见[官方Windows安装指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide)。安装和账号登录由用户按官方流程完成。

## 在 Codex 中使用

解压后安装完整的 `hanxu-script-agent` 文件夹，可先让Codex检查并安装。用户级位置为 `~/.agents/skills/hanxu-script-agent/`，项目级为 `项目目录/.agents/skills/hanxu-script-agent/`。Windows的`~`指用户主目录，通常对应`%USERPROFILE%`，可在文件资源管理器中打开；不用在PowerShell里照抄Bash命令。

在Codex对话里用 `$hanxu-script-agent` 选择技能，再提供题目和材料。具体安装及更新步骤见[快速上手](quickstart.md)。这不是要求在系统终端执行的命令。

## 文件、作者记录与换设备

- 默认保存 `口播试用/作者表达记录.md`，一个作者一个目录；不放在Skill安装目录中。
- 中文、空格路径可用。新建文件统一UTF-8，名称避开Windows保留字符及设备名。引用尽量使用当前任务目录下的相对路径。
- 换机器或换工具时，带上作者表达记录和需要的本地材料，并在新任务中指定位置。安装同一Skill不等于自动同步个人资料。
- 当前宿主没有文件读写能力时，仍可在对话中拿到完整稿和可复制作者记录；下次需重新提供。没有音视频读取能力时提供文字转写。

## 可选的Python证据校验

让AI先检查已有Python 3，使用当前环境可用的入口。Windows常见`py -3`或`python`，macOS常见`python3`。脚本只使用Python标准库，没有额外模型API、网络或第三方库依赖；无需为写稿先安装Python。

Windows PowerShell示例，所有路径须替换为本机实际位置：

```powershell
py -3 "C:/实际安装位置/hanxu-script-agent/scripts/check_short_video_script_review.py" --review "C:/口播试用/正文复核.json" --output "C:/口播试用/final-body-check.json"
```

macOS示例，同样替换实际位置：

```sh
python3 "/实际安装位置/hanxu-script-agent/scripts/check_short_video_script_review.py" --review "/实际任务目录/正文复核.json" --output "/实际任务目录/final-body-check.json"
```

复核记录格式见[正文复核记录与校验](../references/正文复核记录与校验.md)。JSON路径用`/`或转义反斜杠；正文、记录及反馈兼容UTF-8、UTF-8 BOM、带BOM的UTF-16和CRLF。报告写为UTF-8；终端JSON中的`\u`转义是有效JSON，不是正文乱码。修改BOM、编码或换行后，原文件哈希变化，须重新生成证据及报告。

程序检查引用、逐段覆盖和版本一致性，语义判断仍须实际审读。没有Python时可以完整写稿和文字审读，但应说明程序未运行，不能伪造程序结果。

## 当前验证状态

| 对象 | 已完成 | 仍待验证 |
| --- | --- | --- |
| macOS上的文件包与工具 | ZIP解压、相对引用、真实脚本调用及有/无语料模拟任务 | 目标用户实际采用、真实听感 |
| Windows兼容 | 中文及空格目录、CRLF、BOM、UTF-16、非UTF-8控制台回归 | Windows实机安装与完整任务 |
| WorkBuddy入口 | 对照官方本地包上传流程补齐说明；执行方法不依赖Codex专有工具 | 真实客户端导入、启用、文件读写与改稿接续 |

编码回归在macOS上运行，不冒充Windows实测。官方支持上传本地技能包，也不等于本包已获其认证。遇到差异请附操作系统、客户端版本、SOURCE.json版本及具体错误，见[反馈模板](trial-and-feedback.md)。
