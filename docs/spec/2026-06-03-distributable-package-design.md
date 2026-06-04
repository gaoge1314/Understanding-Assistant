# Understanding-Assistant 整合包设计文档

**日期：** 2026-06-03
**状态：** 待实施

## 1. 背景

项目经过三次迭代开发，已具备完整的卡包生成（understanding-memory Skill）、学习应用生成（learning-app Agent + generate_app.py）、HTML 交互学习三大模块。当前代码分散在 `.agents/skills/` 和 `scripts/` 中，用户需要一份**可直接分发到 GitHub 的整合包**，下载后放入笔记即可使用。

## 2. 目标

创建一个 GitHub 仓库整合包，达到：
- **下载即用**——用户 clone 后按文档指引即可完成初始化
- **示例驱动**——带一个可直接打开的示例 HTML 学习应用，让用户 0 门槛看到效果
- **文档完整**——README 手把手引导，覆盖从"放入笔记"到"生成卡牌"的全流程
- **独立分发**——脱离当前开发目录结构，clean 打包

## 3. 目录结构

```
jiyikapian/
│
├── .agents/skills/
│   ├── understanding-memory/      # 主 Skill：卡包生成编排
│   ├── learning-app/              # 交互式学习应用生成
│   │   ├── SKILL.md               # Agent prompt
│   │   ├── templates/
│   │   │   ├── index.html         # 三栏布局模板（数据已内嵌，支持 file://）
│   │   │   ├── style.css          # 完整样式
│   │   │   └── app.js             # 交互逻辑（折叠面板/拖拽/翻转/记忆曲线）
│   │   └── scripts/
│   │       └── generate_app.py    # JSON → HTML 应用（内嵌数据，免 CORS）
│   ├── transcript-processor/      # 子 Skill：预处理录音稿/笔记
│   ├── knowledge-extractor/       # 子 Skill：提取知识点标题
│   ├── card-generator/            # 子 Skill：生成单张卡片
│   └── memory-techniques/         # 子 Skill：生成记忆技巧
│
├── scripts/
│   ├── __init__.py
│   ├── models.py                  # 数据模型（含 to_dict/from_dict）
│   ├── validator.py               # 卡包校验器
│   ├── card_generator.py          # Markdown/JSON 输出 + 知识图谱
│   ├── knowledge_store.py         # 持久化读写 + 版本管理
│   ├── fill_answers.py            # 补充答案 + 生成记忆技巧
│   ├── requirements.txt           # Python 依赖
│   └── setup.ps1                  # 初始化脚本（创建目录 + 装依赖）
│
├── input/                         # 【用户入口】放置学习资料
│   ├── 参考资料/
│   └── 大纲/
│
├── output/
│   ├── json/                      # 卡包 JSON（自动生成）
│   ├── markdown/                  # 卡包 Markdown（自动生成）
│   ├── knowledge/                 # 知识点清单（自动生成）
│   ├── processed/                 # 预处理产物（自动生成）
│   └── card-app/
│       ├── 灾害学/                # 示例：灾害学学习应用
│       │   ├── index.html
│       │   ├── style.css
│       │   └── app.js
│       └── 你的科目名/           # 你生成的会放在这里
│
├── docs/
│   ├── README.md                 # 使用说明（本文件）
│   └── spec/                     # 设计文档（开发者参考）
│
├── CONTEXT.md                     # 项目术语表
├── .gitignore
└── LICENSE
```

## 4. 关键技术决策

### 4.1 data.json 内嵌到 HTML 中

位置：`templates/index.html` 中 `<script>window.__CARD_DATA__ = __DATA__;</script>`

`generate_app.py` 在生成时替换 `__DATA__` 为 JSON 数据。用户双击 `index.html` 即可在浏览器直接打开，不受 `file://` 协议下 `fetch()` 的 CORS 限制。

### 4.2 模板化架构

- HTML/CSS/JS 模板存放在 `templates/` 目录，`generate_app.py` 每次拷贝并注入数据
- 所有交互逻辑在 app.js 中一次编写，所有科目共用
- 升级模板只需更新 templates/，重新生成即可

### 4.3 纯前端零依赖

- HTML 应用不需要 Node.js、npm、Webpack 等
- 数据存 localStorage，重启浏览器不丢失
- 记忆曲线、翻转卡、拖拽排序全部原生 JS 实现

### 4.4 依托 Trae IDE

- 卡包生成依赖 Trae IDE 中的 AI Skills 自动编排
- HTML 应用生成可通过 Trae 对话触发（AI 自动调用 generate_app.py）
- 也可手动运行 Python 脚本

## 5. 用户流程

### 首次使用

1. 从 GitHub 下载/克隆整合包
2. 双击 `output/card-app/灾害学/index.html` → 看到示例学习应用
3. 运行 `scripts/setup.ps1` → 初始化目录 + 安装依赖

### 生成自己的卡包

4. 把自己的笔记放入 `input/参考资料/`，如有大纲放入 `input/大纲/`
5. 在 Trae IDE 中打开本项目目录
6. 说：**"帮我生成知识卡包"**
7. AI 自动处理 → 输出到 `output/json/` 和 `output/markdown/`
8. 说：**"生成学习应用"** → AI 调用 generate_app.py
9. 双击 `output/card-app/你的科目/index.html` → 开始学习

### 增量更新

10. 放入新资料，说：**"更新卡包"** → AI 读取已有卡包，只处理新增知识点

## 6. 整合包 vs 当前开发目录

| 项目 | 当前开发目录 | 整合包 |
|:---|:---|:---|
| `.superpowers/` | 包含 | ❌ 移除 |
| `原始讨论/` | 包含 | ❌ 移除 |
| `.agents/skills/` | ✅ 保留 | ✅ 保留（核心引擎） |
| `scripts/` | ✅ 保留 | ✅ 保留 |
| `output/` | 有零散临时文件 | ✅ 清理，保留示例 |
| `docs/spec/` | ✅ 保留 | ✅ 保留 |
| `.gitignore` | 需补充 | ✅ `.agents/skills/` 不忽略 |

## 7. 示例数据

使用现有 `灾害学_v5.json`（24 张卡片），生成示例 HTML 应用放在 `output/card-app/灾害学/`。应用含：
- 24 张卡片，4 段折叠面板
- 19 张支持概念重组，24 张支持概念填空（44 道挖空题）
- 完整的三视图导航（学习/背诵/复习）
- 记忆曲线 + 每日字数推荐

## 8. 未包含（下次更新）

- 检测题 + 批改反馈（已在 backlog）
- 自我解释 + AI追问（已在 backlog）
- 语音朗读（Web Speech API）
- PWA 化（可安装到手机桌面）
- 移动端适配
