import { defineUserConfig } from "vuepress";

import theme from "./theme.js";

export default defineUserConfig({
  base: "/",

  lang: "zh-CN",
  title: "Yukino's Blog",
  description: "Yukino's Blog",

  head: [
    [
      "link",
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Tangerine:wght@400;700&display=swap",
      },
    ],
  ],

  theme,

  // Enable it with pwa
  // shouldPrefetch: false,
});
