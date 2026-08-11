/**
 * Converts frontend/app/globals.css's OKLCH color tokens to the HSL triplets
 * global.css and lib/theme.ts need — React Native's style engine and
 * NativeWind v4 don't parse oklch(). Re-run and copy the output into both
 * files whenever the web app's theme (mauve/base-nova preset) changes.
 */
function oklchToSrgb(L, C, H) {
  const hRad = (H * Math.PI) / 180;
  const a = C * Math.cos(hRad);
  const b = C * Math.sin(hRad);

  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.2914855480 * b;

  const l = l_ ** 3;
  const m = m_ ** 3;
  const s = s_ ** 3;

  let r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s;
  let g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s;
  let bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s;

  const gamma = (c) => {
    c = Math.max(0, Math.min(1, c));
    return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  };

  r = gamma(r);
  g = gamma(g);
  bl = gamma(bl);

  return [r, g, bl].map((c) => Math.round(Math.max(0, Math.min(1, c)) * 255));
}

function rgbToHsl(r, g, b) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  const d = max - min;
  if (d !== 0) {
    s = d / (1 - Math.abs(2 * l - 1));
    switch (max) {
      case r:
        h = ((g - b) / d) % 6;
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      case b:
        h = (r - g) / d + 4;
        break;
    }
    h *= 60;
    if (h < 0) h += 360;
  }
  return [Math.round(h * 10) / 10, Math.round(s * 1000) / 10, Math.round(l * 1000) / 10];
}

function oklchToHsl(L, C, H) {
  const [r, g, b] = oklchToSrgb(L, C, H);
  const [h, s, l] = rgbToHsl(r, g, b);
  return `${h} ${s}% ${l}%`;
}

// L, C, H triplets copied from frontend/app/globals.css.
const tokens = {
  light: {
    background: [1, 0, 0],
    foreground: [0.145, 0.008, 326],
    card: [1, 0, 0],
    cardForeground: [0.145, 0.008, 326],
    popover: [1, 0, 0],
    popoverForeground: [0.145, 0.008, 326],
    primary: [0.555, 0.163, 48.998],
    primaryForeground: [0.987, 0.022, 95.277],
    secondary: [0.967, 0.001, 286.375],
    secondaryForeground: [0.21, 0.006, 285.885],
    muted: [0.96, 0.003, 325.6],
    mutedForeground: [0.542, 0.034, 322.5],
    accent: [0.96, 0.003, 325.6],
    accentForeground: [0.212, 0.019, 322.12],
    destructive: [0.577, 0.245, 27.325],
    border: [0.922, 0.005, 325.62],
    input: [0.922, 0.005, 325.62],
    ring: [0.711, 0.019, 323.02],
    chart1: [0.879, 0.169, 91.605],
    chart2: [0.769, 0.188, 70.08],
    chart3: [0.666, 0.179, 58.318],
    chart4: [0.555, 0.163, 48.998],
    chart5: [0.473, 0.137, 46.201],
  },
  dark: {
    background: [0.145, 0.008, 326],
    foreground: [0.985, 0, 0],
    card: [0.212, 0.019, 322.12],
    cardForeground: [0.985, 0, 0],
    popover: [0.212, 0.019, 322.12],
    popoverForeground: [0.985, 0, 0],
    primary: [0.473, 0.137, 46.201],
    primaryForeground: [0.987, 0.022, 95.277],
    secondary: [0.274, 0.006, 286.033],
    secondaryForeground: [0.985, 0, 0],
    muted: [0.263, 0.024, 320.12],
    mutedForeground: [0.711, 0.019, 323.02],
    accent: [0.263, 0.024, 320.12],
    accentForeground: [0.985, 0, 0],
    destructive: [0.704, 0.191, 22.216],
    border: [1, 0, 0], // oklch(1 0 0 / 10%) in the web app — alpha applied separately, see lib/theme.ts
    input: [1, 0, 0], // oklch(1 0 0 / 15%) in the web app — alpha applied separately, see lib/theme.ts
    ring: [0.542, 0.034, 322.5],
    chart1: [0.879, 0.169, 91.605],
    chart2: [0.769, 0.188, 70.08],
    chart3: [0.666, 0.179, 58.318],
    chart4: [0.555, 0.163, 48.998],
    chart5: [0.473, 0.137, 46.201],
  },
};

for (const [mode, colors] of Object.entries(tokens)) {
  console.log(`\n-- ${mode} --`);
  for (const [name, [L, C, H]] of Object.entries(colors)) {
    console.log(`${name}: ${oklchToHsl(L, C, H)}`);
  }
}
