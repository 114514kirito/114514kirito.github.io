import { sidebar } from "vuepress-theme-hope";

export default sidebar([
  "/",
  {
    text: "xv6-riscv-book",
    collapsible: true,
    prefix: "/xv6-riscv-book/",
    children: [
      "",
      "chapter1/",
      "chapter2/",
      "chapter3/",
      "chapter4/",
      "chapter5/",
      "chapter6/",
      "chapter7/",
      "chapter8/",
      "chapter9/",
    ],
  },
]);
