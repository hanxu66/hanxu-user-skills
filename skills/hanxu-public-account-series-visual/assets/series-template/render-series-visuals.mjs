import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const runtimeRequire = createRequire(import.meta.url);
const sharp = runtimeRequire('sharp');

const baseDir = path.dirname(new URL(import.meta.url).pathname);
const configPath = process.argv[2] || path.join(baseDir, 'config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const outDir = process.env.PA_SERIES_OUTPUT_DIR
  ? path.resolve(process.env.PA_SERIES_OUTPUT_DIR)
  : path.join(path.dirname(configPath), 'renders');
fs.mkdirSync(outDir, { recursive: true });

const palette = {
  paper: '#F2F4F6',
  white: '#FAFBFC',
  navy: '#17243A',
  blue: '#365A7C',
  muted: '#6E7783',
  pale: '#DDE3EA',
  line: '#C9D1DA'
};

function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function autoLines(title, maxChars = 8) {
  if (title.length <= maxChars) return [title];
  const punctuation = ['，', '。', '？', '！', '：', '；', ','];
  const near = Math.round(title.length / 2);
  let split = -1;
  for (let d = 0; d <= 4; d += 1) {
    for (const idx of [near - d, near + d]) {
      if (idx > 0 && punctuation.includes(title[idx])) {
        split = idx + 1;
        break;
      }
    }
    if (split > 0) break;
  }
  if (split < 0) split = Math.min(maxChars, Math.ceil(title.length / 2));
  const first = title.slice(0, split);
  const rest = title.slice(split);
  return rest.length > maxChars
    ? [first, rest.slice(0, maxChars), rest.slice(maxChars)]
    : [first, rest];
}

function titleLines() {
  if (Array.isArray(config.titleLines) && config.titleLines.length) {
    return config.titleLines;
  }
  return autoLines(config.title);
}

function renderTextLines(lines, x, y, fontSize, lineHeight) {
  return lines.map((line, index) =>
    `<text x="${x}" y="${y + index * lineHeight}" class="title">${esc(line)}</text>`
  ).join('\n');
}

function svgFor(kind) {
  const cover = kind === 'cover';
  const width = cover ? 900 : 1080;
  const height = cover ? 383 : 120;
  const lines = titleLines();
  const issue = String(config.issueNumber).padStart(2, '0');
  if (cover && config.coverStyle === '2') return coverTwoSvg(lines, issue);

  if (!cover) {
    return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="120" viewBox="0 0 1080 120">
  <rect width="1080" height="120" fill="${palette.navy}"/>
  <line x1="78" y1="60" x2="224" y2="60" stroke="${palette.white}" stroke-width="1" opacity="0.24"/>
  <text x="540" y="76" text-anchor="middle" class="header-series">${esc([config.author, config.seriesName].filter(Boolean).join("的"))}　<tspan class="header-issue">第${esc(issue)}篇</tspan></text>
  <line x1="856" y1="60" x2="1002" y2="60" stroke="${palette.white}" stroke-width="1" opacity="0.24"/>
  <style>
    .header-series { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 40px; font-weight: 600; fill: ${palette.white}; letter-spacing: 3px; }
    .header-issue { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 24px; font-weight: 400; fill: ${palette.white}; opacity: 0.72; letter-spacing: 2px; }
  </style>
</svg>`;
  }

  const fontSize = lines.length >= 3 ? 43 : 58;
  const lineHeight = Math.round(fontSize * 1.24);
  const titleX = 68;
  const titleY = lines.length === 1 ? 198 : 141;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="900" height="383" fill="#E7EBF0"/>
  <rect x="0" y="0" width="14" height="383" fill="${palette.navy}"/>

  <g transform="translate(697 71)">
    <rect x="0" y="36" width="116" height="148" rx="8" fill="none" stroke="${palette.navy}" stroke-width="2" opacity="0.12"/>
    <rect x="18" y="18" width="116" height="148" rx="8" fill="none" stroke="${palette.navy}" stroke-width="2" opacity="0.20"/>
    <rect x="36" y="0" width="116" height="148" rx="8" fill="${palette.navy}" fill-opacity="0.05" stroke="${palette.navy}" stroke-width="2" opacity="0.34"/>
    <circle cx="54" cy="22" r="4" fill="${palette.blue}" opacity="0.68"/>
    <line x1="70" y1="22" x2="129" y2="22" stroke="${palette.navy}" stroke-width="2" opacity="0.18"/>
    <line x1="54" y1="52" x2="129" y2="52" stroke="${palette.navy}" stroke-width="2" opacity="0.16"/>
    <line x1="54" y1="80" x2="116" y2="80" stroke="${palette.navy}" stroke-width="2" opacity="0.16"/>
    <line x1="54" y1="108" x2="125" y2="108" stroke="${palette.navy}" stroke-width="2" opacity="0.16"/>
  </g>

  ${renderTextLines(lines, titleX, titleY, fontSize, lineHeight)}
  <line x1="68" y1="294" x2="640" y2="294" stroke="${palette.navy}" stroke-width="1" opacity="0.16"/>
  <text x="68" y="332" class="subtitle">${esc([config.author, config.seriesName].filter(Boolean).join("的"))}　<tspan class="subtitle-issue">第${esc(issue)}篇</tspan></text>
  <style>
    .title { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: ${fontSize}px; font-weight: 700; fill: ${palette.navy}; letter-spacing: -0.6px; }
    .subtitle { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 18px; font-weight: 500; fill: ${palette.navy}; letter-spacing: 1.6px; }
    .subtitle-issue { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 18px; font-weight: 500; fill: ${palette.blue}; letter-spacing: 1.6px; }
  </style>
</svg>`;
}

function squareSvg() {
  const issue = String(config.issueNumber).padStart(2, '0');
  if (config.coverStyle === '2') return squareTwoSvg(issue);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="383" height="383" viewBox="0 0 383 383">
  <rect width="383" height="383" fill="${palette.navy}"/>
  <text x="54" y="139" class="series-small">${esc(config.author ? config.author + "的" : "")}</text>
  <text x="54" y="190" class="series">${esc(config.seriesName || "")}</text>
  <line x1="54" y1="235" x2="329" y2="235" stroke="${palette.white}" stroke-width="1" opacity="0.22"/>
  <text x="54" y="301" class="issue">第${esc(issue)}篇</text>

  <style>
    .series-small { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 25px; font-weight: 400; fill: ${palette.white}; opacity: 0.80; letter-spacing: 4px; }
    .series { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 32px; font-weight: 600; fill: ${palette.white}; letter-spacing: 2px; }
    .issue { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 27px; font-weight: 400; fill: ${palette.white}; opacity: 0.72; letter-spacing: 5px; }
  </style>
</svg>`;
}

function coverTwoSvg(lines) {
  const units = line => Array.from(line).reduce((n, ch) => n + (/^[\x00-\x7F]$/.test(ch) ? 0.62 : 1), 0);
  const fontSize = Math.min(46, Math.floor(740 / Math.max(...lines.map(units))));
  const lineHeight = Math.round(fontSize * 1.38);
  const titleY = Math.round(191.5 - (lines.length - 1) * lineHeight / 2 + fontSize * 0.38);
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="383" viewBox="0 0 900 383">
  <defs>
    <linearGradient id="paperWash" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F5F7FA"/><stop offset="1" stop-color="#DDE7EF"/></linearGradient>
    <radialGradient id="blueWash"><stop offset="0" stop-color="#96B4C9" stop-opacity="0.2"/><stop offset="1" stop-color="#96B4C9" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="900" height="383" fill="url(#paperWash)"/>
  <ellipse cx="786" cy="327" rx="330" ry="280" fill="url(#blueWash)"/>
  <path d="M670 0L900 0L900 383L554 383Z" fill="#B9CBD9" opacity="0.09"/>
  <g fill="none" stroke="#879FB2" stroke-width="1" opacity="0.16">
    <path d="M650 315L811 315L811 63"/><path d="M693 345L845 345L845 104"/>
  </g>
  ${config.brandLabel ? `<text x="80" y="100" class="brand-label">${esc(config.brandLabel)}</text>` : ''}
  ${renderTextLines(lines, 80, titleY, fontSize, lineHeight)}
  <style>
    .title { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: ${fontSize}px; font-weight: 600; fill: #24364B; letter-spacing: 0; }
    .brand-label { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-size: 18px; font-weight: 400; fill: #6C8295; letter-spacing: 1px; }
  </style>
</svg>`;
}

async function squareTwoSvg() {
  const lines = config.squareLines;
  if (!Array.isArray(lines) || !lines.length) throw new Error('Missing concise square topic');
  const units = line => Array.from(line).reduce((n, ch) => n + (/^[\x00-\x7F]$/.test(ch) ? 0.62 : 1), 0);
  const mainFont = Math.min(62, Math.floor(279 / units(lines[0])));
  const secondFont = lines[1] ? Math.min(44, Math.floor(279 / units(lines[1]))) : 0;
  const fonts = [mainFont, secondFont];
  const positions = [];
  for (let i = 0; i < lines.length; i++) {
    const probe = `<svg xmlns="http://www.w3.org/2000/svg" width="383" height="200"><text x="191.5" y="100" text-anchor="middle" style='font-family:"Hiragino Sans GB","STHeiti",sans-serif;font-size:${fonts[i]}px;font-weight:${i === 0 ? 600 : 400};fill:white;letter-spacing:0'>${esc(lines[i])}</text></svg>`;
    const { data, info } = await sharp(Buffer.from(probe)).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    let left = 383, right = 0, top = 200, bottom = 0;
    for (let y = 0; y < info.height; y++) for (let x = 0; x < info.width; x++) {
      if (data[(y * info.width + x) * info.channels + 3] > 32) {
        left = Math.min(left, x); right = Math.max(right, x);
        top = Math.min(top, y); bottom = Math.max(bottom, y);
      }
    }
    positions.push({ x: 191.5 + (191.5 - (left + right) / 2), top, height: bottom - top + 1 });
  }
  const gap = 22;
  const blockHeight = positions.reduce((n, p) => n + p.height, 0) + gap * (lines.length - 1);
  let nextTop = (383 - blockHeight) / 2;
  for (const p of positions) { p.y = 100 + nextTop - p.top; nextTop += p.height + gap; }
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="383" height="383" viewBox="0 0 383 383">
  <defs>
    <linearGradient id="topicPaper" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#263D56"/><stop offset="1" stop-color="#1C2D42"/></linearGradient>
  </defs>
  <rect width="383" height="383" fill="url(#topicPaper)"/>
  <path d="M255 0H383V383H337Z" fill="#839CB3" opacity="0.06"/>
  <path d="M52 73H89M331 310H294" stroke="#A3B7C9" stroke-width="1.5" opacity="0.6"/>
  <text x="${positions[0].x}" y="${positions[0].y}" text-anchor="middle" class="square-topic" font-size="${mainFont}">${esc(lines[0])}</text>
  ${lines[1] ? `<text x="${positions[1].x}" y="${positions[1].y}" text-anchor="middle" class="square-topic square-secondary" font-size="${secondFont}">${esc(lines[1])}</text>` : ''}
  <style>
    .square-topic { font-family: "Hiragino Sans GB", "STHeiti", sans-serif; font-weight: 600; fill: #F3F6FA; letter-spacing: 0; }
    .square-secondary { font-weight: 400; fill: #CDDCE8; }
  </style>
</svg>`;
}

async function render(kind, filename) {
  const svg = svgFor(kind);
  const svgPath = path.join(outDir, `${filename}.svg`);
  const pngPath = path.join(outDir, `${filename}.png`);
  fs.writeFileSync(svgPath, svg, 'utf8');
  await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toFile(pngPath);
  return { svgPath, pngPath };
}

const issue = config.coverStyle === '2' ? null : String(config.issueNumber).padStart(2, '0');
const stem = issue === null ? `${config.contentObjectId}-COVER2-${config.visualRevision}` : `${config.contentObjectId}-S${issue}-${config.visualRevision}`;
const coverResult = await render('cover', `${stem}-message-list-crop-900x383`);
const headerResult = config.coverOnly ? null : await render('header', `${stem}-article-header-1080x120`);

const square = await squareSvg();
const squareSvgPath = path.join(outDir, `${stem}-square-crop-383x383.svg`);
const squarePngPath = path.join(outDir, `${stem}-square-crop-383x383.png`);
fs.writeFileSync(squareSvgPath, square, 'utf8');
await sharp(Buffer.from(square)).png({ compressionLevel: 9 }).toFile(squarePngPath);

const masterSvg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1283" height="383" viewBox="0 0 1283 383">
  <image x="0" y="0" width="900" height="383" href="data:image/png;base64,${fs.readFileSync(coverResult.pngPath).toString('base64')}"/>
  <image x="900" y="0" width="383" height="383" href="data:image/png;base64,${fs.readFileSync(squarePngPath).toString('base64')}"/>
</svg>`;
const masterSvgPath = path.join(outDir, `${stem}-UPLOAD-MASTER-1283x383.svg`);
const masterPngPath = path.join(outDir, `${stem}-UPLOAD-MASTER-1283x383.png`);
fs.writeFileSync(masterSvgPath, masterSvg, 'utf8');
await sharp(Buffer.from(masterSvg)).png({ compressionLevel: 9 }).toFile(masterPngPath);

const results = [
  { role: 'upload-master', svgPath: masterSvgPath, pngPath: masterPngPath },
  { role: 'message-list-crop-check', ...coverResult },
  { role: 'square-crop-check', svgPath: squareSvgPath, pngPath: squarePngPath },
  ...(headerResult ? [{ role: 'article-header', ...headerResult }] : [])
];

console.log(JSON.stringify({ configPath, results }, null, 2));
