import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import os from "node:os";
import fsSync from "node:fs";
let sharp;
try { sharp = createRequire(import.meta.url)("sharp"); }
catch (error) {
  if (!fsSync.existsSync(new URL("../knowledge-base/", import.meta.url))) throw error;
  sharp = createRequire(path.join(os.homedir(), ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/runtime-entry.cjs"))("sharp");
}

const configPath = process.argv[2];
if (!configPath) throw new Error("usage: render_xhs_full_article.mjs CONFIG.json");
const cfg = JSON.parse(await fs.readFile(configPath, "utf8"));
const objectDir = cfg.objectDir || path.dirname(path.dirname(path.resolve(configPath)));
const personalConfig = new URL("../knowledge-base/", import.meta.url);
let internal = false; try { await fs.access(personalConfig); internal = true; } catch {}
const authorLabel = cfg.authorLabel ?? (internal ? "韩叙 HanXu" : "");
const brandLabel = cfg.brandLabel ?? (internal ? "HAN XU · 2026" : "");
const sourceDir = path.join(objectDir, "source", cfg.revision);
const exportDir = path.join(objectDir, "exports", `${cfg.revision}-full-article`);
const raw = await fs.readFile(cfg.sourcePath || path.join(objectDir, "references", "wechat-source-raw.txt"), "utf8");
let texts = raw.split(/\n+/).map((v) => v.trim()).filter(Boolean);
const sourceCount = texts.length;
const sourceChars = texts.join("").length;
let excluded = [];
if (cfg.excludeFrom) {
  const boundary = texts.indexOf(cfg.excludeFrom);
  if (boundary < 0) throw new Error(`Missing advertising boundary: ${cfg.excludeFrom}`);
  excluded = texts.slice(boundary);
  texts = texts.slice(0, boundary);
}
const renderedChars = texts.join("").length;
if (texts[0] !== cfg.opening) throw new Error("Opening gate failed");
if (texts.at(-1) !== cfg.ending) throw new Error("Ending gate failed");

const C = { navy:"#14283B", body:"#293947", muted:"#667786", paper:"#F5F2EA", line:"#CED3D4" };
const esc = (v) => String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
const sansEl = (x,y,v,size,weight=400,fill=C.body,extra="") => `<text x="${x}" y="${y}" font-family="Hiragino Sans GB, STHeiti, PingFang SC, sans-serif" font-size="${size}" font-weight="${weight}" fill="${fill}" ${extra}>${esc(v)}</text>`;
const songEl = (x,y,v,size,weight=500,fill=C.body,extra="") => `<text x="${x}" y="${y}" font-family="Songti SC, STSong, serif" font-size="${size}" font-weight="${weight}" fill="${fill}" ${extra}>${esc(v)}</text>`;
const units = (c) => /\s/.test(c) ? .35 : /[\x00-\x7F]/.test(c) ? .55 : 1;
const wrap = (value, limit=25.2) => {
  const lines=[]; const closing=new Set(["，","。","！","？","：","；","、","）","】","》","…"]); let line="",width=0;
  for (const c of value) { const n=units(c); if(line && width+n>limit && !closing.has(c)){lines.push(line);line=c;width=n;}else{line+=c;width+=n;} }
  if(line) lines.push(line); return lines;
};
const sections = new Set(cfg.sections || []);
const emphases = new Set(cfg.emphases || []);
const looksLikeSubhead = (text) => text.length <= 34 && (
  /^\d+[、.．]/.test(text) ||
  /^[一二三四五六七八九十]+[、.．]/.test(text) ||
  /^(机会|挑战|步骤|误区|建议|结论|重点)[一二三四五六七八九十0-9]+[：:]/.test(text) ||
  /^第[一二三四五六七八九十0-9]+(层|步|件事|个)/.test(text) ||
  /^（[一二三四五六七八九十0-9]+）/.test(text)
);
const normalizedBlocks = [];
if (cfg.mergeExtractedLines) {
  let block = "";
  const flush = () => { if (block) normalizedBlocks.push(block); block = ""; };
  const mergeLimit = cfg.mergeBlockLimit || 118;
  for (const text of texts) {
    const boundary = sections.has(text) || emphases.has(text) || looksLikeSubhead(text);
    if (boundary) { flush(); normalizedBlocks.push(text); continue; }
    const candidate = block + text;
    if (block && [...candidate].reduce((sum,c)=>sum+units(c),0) > mergeLimit) flush();
    block += text;
  }
  flush();
} else {
  normalizedBlocks.push(...texts);
}
const paragraphs = normalizedBlocks.map((text,index)=>({
  text,index,
  section:sections.has(text),
  subhead:!sections.has(text) && looksLikeSubhead(text),
  emphasis:emphases.has(text),
  lines:wrap(text, cfg.wrapLimit || 25.2),
}));

const editorial = Boolean(cfg.editorial);
const dense = Boolean(cfg.dense);
const reference13 = cfg.readingStyle === "reference-20260813";
const exact13 = cfg.readingStyle === "exact-20260813";
const replacement13 = cfg.readingStyle === "replacement-20260813";
const lineHeight = (p) => replacement13
  ? (p.section || p.subhead ? 58 : 50)
  : exact13
  ? (p.section ? 66 : 60)
  : reference13
  ? (p.section ? 52 : p.subhead ? 49 : 46)
  : editorial ? (p.section ? 51 : p.subhead ? 47 : 44) : p.section ? (dense ? 50 : 54) : (dense ? 43 : 47);
let pageBudget = exact13 ? 1110 : reference13 ? (cfg.pageBudget || 1240) : editorial ? (cfg.pageBudget || 1228) : dense ? 1170 : 1175;
const baseGap = replacement13 ? 16 : exact13 ? 28 : reference13 ? (cfg.baseGap || 12) : editorial ? (cfg.baseGap || 12) : dense ? 5 : 8;
const paginate = (budget) => {
  const result=[]; let group=[],used=0;
  for(const p of paragraphs){ const cost=p.lines.length*lineHeight(p)+(group.length?baseGap:0); if(group.length && used+cost>budget){result.push(group);group=[];used=0;} group.push(p.index);used+=p.lines.length*lineHeight(p)+(group.length>1?baseGap:0); }
  if(group.length) result.push(group);
  return result;
};
const renderedHeight = (indices) => {
  const entries=indices.map(i=>paragraphs[i]);
  const h=entries.reduce((sum,p)=>sum+p.lines.length*lineHeight(p),0);
  const gap=entries.length>1
    ? replacement13 ? Math.max(16,Math.min(32,(1290-178-h)/(entries.length-1)))
    : exact13 ? Math.max(28,Math.min(40,(1290-178-h)/(entries.length-1)))
    : baseGap
    : 0;
  return (exact13||replacement13?178:122)+h+Math.max(0,entries.length-1)*gap;
};
let groups;
if (cfg.targetBodyPages) {
  for (let budget=800; budget<=1500; budget+=1) {
    const candidate=paginate(budget);
    if(candidate.length===cfg.targetBodyPages && candidate.every(g=>renderedHeight(g)<=1322)){pageBudget=budget;groups=candidate;break;}
  }
  if(!groups) throw new Error(`Cannot reach target body pages: ${cfg.targetBodyPages}`);
} else groups=paginate(pageBudget);
if(groups.length > 17 && !cfg.allowOverPlatformImageLimit) throw new Error(`Image limit exceeded: ${groups.length+1}`);
if(groups.flat().length !== paragraphs.length) throw new Error("Pagination completeness gate failed");
const totalPages=groups.length+1;

const header = (page) => exact13 || replacement13
  ? `${sansEl(86,76,cfg.runningTitle,18,500,C.muted,'letter-spacing="1.3"')}${sansEl(994,76,`${String(page).padStart(2,"0")} / ${String(totalPages).padStart(2,"0")}`,18,500,C.muted,'text-anchor="end" letter-spacing="1.4"')}<line x1="86" y1="105" x2="994" y2="105" stroke="${C.line}" stroke-width="1.5"/>`
  : `${sansEl(76,64,cfg.runningTitle,15,500,C.muted,'letter-spacing="1.1"')}${sansEl(1004,64,`${String(page).padStart(2,"0")} / ${String(totalPages).padStart(2,"0")}`,15,500,C.muted,'text-anchor="end" letter-spacing="1.1"')}<line x1="76" y1="88" x2="1004" y2="88" stroke="${C.line}" stroke-width="1.2"/>`;
const footer = (page) => exact13 || replacement13
  ? `<line x1="86" y1="1342" x2="994" y2="1342" stroke="${C.line}" stroke-width="1.5"/>${sansEl(86,1382,authorLabel,17,500,C.muted)}${sansEl(994,1382,String(page).padStart(2,"0"),17,500,C.muted,'text-anchor="end"')}`
  : `<line x1="76" y1="1360" x2="1004" y2="1360" stroke="${C.line}" stroke-width="1.2"/>${sansEl(76,1392,authorLabel,14,500,C.muted)}${sansEl(1004,1392,String(page).padStart(2,"0"),14,500,C.muted,'text-anchor="end"')}`;
const renderBody = (indices,page) => {
  let y=exact13 || replacement13 ? 178 : 122;
  const out=[header(page)];
  const entries=indices.map(i=>paragraphs[i]);
  const h=entries.reduce((s,p)=>s+p.lines.length*lineHeight(p),0);
  const gap=entries.length>1
    ? (replacement13
      ? Math.max(16,Math.min(32,(1290-178-h)/(entries.length-1)))
      : exact13
      ? Math.max(28,Math.min(40,(1290-178-h)/(entries.length-1)))
      : reference13
      ? Math.max(cfg.baseGap || 12,Math.min(22,(1340-122-h)/(entries.length-1)))
      : editorial ? Math.max(cfg.baseGap || 12,Math.min(22,(1340-122-h)/(entries.length-1))) : Math.max(dense?5:8,Math.min(dense?12:17,(1303-145-h)/(entries.length-1))))
    : 0;
  for(let i=0;i<entries.length;i++){
    const p=entries[i];
    const size=replacement13 ? (p.section||p.subhead?36:32) : exact13 ? (p.section||p.subhead?40:36) : reference13 ? (p.section?34:p.subhead?33:31) : editorial ? (p.section?34:p.subhead?32:30) : p.section?(dense?34:36):(dense?29:31);
    const weight=p.section?700:p.subhead?650:p.emphasis?650:500;
    for(const line of p.lines){out.push((editorial && !reference13 && !exact13 && !replacement13 ? songEl : sansEl)(exact13||replacement13?86:76,y,line,size,weight,p.section||p.subhead||p.emphasis?C.navy:C.body));y+=lineHeight(p);}
    if(i<entries.length-1)y+=gap;
  }
  if(y>(exact13||replacement13?1322:1355))throw new Error(`Overflow page ${page}: ${y}`);
  out.push(footer(page));
  return out.join("\n");
};
const base = (content) => `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440"><rect width="1080" height="1440" fill="${C.paper}"/>${content}</svg>`;

const photo = await sharp(cfg.photoPath).rotate().resize(1080,690,{fit:"cover",position:cfg.photoPosition||"centre"}).modulate({brightness:cfg.brightness||1.02,saturation:cfg.saturation||.93}).png().toBuffer();
const coverLines = cfg.coverLines;
const coverTitleSize = cfg.coverTitleSize || 68;
const coverTitleWeight = cfg.coverTitleWeight || 700;
const coverTitleLineHeight = cfg.coverTitleLineHeight || 100;
const titleSvg = coverLines.map((line,i)=>sansEl(72,940+i*coverTitleLineHeight,line,coverTitleSize,coverTitleWeight,C.navy)).join("\n");
const coverRuleY = 990 + coverLines.length * coverTitleLineHeight;
const coverSublineY = 1060 + coverLines.length * coverTitleLineHeight;
const photoData = photo.toString("base64");
const cover = cfg.coverVariant === "text-top-photo-bottom"
  ? `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440"><rect width="1080" height="1440" fill="${C.paper}"/><rect x="72" y="84" width="52" height="7" rx="3" fill="#2E6795"/>${sansEl(72,150,cfg.eyebrow,21,600,C.muted,'letter-spacing="1.4"')}${coverLines.map((line,i)=>sansEl(72,270+i*coverTitleLineHeight,line,coverTitleSize,coverTitleWeight,C.navy)).join("\n")}<line x1="72" y1="${320 + coverLines.length * coverTitleLineHeight}" x2="1008" y2="${320 + coverLines.length * coverTitleLineHeight}" stroke="${C.line}" stroke-width="2"/>${sansEl(72,390 + coverLines.length * coverTitleLineHeight,cfg.subline,25,500,C.body)}<image href="data:image/png;base64,${photoData}" x="0" y="750" width="1080" height="690" preserveAspectRatio="xMidYMid slice"/></svg>`
  : `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1440" viewBox="0 0 1080 1440"><rect width="1080" height="1440" fill="${C.paper}"/><image href="data:image/png;base64,${photoData}" x="0" y="0" width="1080" height="690" preserveAspectRatio="xMidYMid slice"/><rect x="0" y="690" width="1080" height="750" fill="${C.paper}"/><rect x="72" y="758" width="52" height="7" rx="3" fill="#2E6795"/>${sansEl(72,824,cfg.eyebrow,21,600,C.muted,'letter-spacing="1.4"')}${titleSvg}<line x1="72" y1="${coverRuleY}" x2="1008" y2="${coverRuleY}" stroke="${C.line}" stroke-width="2"/>${sansEl(72,coverSublineY,cfg.subline,25,500,C.body)}${sansEl(72,1380,brandLabel,17,500,C.muted,'letter-spacing="1.3"')}${sansEl(1008,1380,"01",17,600,C.muted,'text-anchor="end"')}</svg>`;

const pages=[{name:"01-cover",svg:cover}];
groups.forEach((indices,offset)=>{const page=offset+2;pages.push({name:`${String(page).padStart(2,"0")}-full-article`,svg:base(renderBody(indices,page))});});
const forbidden=["广告前原文","逐字完整呈现","不删减","校验结果","全文闸门","内部要求","需求说明"];
const publicLayer=pages.map(p=>p.svg).join("\n"); const leaked=forbidden.filter(p=>publicLayer.includes(p)); if(leaked.length)throw new Error(`Internal leak: ${leaked}`);
try { await fs.access(exportDir); if (!cfg.replace) throw new Error("Output exists; use a new revision or explicit replace"); } catch (error) { if (error.code !== "ENOENT") throw error; }
await fs.rm(exportDir,{recursive:true,force:true});
await fs.rm(sourceDir,{recursive:true,force:true});
await fs.mkdir(exportDir,{recursive:true});
await fs.mkdir(sourceDir,{recursive:true});
for(const page of pages){await fs.writeFile(path.join(sourceDir,`${page.name}.svg`),page.svg);await sharp(Buffer.from(page.svg)).png().toFile(path.join(exportDir,`${page.name}.png`));}
const thumbs=await Promise.all(pages.map(p=>sharp(path.join(exportDir,`${p.name}.png`)).resize(270,360).png().toBuffer()));
const cols=3,rows=Math.ceil(pages.length/cols);await sharp({create:{width:990,height:36+rows*396,channels:4,background:"#D7D2C9"}}).composite(thumbs.map((input,i)=>({input,left:45+(i%cols)*315,top:18+Math.floor(i/cols)*396}))).png().toFile(path.join(exportDir,"00-contact-sheet.png"));
await sharp(path.join(exportDir,"01-cover.png")).resize(270,360).png().toFile(path.join(exportDir,"00-cover-thumbnail.png"));
await fs.writeFile(path.join(exportDir,"00-rendered-article.txt"),`${cfg.sourceTitle}\n\n${texts.join("\n\n")}\n`);
await fs.writeFile(path.join(exportDir,"00-full-source-gate.txt"),["PASS",`source_title=${cfg.sourceTitle}`,`raw_source_paragraphs=${sourceCount}`,`raw_source_characters=${sourceChars}`,`excluded_ad_paragraphs=${excluded.length}`,`rendered_paragraphs=${texts.length}`,`rendered_characters=${renderedChars}`,`images=${pages.length}`,`body_pages=${groups.length}`,`opening=${texts[0]}`,`ending=${texts.at(-1)}`,`advertising_boundary=${cfg.excludeFrom||"none"}`,"rule=All in-boundary article paragraphs preserved in original order."].join("\n")+"\n");
await fs.writeFile(path.join(exportDir,"00-public-layer-gate.txt"),["PASS",`forbidden_phrases=${forbidden.join("|")}`,"leaked_phrases=none"].join("\n")+"\n");
console.log(JSON.stringify({objectId:cfg.objectId,images:pages.length,bodyPages:groups.length,sourceCount,sourceChars,excluded:excluded.length,renderedParagraphs:texts.length,renderedChars,exportDir}));
