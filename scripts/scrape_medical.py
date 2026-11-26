#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NexusRAG 医疗药品说明书语料抓取器
数据源: 大医网 dayi.org.cn 药品说明书 / 适应症 / 用法用量页面（公开、无需登录）。
红线: 仅抓公开可访问页面; 不含任何患者/处方/隐私; 不绕过登录或付费墙;
      请求限速(随机 1-3s, 平均<=1 req/s); 单站总量上限 1000 页; 遵循 robots.txt。
输出: 每条药品 -> JSON (含 sections) + 原始 HTML, 按类别分子目录。
"""
import os, sys, re, json, time, random, argparse, hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BASE = r"E:\Temp\NexusRAG"
OUT = os.path.join(BASE, "data", "raw", "medical")
RAW = os.path.join(OUT, "raw_html")
SITEMAP_INDEX = "https://www.dayi.org.cn/sitemap.xml"
CST = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# path 前缀 -> (子目录, 类别中文名)
CATEGORY = {
    "drug":     ("chemical_drug",   "药品说明书(化学药+中成药)"),
    "cmedical": ("chinese_medicine", "中药材/中草药"),
}

def now_cst():
    return datetime.now(CST).isoformat(timespec="seconds")

def polite_sleep():
    time.sleep(random.uniform(1.0, 3.0))

def fetch(session, url, max_retry=3):
    """返回 (status, html_text)。对 412/429/5xx 退避重试; 反复失败返回 (status, None)。"""
    for attempt in range(1, max_retry + 1):
        try:
            r = session.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding or "utf-8"
                return 200, r.text
            if r.status_code in (412, 429) or 500 <= r.status_code < 600:
                wait = random.uniform(2, 5) * attempt
                print(f"    [retry {attempt}/{max_retry}] HTTP {r.status_code} -> sleep {wait:.1f}s")
                time.sleep(wait)
                continue
            return r.status_code, None
        except requests.RequestException as e:
            wait = random.uniform(2, 4) * attempt
            print(f"    [retry {attempt}/{max_retry}] {type(e).__name__} -> sleep {wait:.1f}s")
            time.sleep(wait)
    return -1, None

def parse_drug_page(html, url):
    """解析大医网药品页; 返回 dict 或 None。"""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    drug_name = h1.get_text(strip=True) if h1 else None
    if not drug_name:
        # 退化: 取 <title> 第一段
        t = soup.find("title")
        if t:
            drug_name = re.split(r"[_|]", t.get_text(strip=True))[0].strip()
    sections = {}
    for h2 in soup.find_all("h2"):
        title = h2.get_text(strip=True)
        if not title:
            continue
        fc = h2.find_parent(class_="field-container")
        content = ""
        if fc:
            c = fc.find(class_="field-content")
            if c:
                content = c.get_text("\n", strip=True)
        # 只保留有正文的条目, 同名去重
        if content and title not in sections:
            sections[title] = content
    if not drug_name or not sections:
        return None
    return {"drug_name": drug_name, "sections": sections}

def load_urls(limit_per_cat, seed=20261125):
    """从 sitemap 索引收集 drug / cmedical 页面 URL, 按类别限量。"""
    s = requests.Session()
    st, txt = -1, None
    for attempt in range(3):
        try:
            r = s.get(SITEMAP_INDEX, headers=HEADERS, timeout=25)
            st, txt = r.status_code, r.text
            if st == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    if st != 200:
        print(f"!! 无法获取 sitemap 索引 (status={st})")
        return {"drug": [], "cmedical": [], "_incomplete": True}
    subs = re.findall(r"<loc>(.*?)</loc>", txt or "")
    buckets = {"drug": [], "cmedical": []}
    incomplete = False
    for sm in subs:
        m = re.search(r"/(\d{4}-\d{2}-\d{2})-(drug|cmedical)-\d+\.xml$", sm)
        if not m:
            continue
        cat = m.group(2)
        if len(buckets[cat]) >= limit_per_cat * 6:  # 只需足够多的候选
            continue
        st2, t2 = fetch(s, sm)
        if st2 != 200 or not t2:
            incomplete = True
            continue
        buckets[cat].extend(re.findall(r"<loc>(.*?)</loc>", t2))
        polite_sleep()
    rng = random.Random(seed)
    out = {}
    for cat in buckets:
        uniq = list(dict.fromkeys(buckets[cat]))
        rng.shuffle(uniq)
        out[cat] = uniq[:limit_per_cat]
    out["_incomplete"] = incomplete
    return out

def slug(cat, url):
    pid = url.rstrip("/").split("/")[-1]
    return f"{cat}_{pid}"

def run(limit_per_cat, max_total, resume=True):
    os.makedirs(RAW, exist_ok=True)
    for sub, _ in CATEGORY.values():
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)

    print(f"[1/3] 收集 URL ... (每类上限 {limit_per_cat})")
    urlmap = load_urls(limit_per_cat)
    plan = []
    for cat, (sub, _cn) in CATEGORY.items():
        for u in urlmap.get(cat, []):
            plan.append((cat, sub, u))
    plan = plan[:max_total]
    print(f"    待抓取 {len(plan)} 条: " +
          ", ".join(f"{c}={sum(1 for x in plan if x[0]==c)}" for c in CATEGORY))

    session = requests.Session()
    records = []   # 成功记录，每项含 manifest 所需字段
    skipped = []   # 失败/跳过记录
    t_start = now_cst()

    print(f"[2/3] 抓取并解析 ...")
    for i, (cat, sub, url) in enumerate(plan, 1):
        sid = slug(cat, url)
        json_path = os.path.join(OUT, sub, sid + ".json")
        html_path = os.path.join(RAW, sid + ".html")
        if resume and os.path.exists(json_path) and os.path.getsize(json_path) > 0:
            try:
                d = json.load(open(json_path, encoding="utf-8"))
                records.append({"drug_name": d["drug_name"], "source_url": url,
                                "source_site": "dayi.org.cn", "category": cat,
                                "category_cn": CATEGORY[cat][1],
                                "json": os.path.relpath(json_path, BASE).replace("\\", "/"),
                                "html": os.path.relpath(html_path, BASE).replace("\\", "/"),
                                "n_sections": len(d.get("sections", {})),
                                "fetched_at": d.get("fetched_at")})
                print(f"  [{i}/{len(plan)}] skip(已存在) {sid}")
                continue
            except Exception:
                pass

        st, html = fetch(session, url)
        fetched_at = now_cst()
        if st != 200 or not html:
            skipped.append({"url": url, "category": cat, "status": st, "reason": "fetch_failed"})
            print(f"  [{i}/{len(plan)}] FAIL({st}) {url}")
            polite_sleep()
            continue

        parsed = parse_drug_page(html, url)
        if not parsed:
            skipped.append({"url": url, "category": cat, "status": st, "reason": "parse_empty"})
            print(f"  [{i}/{len(plan)}] PARSE-EMPTY {url}")
            polite_sleep()
            continue

        record = {
            "drug_name": parsed["drug_name"],
            "source_url": url,
            "source_site": "dayi.org.cn",
            "fetched_at": fetched_at,
            "category": cat,
            "category_cn": CATEGORY[cat][1],
            "sections": parsed["sections"],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        records.append({"drug_name": parsed["drug_name"], "source_url": url,
                        "source_site": "dayi.org.cn", "category": cat,
                        "category_cn": CATEGORY[cat][1],
                        "json": os.path.relpath(json_path, BASE).replace("\\", "/"),
                        "html": os.path.relpath(html_path, BASE).replace("\\", "/"),
                        "n_sections": len(parsed["sections"]), "fetched_at": fetched_at})
        print(f"  [{i}/{len(plan)}] OK {parsed['drug_name']} ({len(parsed['sections'])}节)")
        polite_sleep()

    print(f"[3/3] 生成 MANIFEST ...")
    write_manifest(records, skipped, urlmap.get("_incomplete", False), t_start, now_cst(), limit_per_cat, max_total)

    # 机器可读的抓取清单
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": now_cst(), "records": records, "skipped": skipped},
                  f, ensure_ascii=False, indent=2)

    print(f"\n完成: 成功 {len(records)} / 失败跳过 {len(skipped)} / 计划 {len(plan)}")
    return len(records), len(skipped)

def write_manifest(records, skipped, incomplete, t_start, t_end, limit_per_cat, max_total):
    lines = []
    lines.append("# NexusRAG 医疗药品语料抓取 MANIFEST\n")
    lines.append(f"- 生成时间(北京时间): {t_end}")
    lines.append(f"- 抓取开始: {t_start}")
    lines.append("- 抓取脚本: `scripts/scrape_medical.py` (Python 3.11, requests + BeautifulSoup)")
    lines.append("- 主数据源: 大医网 **dayi.org.cn**（药品说明书/适应症/用法用量页面）")
    lines.append("- 备用源: NMPA datasearch.nmpa.gov.cn —— 实测所有请求返回 **HTTP 412**（WAF/JS 挑战），"
                 "重试无效，按项目规则放过，本批次未采集。")
    lines.append("")
    lines.append("## 合规说明")
    lines.append("- 仅抓取公开可访问、无需登录的药品说明书页面；robots.txt 允许 `/`（仅 /search /error /health 禁止）。")
    lines.append("- 不含任何患者病历/处方/个人隐私数据；不绕过登录或付费墙。")
    lines.append("- 限速：每请求后随机 sleep 1–3 秒（平均 < 1 req/s）；单站总量上限 1000 页。")
    lines.append("- 遇 412/429/5xx 自动退避重试（最多 3 次），仍失败则跳过并记录。")
    lines.append("")
    lines.append("## 字段结构")
    lines.append("```json")
    lines.append('{ "drug_name": "...", "source_url": "...", "source_site": "dayi.org.cn",')
    lines.append('  "fetched_at": "ISO8601+08:00", "category": "drug|cmedical", "category_cn": "...",')
    lines.append('  "sections": { "成分": "...", "适应症": "...", "用法用量": "...", ... } }')
    lines.append("```")
    lines.append("- 原始 HTML 保留在 `raw_html/<category>_<id>.html`，与 JSON 一一对应。")
    lines.append("")
    lines.append("## 目录布局")
    lines.append("```")
    lines.append("data/raw/medical/")
    lines.append("├── chemical_drug/      # 化学药/西药 (drug/<id>)")
    lines.append("├── chinese_medicine/   # 中药/中草药 (cmedical/<id>)")
    lines.append("├── raw_html/           # 原始 HTML")
    lines.append("├── MANIFEST.md         # 本文件")
    lines.append("└── manifest.json       # 机器可读清单 (records + skipped)")
    lines.append("```")
    lines.append("")
    # 统计
    from collections import Counter
    cnt = Counter(r["category"] for r in records)
    lines.append("## 本批次统计")
    lines.append(f"- 成功: **{len(records)}** 条")
    for cat, (sub, cn) in CATEGORY.items():
        lines.append(f"  - {cn} (`{sub}`): {cnt.get(cat,0)} 条")
    lines.append(f"- 失败/跳过: {len(skipped)} 条" + ("（见 manifest.json → skipped）" if skipped else ""))
    if incomplete:
        lines.append("- ⚠️ 部分 sub-sitemap 拉取失败，URL 池可能不完整。")
    lines.append("")
    lines.append("## URL 列表（成功抓取）")
    lines.append("| # | drug_name | category | sections | fetched_at | source_url |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(records, 1):
        lines.append(f"| {i} | {r['drug_name']} | {r['category_cn']} | {r['n_sections']} | {r['fetched_at']} | {r['source_url']} |")
    if skipped:
        lines.append("")
        lines.append("## 跳过/失败")
        lines.append("| status | reason | url |")
        lines.append("|---|---|---|")
        for s in skipped:
            lines.append(f"| {s['status']} | {s['reason']} | {s['url']} |")
    lines.append("")
    lines.append("## 复现方式")
    lines.append("```bash")
    lines.append("# 试抓 25 份（每类）")
    lines.append("python scripts/scrape_medical.py --limit-per-cat 25 --max-total 50")
    lines.append("# 放量（每类 500，单站总量 <=1000）")
    lines.append("python scripts/scrape_medical.py --limit-per-cat 500 --max-total 1000")
    lines.append("```")
    with open(os.path.join(OUT, "MANIFEST.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per-cat", type=int, default=25)
    ap.add_argument("--max-total", type=int, default=1000)
    ap.add_argument("--no-resume", action="store_true")
    a = ap.parse_args()
    run(a.limit_per_cat, a.max_total, resume=not a.no_resume)
