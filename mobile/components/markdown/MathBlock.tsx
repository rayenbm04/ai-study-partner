/**
 * Renders one LaTeX expression as real typeset math (fractions, sums,
 * superscripts, proper symbol fonts) via KaTeX inside a WebView — React
 * Native has no native math-typesetting primitive, and KaTeX is the
 * lightest widely-used renderer that runs standalone in an HTML page.
 * KaTeX's CSS/JS load from a CDN rather than being bundled, so this needs
 * network access (the app already requires it for chat); the WebView caches
 * them after first load so repeated equations in the same session are fast.
 *
 * The WebView reports its rendered content height back over
 * postMessage/onMessage so the outer View can size to fit instead of
 * clipping or leaving dead space — a WebView has no intrinsic size RN can
 * measure on its own.
 */
import { useMemo, useState } from "react";
import { View } from "react-native";
import WebView from "react-native-webview";

const KATEX_VERSION = "0.16.11";
const DEFAULT_HEIGHT = 32;

type MathBlockProps = {
  latex: string;
  display?: boolean;
  color: string;
};

export function MathBlock({ latex, display = true, color }: MathBlockProps) {
  const [height, setHeight] = useState(DEFAULT_HEIGHT);

  const html = useMemo(() => {
    const latexJson = JSON.stringify(latex);
    return `<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@${KATEX_VERSION}/dist/katex.min.css">
<style>
  html, body { margin: 0; padding: 0; background: transparent; }
  #eq { padding: 6px 2px; overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .katex { font-size: 1.05em; color: ${color}; }
  .katex-display { margin: 0; }
</style>
</head><body>
<div id="eq"></div>
<script src="https://cdn.jsdelivr.net/npm/katex@${KATEX_VERSION}/dist/katex.min.js"></script>
<script>
  function post() {
    var h = document.getElementById('eq').scrollHeight;
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify({ height: h }));
  }
  try {
    katex.render(${latexJson}, document.getElementById('eq'), { throwOnError: false, displayMode: ${display} });
  } catch (e) {
    document.getElementById('eq').innerText = ${latexJson};
  }
  post();
  window.addEventListener('load', post);
  setTimeout(post, 150);
</script>
</body></html>`;
  }, [latex, display, color]);

  return (
    <View style={{ height }}>
      <WebView
        originWhitelist={["*"]}
        source={{ html }}
        style={{ backgroundColor: "transparent" }}
        scrollEnabled={false}
        setSupportMultipleWindows={false}
        onMessage={(event) => {
          try {
            const data = JSON.parse(event.nativeEvent.data) as { height?: number };
            if (typeof data.height === "number" && data.height > 0) {
              setHeight(Math.ceil(data.height) + 4);
            }
          } catch {
            // ignore malformed postMessage payloads
          }
        }}
      />
    </View>
  );
}
