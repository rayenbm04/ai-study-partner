/**
 * Web counterpart to MathBlock.tsx — Metro picks this file automatically on
 * the web target (the .web.tsx extension). react-native-webview has no
 * working web implementation (it renders "does not support this platform"
 * instead of a WebView), but on web we're already inside a real browser, so
 * there's no need for a WebView at all: render KaTeX's HTML output directly
 * into the DOM via the `katex` npm package.
 *
 * KaTeX's stylesheet/fonts load from the same CDN the native WebView build
 * uses (see MathBlock.tsx) rather than being bundled — Metro's web CSS
 * pipeline doesn't reliably resolve KaTeX's relative font URLs, so a CDN
 * `<link>` injected into the page head is the reliable option here too.
 */
import { createElement, useEffect, useMemo, useState } from "react";
import katex from "katex";

const KATEX_VERSION = "0.16.11";
const KATEX_CSS_LINK_ID = "katex-css-cdn";

function ensureKatexCssLoaded() {
  if (typeof document === "undefined") return;
  if (document.getElementById(KATEX_CSS_LINK_ID)) return;
  const link = document.createElement("link");
  link.id = KATEX_CSS_LINK_ID;
  link.rel = "stylesheet";
  link.href = `https://cdn.jsdelivr.net/npm/katex@${KATEX_VERSION}/dist/katex.min.css`;
  document.head.appendChild(link);
}

type MathBlockProps = {
  latex: string;
  display?: boolean;
  color: string;
};

export function MathBlock({ latex, display = true, color }: MathBlockProps) {
  useEffect(ensureKatexCssLoaded, []);

  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, { throwOnError: false, displayMode: display });
    } catch {
      return latex;
    }
  }, [latex, display]);

  return createElement("div", {
    style: { color, overflowX: "auto", padding: "6px 2px" },
    dangerouslySetInnerHTML: { __html: html },
  });
}
