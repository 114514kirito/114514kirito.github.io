import { defineUserConfig } from "vuepress";
import theme from "./theme.js";

export default defineUserConfig({
  base: "/",

  lang: "zh-CN",
  title: "Yukino's Blog",
  description: "Yukino's Blog",

  theme,

  // Enable it with pwa
  // shouldPrefetch: false,
});
