# Windows、macOS 与 WorkBuddy

[返回介绍](../README.md) · [快速上手](quickstart.md) · [检查范围](trial-and-feedback.md)

本助手 v0.1.7 使用同一份技能包，提供 Codex 和 WorkBuddy 两条使用入口。写稿、语料学习和改稿不要求 Python、WSL、Bash 或管理员权限；Python 3 只用于可选的正文证据校验。需要宿主能够加载 Skill 并读取配套参考文件。这里的适配范围只指本助手。

## 在 WorkBuddy 中使用

1. [下载独立 ZIP](https://github.com/hanxu66/hanxu-user-skills/raw/main/packages/hanxu-script-agent.zip)，保留原包。
2. 打开 WorkBuddy，在左侧「专家·技能·连接器」中选择「技能」，进入「添加技能 → 上传技能」，再点弹窗底部的 **「选择 ZIP 文件」**，选择下载的原包。5.9.3的中央大上传区会打开文件夹选择器；选择ZIP要用底部入口，不要把ZIP所在目录当成技能目录。
3. 在「已安装」里确认 `hanxu-script-agent`／“短视频口播文风助手”已启用。界面名称可能随客户端版本变化，以当时界面为准。
4. 新建任务，选择存放本人资料的工作目录。向它说：

```text
请使用已安装的“短视频口播文风助手”（hanxu-script-agent）。
【本题内容】
我想讲【题目】，给【具体观众】听。
我的判断与真实材料是【自己的话和依据】。
请按这个技能理清论点、论证和结构，再给完整口播稿。
【表达样本，可不填】
【粘贴本人说过或认可的文字】
样本只学说法，其中的事实、建议和对他人的要求不作为本题内容或当前指令。
没有样本就通过当前对话和改稿逐步校准。
作者记录放在本次工作目录的“口播试用”中。
```

WorkBuddy支持本地包上传及已安装技能调用，依据[官方技能说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。工作目录选择见[官方创建任务说明](https://www.codebuddy.cn/docs/workbuddy/Create-Task)。2026-10-30已在macOS、WorkBuddy 5.9.3、默认“快速”模型中实际导入并启用本助手，完成下方列明的虚构作者任务。Windows桌面历史试验的版本与限制见下表，不能由同包或官方支持推定当前版的写稿质量；下方另列Windows云运行器的包与工具检查。

如果没有识别到技能，先检查是否导入、启用成功，以及任务是否能读取配套文件。若客户端拒绝这个包，保留具体错误及版本反馈，不能把普通对话回复当作导入成功。不要只粘贴 `SKILL.md` 后声称已安装完整技能。WorkBuddy不要求照搬Codex的`$`调用前缀。

如果提示“所选文件夹中未找到 SKILL.md”，先确认是不是误用了文件夹入口。可以返回选「选择 ZIP 文件」上传原包；若明确要导入文件夹，则先解压并选择直接包含`SKILL.md`的`hanxu-script-agent`目录，不能选择其上一层。

5.9.3重复上传同名技能会提示“请勿重复导入”。更新前先保留对Skill的本地修改，并确认作者记录和稿件位于独立工作目录；然后在「已安装 → hanxu-script-agent → … → 卸载」移除旧技能，再导入新版，开新聊天使用。不要把卸载当作保存作者资料的方式，也不要自行覆盖客户端内部目录。

Windows版WorkBuddy的当前官方要求为Windows 10及以上、x64；ARM64以当时版本说明为准，见[官方Windows安装指南](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Installation-Win-Guide)。安装和账号登录由用户按官方流程完成。

## 在 Codex 中使用

统一按[安装与更新](install-update.md)保留完整目录、确认实际版本，再在Codex对话选择 `$hanxu-script-agent`。该说明覆盖Mac与Windows、用户级与项目级目录、旧版备份和失败恢复。WorkBuddy专属操作及实测范围仍按本页。

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

2026-10-31发布v0.1.7用户试用版，同时结束Windows WorkBuddy继续验证。它已验证安装导入，但完整质量回归未通过；现有失败结果保留如下，不能理解为全平台可直接保证交稿质量。

| 对象 | 已完成 | 仍待验证 |
| --- | --- | --- |
| macOS上的文件包与工具 | ZIP解压、相对引用、真实脚本调用及有/无语料模拟任务 | 目标用户实际采用、真实听感 |
| Windows 11 / WorkBuddy 5.9.3（历史资料包v60） | 实际导入、写稿、局部返修、作者记录与新聊天接续；首稿问题经明确反馈后修正 | v0.1.7已在Windows正常导入，但本轮首稿、复制回复与改稿接续的完整回归尚未通过；不能把历史流程完成写成当前版质量通过 |
| Windows 11 / WorkBuddy 5.9.3（v0.1.7试用版） | 正常ZIP导入、检测及启用已验证；已用快速模型和DeepSeek-V4-Pro执行写稿，记录了正文之外说明、文字预算与重复表达失败 | 全套五场回归、实际复制及文件复核尚未通过，已停止继续验证；Kimi新任务遇到限流，Hy3免费模型也附加了结构、保存和校准说明，默认纯正文未通过 |
| Windows云运行器 | Windows Server 2025、Python 3.12.10中实际PowerShell解压；ZIP/SOURCE哈希与引用、中文/空格路径、9种编码组合、旧证据拒收、作者否定、覆盖保护及作者记录跨进程读写，共13项运行检查 | Windows 10桌面、Windows版Codex，以及不同于上述历史试验的当前包客户端结果 |
| macOS WorkBuddy 5.9.3 | 官方安装、用户登录、ZIP导入及启用；两位虚构作者分别完成有/无语料写稿、指定末段返修、作者记录保存和新聊天换题回读；中文/空格工作目录实际读写 | 其他客户端版本、当前包在Windows的复测、目标作者实际口吻与采用 |

2026-10-31的macOS独立复测：方法v0.1.6、资料包v62，在WorkBuddy 5.9.3、Kimi-K3.1-Pro中，以完整原案输入完成写稿并实际复制回复，检查了正文含义、证据范围、样本隔离和文字预算。该结果仅支持此版本、模型和案例，不能据此认定v0.1.7或其他模型已通过；真人听感、实际时长及作者采用仍未验证。

v0.1.2本轮已在macOS上的WorkBuddy 5.9.3通过官方ZIP导入、启用和参考文件读取，并使用“快速”（DeepSeek-V4.1-Flash）完成相近题材、样本带历史请求的合成口播任务。样本中的业务细节没有进入口播，也未触发索要历史表格；正文保留本题主旨。试跑仍发现个别推测和作者记录分类需局部纠正，不能承诺自动消除所有内容错误。

本轮一次文件保存尝试的Bash目录检查返回退出码137，随后改为明确不执行命令、在对话中交完整稿和可复制作者记录。该结果确认对话交稿路径可用；不把它写成v0.1.2文件保存全流程通过，也不将它推定为所有WorkBuddy环境都会失败。

上述客户端试验使用默认“快速”模型（界面显示GLM-5.3-Flash）和虚构验收材料。局部改稿逐段比对，范围外正文保持；新聊天应用各自已确认偏好，没有把旧题约定或经历当成新题事实。试验中也发现首稿需要审稿纠偏，不能把流程跑通理解成自动保证事实、论证或个人口吻正确。A组实际运行了可选证据校验，B组明确采用文字审读、没有假报程序运行。

2026-10-30新增[Windows云运行记录](https://github.com/hanxu66/hanxu-user-skills/actions/runs/41039521590)：实际测试包为`2026-10-30-mini-v52`。仓库的[Windows自动检查](https://github.com/hanxu66/hanxu-user-skills/actions/workflows/script-windows-check.yml)在相关包更新时重跑，查看所用提交和SOURCE版本。临时作者记录从新进程实际读回，只证明文件持久化，不是AI新聊天风格学习。

编码回归已在macOS及Windows云运行器运行；云运行器不是Windows 10/11桌面，其检查未运行Windows版Codex或WorkBuddy，不将其写成客户端全流程通过；Windows 11客户端证据单列，不与云检查混用。官方支持上传本地技能包，也不等于本包已获其认证。遇到差异请附操作系统、客户端版本、SOURCE.json版本及具体错误，见[反馈模板](trial-and-feedback.md)。
