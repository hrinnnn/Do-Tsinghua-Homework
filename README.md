# Codex Personal Skills

个人 Codex 技能库，用来在多台电脑复用课程作业写作流程和 Markdown 报告排版。采用 MIT 开源许可证。

| Skill | 用途 |
| --- | --- |
| [do-tsinghua-homework](skills/do-tsinghua-homework/SKILL.md) | 完成课程作业、实现和真实实验，先交付可编辑的 Markdown，修改确认后再转 PDF |
| [markdown-report-pdf](skills/markdown-report-pdf/SKILL.md) | 将最新 Markdown 导出为 PDF，嵌入中文字体、保留图片比例并检查分页 |
| [writer-tsinghua-report](skills/writer-tsinghua-report/SKILL.md) | 旧名称的兼容入口，沿用 Do Tsinghua Homework 的完整流程 |

这是个人写作偏好，不是清华大学的统一报告格式。作业内容、实现范围和提交要求以当前题目为准。

## 在另一台电脑安装

需要 Python 3.9+。有 Git 时执行：

```sh
git clone https://github.com/hrinnnn/codex-personal-skills.git
cd codex-personal-skills
python3 scripts/install.py
```

Windows 将 python3 换为 py -3。也可以使用 GitHub 页面上的 Code → Download ZIP，解压后在目录内运行同一个安装命令。

安装脚本默认复制到 CODEX_HOME/skills；未设置 CODEX_HOME 时使用 ~/.codex/skills。可以通过 --dest 指定技能目录，例如：

```sh
python3 scripts/install.py --dest ~/.agents/skills
```

已有内容相同的 skill 会跳过；已有不同内容时会停止，不自动覆盖。明确需要更新时使用 --replace，旧目录会保存到目标技能目录旁的 skill-backups 文件夹。

每台电脑安装一次即可使用，安装后在下一轮 Codex 对话中调用。仓库更新后，在各电脑运行：

```sh
git pull --ff-only
python3 scripts/install.py --replace
```

本仓库提供按需同步方式，更新需要在各电脑执行。安装仅复制技能文件，导出依赖另行配置。

也可以在 Codex 中直接请求：

> 安装 https://github.com/hrinnnn/codex-personal-skills 中 skills 目录下的三个技能。

## 使用

```text
使用 $do-tsinghua-homework 帮我完成这个作业，先给 Markdown 报告。
```

默认流程：完成题目所需工作 → 保存并交付 .md → 用户修改确认 → 按最新 .md 导出 PDF。第一版不会自动跳过确认环节。用户明确请求把现有 Markdown 转成 PDF 时，可以直接进入导出阶段。

```text
使用 $markdown-report-pdf 将我最新保存的 Report.md 转成 PDF。
```

## PDF 导出环境

可以使用 Codex 自带的文档运行环境。在普通 Python 环境中，建议使用独立虚拟环境安装导出依赖：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python skills/markdown-report-pdf/scripts/export_pdf.py Report.md Report.pdf --render-dir tmp/preview
```

Windows 对应命令：

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Mac 默认使用系统宋体、黑体和 Times New Roman，字体嵌入 PDF。仓库不分发系统字体。

Windows 可以显式指定本机字体：

```powershell
.venv\Scripts\python skills/markdown-report-pdf/scripts/export_pdf.py Report.md Report.pdf --chinese-font "C:/Windows/Fonts/simsun.ttc" --chinese-index 0 --heading-font "C:/Windows/Fonts/simhei.ttf" --heading-index 0 --latin-font "C:/Windows/Fonts/times.ttf" --latin-bold "C:/Windows/Fonts/timesbd.ttf" --render-dir tmp/preview
```

以上字体需在本机实际存在。Linux 或其他字体配置的电脑，使用 --chinese-font、--heading-font、--latin-font、--latin-bold 指定可用的字体；TTC 的子字体通过 --chinese-index、--heading-index 选择。需要粗体时可另加 --chinese-bold。选择含所需中文字形的 TrueType 字体，具体参数见脚本 --help。字体不存在或缺字时会明确报错。

图片路径相对于 Markdown 文件解析，保持原图比例。支持常用标题、段落、列表、表格、代码块和本地图片；复杂公式、多级列表等超出脚本支持范围时，由 agent 根据文档实际内容选择其他转换方式。

## 维护

新增 skill 放在 `skills/<skill-name>/`，至少包含 SKILL.md；所需脚本、参考材料和界面元数据放入该技能目录。发布前检查相对链接、脚本和公共内容。

[官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)
