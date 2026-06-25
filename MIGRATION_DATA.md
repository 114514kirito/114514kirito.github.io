# VitePress 迁移数据包

> 本文档包含从 VuePress 2 + vuepress-theme-hope 迁移到 VitePress 所需的全部信息。
> 目标：将当前博客完整迁移到 VitePress，保留所有功能和内容。

---

## 一、站点元数据

```ts
// .vitepress/config.ts — site-level config
export default {
  base: "/",
  lang: "zh-CN",
  title: "Yukino's Blog",
  description: "Yukino's Blog",
  head: [
    ["link", { rel: "icon", href: "/Image_1778813659900_438.jpg" }]
  ],
  // 当前 hostname: "https://114514kirito.github.io" — VitePress 无此配置项
  // 用于 SEO/Feed，需要在 VitePress 中通过 transformHead 或其他方式处理
}
```

---

## 二、主题配置

### 2.1 当前主题：vuepress-theme-hope (blog 模式)

```ts
// 原 vuepress-theme-hope 配置 — 需要映射到 VitePress 默认主题
{
  hostname: "https://114514kirito.github.io",
  contributors: false,  // VitePress 默认主题无此功能，无需迁移

  author: {
    name: "Yukino",
    url: "https://114514kirito.github.io",
  },

  logo: "/Image_1778813659900_438.jpg",
  favicon: "/Image_1778813659900_438.jpg",

  repo: "114514kirito/114514kirito.github.io",  // VitePress socialLinks
  repoDisplay: false,

  docsDir: "src",  // VitePress 默认为项目根目录，内容在 src/ 下

  footer: "The content on this site is all CC-BY-SA, or MIT/GPLv3+ dual license for code.",
  displayFooter: true,

  // blog 模式配置 — VitePress 无原生 blog，需要自己实现
  blog: {
    avatar: "/Image_1778813659900_438.jpg",
    description: "Yukino's Blog",
    medias: {
      Discord: "",
      Email: "",
      Facebook: "",
      GitHub: "",
      Instagram: "",
      Twitter: "",
      Youtube: "",
    },
  },
}
```

### 2.2 博客功能清单（需要重新实现）

原 `vuepress-theme-hope` blog 插件自动生成以下页面：
- **文章列表** — `/article/` — 按时间倒序排列所有文章
- **分类页** — `/category/` — 按 frontmatter `categories` 分组
- **标签页** — `/tag/` — 按 frontmatter `tags` 分组
- **时间线** — `/timeline/` — 按年份分组
- **星标页** — `/star/` — frontmatter `star: true` 的文章
- **Blog 首页** — `/` — hero + 文章列表

### 2.3 博客首页 frontmatter（src/README.md）

```yaml
---
home: true
title: Yukino's Blog
heroText: 𝓨𝓾𝓴𝓲𝓷𝓸'𝓼 𝓑𝓵𝓸𝓰
tagline: 𝓝𝓸𝓽𝓱𝓲𝓷𝓰 𝓲𝓼 𝓲𝓶𝓹𝓸𝓼𝓼𝓲𝓫𝓵𝓮
layout: Blog
bgImage: /1778815146056.jpeg
icon: house
heroFullScreen: true
---
```

### 2.4 VitePress 博客实现方案

**推荐方案**：使用 VitePress 的 `createContentLoader` + 动态路由实现博客功能。

关键实现点：
1. 用 `createContentLoader` 读取所有 `.md` 文件的 frontmatter
2. 用 `loadEnv` 或 `.vitepress/config.ts` 的 `srcDir` 配置内容目录
3. 用动态路由 `[page].md` 或 `[page].paths.js` 实现分页、分类、标签页
4. 博客首页用 `index.md` + `VPHome` 组件布局

---

## 三、侧边栏配置

完整映射如下。VitePress 侧边栏语法与原 VuePress 不同：

```ts
// .vitepress/config.ts — themeConfig.sidebar
// VitePress 格式：key 为路径前缀，值为侧边栏项数组
{
  "/lecture-notes-zh/": [
    {
      text: "MIT 6.1200J 笔记",
      collapsed: true,
      items: [
        { text: "第1讲：谓词、集合与证明", link: "/lecture-notes-zh/lec01" },
        { text: "第2讲：反证法与数学归纳法", link: "/lecture-notes-zh/lec02" },
        { text: "第3讲：分情况讨论与强归纳法", link: "/lecture-notes-zh/lec03" },
        { text: "第4讲：状态机", link: "/lecture-notes-zh/lec04" },
        { text: "第5讲：求和", link: "/lecture-notes-zh/lec05" },
        { text: "第6讲：渐进分析", link: "/lecture-notes-zh/lec06" },
        { text: "第7讲：递推关系", link: "/lecture-notes-zh/lec07" },
        { text: "第8讲：整除性", link: "/lecture-notes-zh/lec08" },
        { text: "第9讲：模运算", link: "/lecture-notes-zh/lec09" },
        { text: "第10讲：密码学", link: "/lecture-notes-zh/lec10" },
        { text: "第11讲：图与着色", link: "/lecture-notes-zh/lec11" },
        { text: "第12讲：匹配", link: "/lecture-notes-zh/lec12" },
        { text: "第13讲：连通性与树", link: "/lecture-notes-zh/lec13" },
        { text: "第14讲：有向图与DAG", link: "/lecture-notes-zh/lec14" },
        { text: "第15讲：关系与计数", link: "/lecture-notes-zh/lec15" },
        { text: "第16讲：计数", link: "/lecture-notes-zh/lec16" },
        { text: "第17讲：更多计数", link: "/lecture-notes-zh/lec17" },
        { text: "第18讲：概率导论", link: "/lecture-notes-zh/lec18" },
        { text: "第19讲：条件概率", link: "/lecture-notes-zh/lec19" },
        { text: "第20讲：独立性", link: "/lecture-notes-zh/lec20" },
        { text: "第21讲：随机变量", link: "/lecture-notes-zh/lec21" },
        { text: "第22讲：期望", link: "/lecture-notes-zh/lec22" },
        { text: "第24讲：大偏差", link: "/lecture-notes-zh/lec24" },
      ],
    },
  ],
  "/xv6-riscv-book/": [
    {
      text: "xv6-riscv-book",
      collapsed: true,
      items: [
        { text: "概述", link: "/xv6-riscv-book/" },
        { text: "Chapter 1", link: "/xv6-riscv-book/chapter1/" },
        { text: "Chapter 2", link: "/xv6-riscv-book/chapter2/" },
        { text: "Chapter 3", link: "/xv6-riscv-book/chapter3/" },
        { text: "Chapter 4", link: "/xv6-riscv-book/chapter4/" },
        { text: "Chapter 5", link: "/xv6-riscv-book/chapter5/" },
        { text: "Chapter 6", link: "/xv6-riscv-book/chapter6/" },
        { text: "Chapter 7", link: "/xv6-riscv-book/chapter7/" },
        { text: "Chapter 8", link: "/xv6-riscv-book/chapter8/" },
        { text: "Chapter 9", link: "/xv6-riscv-book/chapter9/" },
      ],
    },
  ],
  "/slides-zh/": [
    {
      text: "CS110 课件笔记",
      collapsed: true,
      items: [
        { text: "欢迎来到 CS110：计算机系统原理", link: "/slides-zh/01-summary/" },
        { text: "UNIX 文件系统 API 与系统调用", link: "/slides-zh/02-summary/" },
        { text: "异常控制流：中断、故障与陷阱", link: "/slides-zh/03-summary/" },
        { text: "多进程入门：fork 系统调用", link: "/slides-zh/04-summary/" },
        { text: "深入 fork：进程创建与管理", link: "/slides-zh/05-summary/" },
        { text: "信号处理与进程同步基础", link: "/slides-zh/06-summary/" },
        { text: "进程管理：waitpid 与退出状态", link: "/slides-zh/07-summary/" },
        { text: "多进程收尾：SIGCHLD 与信号同步", link: "/slides-zh/08-summary/" },
        { text: "虚拟内存与多线程入门", link: "/slides-zh/09-summary/" },
        { text: "多线程编程：竞争条件与修复", link: "/slides-zh/10-summary/" },
        { text: "线程与并发：哲学家就餐问题", link: "/slides-zh/11-summary/" },
        { text: "条件变量与信号量", link: "/slides-zh/12-summary/" },
        { text: "并发综合：冰淇淋店模拟", link: "/slides-zh/13-summary/" },
        { text: "网络编程入门：Socket 与时间服务器", link: "/slides-zh/14-summary/" },
        { text: "HTTP 协议与 Web 客户端实现", link: "/slides-zh/15-summary/" },
        { text: "Socket 底层实现与服务器架构", link: "/slides-zh/16-summary/" },
        { text: "MapReduce 编程模型", link: "/slides-zh/17-summary/" },
        { text: "MapReduce 实现与系统设计原则", link: "/slides-zh/18-summary/" },
        { text: "非阻塞 I/O", link: "/slides-zh/19-summary/" },
        { text: "课程总结与期末考试信息", link: "/slides-zh/20-summary/" },
      ],
    },
  ],
  "/translated_markdown/": [
    {
      text: "CS106L 课程笔记",
      collapsed: true,
      items: [
        { text: "第1章：欢迎来到 CS106L！", link: "/translated_markdown/01-Welcome/" },
        { text: "第2章：类型与结构体", link: "/translated_markdown/02-TypesAndStructs/" },
        { text: "第3章：初始化与引用", link: "/translated_markdown/03-InitializationAndReferences/" },
        { text: "第4章：流", link: "/translated_markdown/04-Streams/" },
        { text: "第5章：容器", link: "/translated_markdown/05-Containers/" },
        { text: "第6章：迭代器与指针", link: "/translated_markdown/06-Iterators/" },
        { text: "第7章：类与继承", link: "/translated_markdown/07-Classes/" },
        { text: "第8章：继承深入", link: "/translated_markdown/08-Inheritance/" },
        { text: "第9章：模板类", link: "/translated_markdown/09-TemplateClasses/" },
        { text: "第10章：模板函数", link: "/translated_markdown/10-TemplateFunctions/" },
        { text: "第11章：函数与Lambda", link: "/translated_markdown/11-FunctionsAndLambdas/" },
        { text: "第12章：运算符重载", link: "/translated_markdown/12-OperatorOverloading/" },
        { text: "第13章：特殊成员函数", link: "/translated_markdown/13-SpecialMemberFunctions/" },
        { text: "第14章：移动语义", link: "/translated_markdown/14-MoveSemantics/" },
        { text: "第15章：std::optional与类型安全", link: "/translated_markdown/15-OptionalAndTypeSafety/" },
        { text: "第16章：RAII与智能指针", link: "/translated_markdown/16-RAII-SmartPointers/" },
        { text: "第17章：单元测试", link: "/translated_markdown/17-UnitTesting/" },
      ],
    },
  ],
}
```

注意：`lecture-notes-zh` 的 sidebar 标题需要从各 `.md` 文件的 frontmatter `title` 中提取（上方已根据实际 title 填写）。如果 VitePress 自动使用页面 h1 > title frontmatter > 文件名，则只需写 `link`。

---

## 四、Markdown 扩展功能（需要迁移/替换）

| 功能 | 当前 | VitePress 方案 |
|---|---|---|
| `:::` 自定义容器（tip, warning, details, info, note, important, caution） | vuepress-theme-hope 内置 | VitePress 内置支持 `::: tip`、`::: warning`、`::: details`、`::: info`、`::: danger`、`::: raw`。**自定义标题容器（如 `::: tip 重难点解析`）也支持** |
| `==text==` 高亮标记 | @mdit/plugin-mark | 需要安装 `markdown-it-mark` 并在 `markdown.config` 中注册 |
| `~~text~~` 删除线 | GFM | VitePress GFM 内置 |
| `H~2~O` 下标 / `x^2^` 上标 | vuepress-theme-hope | 需要 `markdown-it-sub` + `markdown-it-sup` |
| `@include(file.md)` | @mdit/plugin-include | 需要 `markdown-it-include` |
| `::: code-tabs` 代码选项卡 | vuepress-theme-hope | VitePress 内置 `::: code-group`（语法不同，需要批量替换） |
| `$$...$$` 数学公式 (MathJax) | vuepress-theme-hope | 需要 `markdown-it-mathjax3` |
| `::: plantuml` | vuepress-theme-hope | 需要 `markdown-it-plantuml` |
| `::right` / `::center` 对齐 | @mdit/plugin-align | 需要 `markdown-it-align` 或自定义容器 |
| `<Badge type="tip">Recommended</Badge>` | vuepress-theme-hope components | 需要自己写 Vue 组件注册到 VitePress |
| `<VPCard>` | vuepress-theme-hope components | 需要自己实现 |
| `*Recommended*` → Badge（stylize） | vuepress-theme-hope stylize | VitePress 无等价功能，需要 `markdown-it` 插件或后处理 |
| Shiki 代码高亮 + 行号 + 行高亮 + 词高亮 | vuepress-theme-hope + @vuepress/plugin-shiki | VitePress 内置 Shiki，支持行高亮（`// [!code highlight]`），**语法不同** |

### 4.1 内容文件中实际使用的特殊语法统计

| 语法 | 使用位置 |
|---|---|
| `::: tip` / `::: tip 重难点解析` | lecture-notes-zh（全部23个文件）、slides-zh（大量）、translated_markdown（全部17个文件） |
| `::: warning` | slides-zh（警告框） |
| `<center-panel>` 自定义组件 | xv6-riscv-book（chapter1/2/6 的图表标题） |
| `<center-frame>` / `<center-frame-row>` | xv6-riscv-book |
| `<Badge>` | lecture-notes-zh（标记 "Recommended"） |
| `$$...$$` LaTeX 公式 | lecture-notes-zh（大量）、slides-zh |
| `*Recommended*` → 自动转 Badge | lecture-notes-zh |
| 自定义 color class（`.red`, `.green` 等 20+ 种颜色） | 通过 `<span class="red">` 或 `[text]{.red}` 使用 |

---

## 五、自定义 Vue 组件（3 个）

全部使用 Vue 3 `<script setup lang="ts">` 语法，直接可迁移到 VitePress。

### 组件列表

| 组件名 | 文件名 | 功能 | 使用位置 |
|---|---|---|---|
| `<center-frame>` | center-frame.vue | 居中容器，内部放 center-frame-row | xv6-riscv-book |
| `<center-frame-row>` | center-frame-row.vue | 弹性行布局，支持 `balanced` / `full` props | xv6-riscv-book |
| `<center-panel>` | center-panel.vue | 带标题面板，支持 `title`, `width`, `plain`, `natural` props，支持内联 code 和 link 渲染 | xv6-riscv-book |

### 源码路径

- `/home/kirito/blog/YukinoBlog/src/.vuepress/components/center-frame.vue`
- `/home/kirito/blog/YukinoBlog/src/.vuepress/components/center-frame-row.vue`
- `/home/kirito/blog/YukinoBlog/src/.vuepress/components/center-panel.vue`

### 注册方式（VuePress）

```ts
// client.ts
import { defineClientConfig } from "vuepress/client";
import center_frame from "./components/center-frame.vue";
import center_panel from "./components/center-panel.vue";
import center_frame_row from "./components/center-frame-row.vue";

export default defineClientConfig({
  enhance({ app }) {
    app.component("center-frame", center_frame);
    app.component("center-panel", center_panel);
    app.component("center-frame-row", center_frame_row);
  },
});
```

### VitePress 迁移方式

在 `.vitepress/theme/index.ts` 中：

```ts
import DefaultTheme from 'vitepress/theme'
import centerFrame from './components/center-frame.vue'
import centerPanel from './components/center-panel.vue'
import centerFrameRow from './components/center-frame-row.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('center-frame', centerFrame)
    app.component('center-panel', centerPanel)
    app.component('center-frame-row', centerFrameRow)
  }
}
```

### 组件源码（完整复制）

**center-frame.vue:**
```vue
<template>
  <div class="center-frame">
    <slot />
  </div>
</template>
```

**center-frame-row.vue:**
```vue
<script setup lang="ts">
defineProps<{
  balanced?: boolean;
  full?: boolean;
}>();
</script>

<template>
  <div
    class="center-frame-row"
    :class="{
      'center-frame-row--balanced': balanced,
      'center-frame-row--full': full,
    }"
  >
    <slot />
  </div>
</template>
```

**center-panel.vue:**（略长，见 `src/.vuepress/components/center-panel.vue` 完整源码）

---

## 六、自定义样式（index.scss）

路径：`/home/kirito/blog/YukinoBlog/src/.vuepress/styles/index.scss`
共 366 行，包含：

1. **基本样式** — 图片 margin、行内图片 max-width
2. **CJK 粗体增强** — `strong { font-weight: 650; text-shadow: 0 0 0.3px currentColor; }` + 暗色模式版本
3. **博客链接颜色** — `.posts-expand .post-title-link { color: #F5DEB3; }`
4. **center-frame 布局系统** — 170 行完整的 flex 布局 CSS（用于 xv6-riscv-book 的图表排版）
5. **Shiki 高亮词** — `pre.shiki .highlighted-word`
6. **标题颜色** — h1-h6 自定义颜色（#E8A635, #29E5A9, #F5DEB3, #B3EBF5, #BFD9C8, #D6C7C0）
7. **自定义链接颜色类** — `.redlink`, `.pinklink`, `.wheatlink`（含 :link/:visited/:hover/:active）
8. **20+ 种颜色类** — `.green`, `.yellow`, `.brown`, `.pink`, `.red`, `.orange`, `.purple`, `.blue`, `.ivory`, `.pearl`, `.beige`, `.cornsilk`, `.gainsboro`, `.light_grey`, `.silver`, `.dark_grey`, `.wheat`, `.burlywood`, `.tan`
9. **diff 颜色** — `.deletion`（红底）、`.addition`（绿底）

迁移到 VitePress：复制到 `.vitepress/theme/styles/custom.css` 并在 `theme/index.ts` 中 `import './styles/custom.css'`。

---

## 七、搜索引擎

### 当前配置

```ts
// vuepress-theme-hope plugins.search
search: {
  hotKeys: ["s", "/"],
  maxSuggestions: 6,
}
```

### VitePress 替代

VitePress 内置本地搜索，配置在 `themeConfig.search`：

```ts
// .vitepress/config.ts
themeConfig: {
  search: {
    provider: 'local',
    options: {
      // VitePress 默认 hotkeys 就是 / 和 Cmd+K
    }
  }
}
```

---

## 八、Feed 生成（RSS/Atom/JSON）

### 当前配置

```ts
feed: {
  rss: true,
  atom: true,
  json: true,
}
```

### VitePress 替代

VitePress 无内置 Feed 生成。需要：
1. 安装 `feed` npm 包
2. 在 `buildEnd` hook 中生成 `feed.xml`、`atom.xml`、`feed.json`
3. 添加到 `transformHead` 的 `<link>` 标签

---

## 九、SEO（Sitemap, Robots.txt）

### 当前

vuepress-theme-hope 内置 `@vuepress/plugin-seo` + `@vuepress/plugin-sitemap`。

### VitePress 替代

1. 安装 `sitemap` npm 包
2. 在 `buildEnd` hook 中生成 `sitemap.xml`
3. 在 `public/` 放置 `robots.txt`

---

## 十、Shiki 代码高亮 + 自定义语言

### 当前配置

```ts
highlighter: {
  type: "shiki",
  highlightLines: true,
  notationWordHighlight: true,
  lineNumbers: true,
  langs: [callgraph],  // 自定义语言
}
```

自定义语言文件：`src/.vuepress/shiki/callgraph.tmLanguage.json`

```json
{
  "name": "callgraph",
  "scopeName": "source.callgraph",
  "patterns": [
    {
      "name": "meta.callgraph.entry",
      "match": "\\[([^\\]:]+\\.[^\\]:]+):(\\d+)(?:-(\\d+))?\\]\\s+([A-Za-z_][A-Za-z0-9_]*)",
      "captures": {
        "1": { "name": "string.other.link" },
        "2": { "name": "constant.numeric.integer" },
        "3": { "name": "constant.numeric.integer" },
        "4": { "name": "entity.name.function" }
      }
    }
  ]
}
```

### VitePress 替代

```ts
// .vitepress/config.ts
import callgraph from './shiki/callgraph.tmLanguage.json'

export default {
  markdown: {
    lineNumbers: true,
    shiki: {
      langs: [callgraph as any],
    },
    // 行高亮语法不同：从 `{1,3-5}` 变为 `// [!code highlight]`
  },
}
```

---

## 十一、Markdown 内容详情

### 11.1 内容目录结构

```
src/
├── README.md                    # Blog 首页（hero + 文章列表）
├── lecture-notes-zh/            # MIT 6.1200J 离散数学笔记 (23 files)
│   ├── lec01.md ~ lec24.md      # 文件名即 slug
├── slides-zh/                   # CS110 课件笔记 (20 files)
│   ├── 01-summary/README.md ~ 20-summary/README.md
├── translated_markdown/         # CS106L C++ 课程笔记 (17 files)
│   ├── 01-Welcome/README.md ~ 17-UnitTesting/README.md
├── xv6-riscv-book/              # xv6 RISC-V 书籍 (10 files)
│   ├── README.md                # 概述
│   └── chapter1/README.md ~ chapter9/README.md
└── .vuepress/
    ├── config.ts
    ├── theme.ts
    ├── sidebar.ts
    ├── client.ts
    ├── components/
    │   ├── center-frame.vue
    │   ├── center-frame-row.vue
    │   └── center-panel.vue
    ├── styles/
    │   └── index.scss
    ├── shiki/
    │   └── callgraph.tmLanguage.json
    └── public/
        ├── 1778814915342.png
        ├── 1778815146056.jpeg
        └── Image_1778813659900_438.jpg
```

### 11.2 各内容目录的 frontmatter 示例

**lecture-notes-zh** 典型 frontmatter：
```yaml
---
title: "MIT 6.1200J: 第1讲 — 谓词、集合与证明"
date: 2026-05-15
categories: [MIT 6.1200J, 笔记]
tags: [离散数学, 谓词逻辑, 集合论, 证明]
mathjax: true
---
```

**slides-zh** 无 frontmatter（纯 Markdown 内容，无 YAML 头部）。

**translated_markdown** 典型 frontmatter：
```yaml
---
title: "第1章：欢迎来到 CS106L！"
---
或
```yaml
# 第5章：容器 (Containers)
> **授课教师**：Rachel Fernandez, Thomas Poimenidis
> **学期**：Stanford CS106L, Fall 2025
```

**xv6-riscv-book** 无 frontmatter。

---

## 十二、页面总数与分类统计

| 分类 | 页面数 |
|---|---|
| 内容页面 | 71 |
| 分类页（自动生成） | ~5 (MIT 6.1200J, 笔记, OS, RISC-V) |
| 标签页（自动生成） | ~99 (所有 tags) |
| 时间线 | 1 |
| 文章列表 | 按页 |
| 404 | 1 |
| **总计** | **179** |

---

## 十三、构建与部署

### 13.1 当前构建命令

```json
{
  "build:vite": "vuepress-vite build src",
  "dev": "vuepress-vite dev src",
}
```

### 13.2 迁移后的 VitePress 命令

```json
{
  "build": "vitepress build src",
  "dev": "vitepress dev src",
  "preview": "vitepress preview src"
}
```

### 13.3 CI/CD（GitHub Actions）

当前工作流：`.github/workflows/deploy.yml`

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with: { version: 10.13.1 }
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm run build:vite  # 改为 pnpm run build
      - uses: actions/upload-pages-artifact@v4
        with:
          path: src/.vuepress/dist  # 改为 src/.vitepress/dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
```

迁移改动：
1. `build:vite` → `build`（或保持别名）
2. `src/.vuepress/dist` → `src/.vitepress/dist`（或 `.vitepress/dist`，取决于 `srcDir` 配置）

### 13.4 Package Manager

使用 `pnpm@10.13.1`，VitePress 项目也建议使用 pnpm。

---

## 十四、依赖清单（迁移前后对比）

| 功能 | 当前依赖 | VitePress 替代 |
|---|---|---|
| 框架 | `vuepress@2.0.0-rc.24` | `vitepress` (latest) |
| 主题 | `vuepress-theme-hope@2.0.0-rc.94` | VitePress 默认主题 |
| 构建 | `@vuepress/bundler-vite@2.0.0-rc.24` | VitePress 内置 Vite |
| Vue | `vue@3.5.17` | VitePress 自带 Vue 3 |
| 搜索 | `@vuepress/plugin-search@2.0.0-rc.112` | VitePress 内置 |
| Feed | `@vuepress/plugin-feed@2.0.0-rc.112` | `feed` (npm) |
| SCSS | `sass-embedded@1.89.2`, `sass-loader@16.0.5` | VitePress 内置 SCSS 支持 |
| Math | `mathjax-full@3.2.2` | `markdown-it-mathjax3` |
| 流程图 | `flowchart.ts@3.0.1` | `markdown-it-flowchart` 或 Mermaid |
| Mermaid | `mermaid@11.8.1` | `vitepress-plugin-mermaid` |
| 评论 | `@waline/client@3.6.0` (已安装未使用) | `@waline/client` (VitePress 也可用) |
| PWA | `@vuepress/plugin-pwa@2.0.0-rc.112` (未启用) | `vite-plugin-pwa` |
| RevealJS | `reveal.js@5.2.1`, `@vuepress/plugin-revealjs` | 需要自定义集成 |
| 缓存 | `@vuepress/plugin-cache@2.0.0-rc.112` | VitePress 无等价，通常不需要 |
| 日期 | `@vuepress/plugin-append-date@2.0.0-rc.112` | 不需要（日期在 frontmatter 中） |
| 部署 | `gh-pages@6.3.0` | 保留（GitHub Actions deploy） |
| Lint | `markdownlint-cli2@0.18.1` | 保留 |
| Format | `prettier@3.6.2` | 保留 |

---

## 十五、迁移任务优先级（建议执行顺序）

| 优先级 | 任务 | 说明 |
|---|---|---|
| P0 | 创建 `.vitepress/` 目录结构，配置 `config.ts` | 站点元数据、侧边栏、导航栏 |
| P0 | 迁移 3 个自定义组件 + 注册 | 直接复制，语法完全兼容 |
| P0 | 迁移 `index.scss` → `custom.css` | 直接复制 |
| P1 | 配置 Shiki + callgraph 语言 | 自定义语言文件复制到 `.vitepress/shiki/` |
| P1 | 配置 MathJax（`markdown-it-mathjax3`） | 在 `markdown.config` 中注册 |
| P1 | 验证所有 71 个 Markdown 页面渲染 | 检查 `:::` 容器、公式、代码块 |
| P2 | 实现博客首页（hero + 文章列表） | 用 `createContentLoader` |
| P2 | 实现分类/标签页 | 动态路由 |
| P2 | 实现时间线 | 动态路由 |
| P3 | 实现 Feed 生成 | buildEnd hook |
| P3 | 实现 Sitemap | buildEnd hook |
| P4 | 更新 CI/CD | 改输出路径 |
| P4 | 清理旧依赖 | `pnpm remove` vuepress 相关包 |
