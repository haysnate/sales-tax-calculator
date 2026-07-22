# Generates the 51 state pages, the sitemap, and the static state-links
# block in index.html from the STATES table in public/script.js.
# Run from the repo root: py generate_state_pages.py
import json, re, pathlib

PUB = pathlib.Path(__file__).parent / "public"
DOMAIN = "https://salestaxcalculatorhq.com"

# ---- parse STATES from script.js (single source of truth) ----
js = (PUB / "script.js").read_text(encoding="utf-8")
block = js.split("const STATES = {")[1].split("\n};")[0]
states = {}
for m in re.finditer(r'(\w+): \{ name: "([^"]+)", slug: "([^"]+)", state: ([\d.]+), local: ([\d.]+)(.*?) \},', block):
    code, name, slug, state, local, flags = m.groups()
    states[code] = {
        "name": name, "slug": slug, "state": float(state), "local": float(local),
        "none": "none: true" in flags, "get": "get: true" in flags, "uez": "uez: true" in flags,
        "mandatoryLocal": (lambda f: float(f.group(1)) if f else None)(re.search(r"mandatoryLocal: ([\d.]+)", flags)),
    }
assert len(states) == 51, f"expected 51 states, parsed {len(states)}"

def fmt_rate(r):
    s = f"{r:.3f}".rstrip("0").rstrip(".")
    return s

def money(n):
    return f"${n:,.2f}"

index_template = (PUB / "index.html").read_text(encoding="utf-8")

# ---- static state links block (for index and each state page) ----
links = " ".join(
    f'<a href="{s["slug"]}-sales-tax-calculator">{s["name"]}</a>'
    for s in sorted(states.values(), key=lambda x: x["name"])
)
index_out = re.sub(r'<p id="stateLinks"[^>]*>.*?</p>',
                   f'<p id="stateLinks" style="font-size:0.9rem;line-height:2">{links}</p>',
                   index_template, flags=re.S)
(PUB / "index.html").write_text(index_out, encoding="utf-8")

# ---- per-state pages ----
for code, s in states.items():
    name, slug = s["name"], s["slug"]
    combined = s["state"] + s["local"]
    cr, sr, lr = fmt_rate(combined), fmt_rate(s["state"]), fmt_rate(s["local"])
    fname = f"{slug}-sales-tax-calculator.html"
    clean = f"{slug}-sales-tax-calculator"  # Cloudflare Pages serves the extensionless URL

    if s["none"] and s["local"] > 0:
        rate_sentence = f"{name} has no statewide sales tax, but local governments levy their own. The average local rate is {lr}%, so a typical purchase is taxed at about {cr}%."
        faq1 = f"{name} has no statewide sales tax. Local governments levy their own sales taxes, which average {lr}% across the state, so most purchases are taxed at a low single-digit rate that varies by city."
    elif s["none"]:
        rate_sentence = f"{name} has no state or local sales tax. The price on the tag is the price you pay."
        faq1 = f"{name} has no state or local sales tax. It is one of the five NOMAD states (New Hampshire, Oregon, Montana, Alaska, Delaware) with no statewide sales tax, and unlike Alaska it allows no local sales taxes either."
    else:
        rate_sentence = f"The {name} state sales tax rate is {sr}%. Local rates average {lr}%, for a combined average of {cr}%."
        faq1 = f"The statewide rate is {sr}%. With local taxes included, the average combined rate is {cr}% as of July 1, 2026, though your exact rate depends on your city and county."

    notes = []
    if s["mandatoryLocal"]:
        notes.append(f"The {sr}% state rate shown includes a mandatory statewide local rate of {fmt_rate(s['mandatoryLocal'])}%.")
    if s["get"]:
        notes.append("Hawaii technically levies a general excise tax (GET) on businesses rather than a sales tax on buyers; in practice it is usually passed on and works out similarly at the register.")
    if s["uez"]:
        notes.append("Some New Jersey urban enterprise zones charge half the state rate on qualifying purchases.")
    notes_html = (' ' + " ".join(notes)) if notes else ""

    rows = "\n".join(
        f"          <tr><td>{money(a)}</td><td>{money(a*combined/100)}</td><td>{money(a*(1+combined/100))}</td></tr>"
        for a in (100, 500, 1000)
    )

    faq2 = f"At the average combined rate of {cr}%, sales tax on a $100 purchase in {name} is {money(100*combined/100)}, for a total of {money(100*(1+combined/100))}."
    if s["none"] and s["local"] == 0:
        faq2 = f"Nothing. {name} has no sales tax, so a $100 purchase costs exactly $100.00 at the register."
    faq3_yes = f"Yes. Local sales taxes in {name} average {lr}% on top of the state rate, and the exact rate varies by city and county."
    faq3_no = f"No. {name} has a single statewide rate of {sr}% with no additional local sales taxes." if not s["none"] else f"No. {name} has no state or local sales taxes."
    faq3 = faq3_yes if s["local"] > 0 else faq3_no

    faq_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"What is the sales tax in {name}?",
             "acceptedAnswer": {"@type": "Answer", "text": faq1}},
            {"@type": "Question", "name": f"How much is sales tax on a $100 purchase in {name}?",
             "acceptedAnswer": {"@type": "Answer", "text": faq2}},
            {"@type": "Question", "name": f"Does {name} have local sales taxes?",
             "acceptedAnswer": {"@type": "Answer", "text": faq3}},
        ],
    }, ensure_ascii=False)

    title = f"{name} Sales Tax Calculator 2026 - {cr}% Combined Rate"
    if s["none"] and s["local"] == 0:
        title = f"{name} Sales Tax Calculator 2026 - No Sales Tax"
    desc = f"Free {name} sales tax calculator with July 2026 rates. {rate_sentence} Add tax to a price or work backwards from a total."

    page = index_template
    page = page.replace("<title>Sales Tax Calculator 2026 - All 50 States &amp; Local Rates</title>", f"<title>{title}</title>")
    page = page.replace('content="Free sales tax calculator with July 2026 rates for all 50 states and DC. Add tax to a price or work backwards from a total, with state and average local rates built in."', f'content="{desc}"')
    page = page.replace('href="https://salestaxcalculatorhq.com/" />', f'href="{DOMAIN}/{clean}" />')
    page = page.replace('content="Sales Tax Calculator 2026 - All 50 States &amp; Local Rates" />', f'content="{title}" />')
    page = page.replace('content="https://salestaxcalculatorhq.com/" />', f'content="{DOMAIN}/{clean}" />')
    page = page.replace('<h1 id="pageH1">Sales Tax Calculator</h1>', f'<h1 id="pageH1">{name} Sales Tax Calculator</h1>')
    page = page.replace('<p class="subtitle">2026 rates for every state, plus local taxes.</p>', f'<p class="subtitle">2026 rates: state {sr}%, average local {lr}%.</p>' if not (s["none"] and s["local"]==0) else '<p class="subtitle">No sales tax. Lucky you.</p>')
    page = page.replace('<script src="script.js"></script>', f'<script>window.PRESET_STATE = "{code}";</script>\n  <script src="script.js"></script>')

    info = f'''    <section class="doc" style="max-width:760px;padding:26px 28px">
      <h2 style="font-size:1.05rem;font-weight:700;margin-bottom:10px">Sales tax in {name} (2026)</h2>
      <p style="font-size:0.94rem">{rate_sentence}{notes_html} Rates from the Tax Foundation's July 1, 2026 midyear table.</p>
      <div class="table-wrap">
      <table>
        <thead><tr><th>Purchase</th><th>Sales tax (avg {cr}%)</th><th>Total</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
      </div>
      <div class="faq">
        <h3>What is the sales tax in {name}?</h3>
        <p>{faq1}</p>
        <h3>How much is sales tax on a $100 purchase in {name}?</h3>
        <p>{faq2}</p>
        <h3>Does {name} have local sales taxes?</h3>
        <p>{faq3}</p>
      </div>
      <p style="font-size:0.9rem;margin-top:10px"><a href="/">All states</a> · <a href="guide">How US sales tax works</a></p>
    </section>
'''
    # swap the state-links section for the state info section, and add FAQ schema
    page = re.sub(r'    <section class="doc" style="max-width:760px;padding:26px 28px">\n      <h2[^>]*>Sales tax calculator by state</h2>.*?</section>\n', info, page, flags=re.S)
    page = page.replace("  </script>\n</head>", f'  </script>\n  <script type="application/ld+json">\n  {faq_schema}\n  </script>\n</head>')
    (PUB / fname).write_text(page, encoding="utf-8")

# ---- sitemap ----
urls = [f"{DOMAIN}/", f"{DOMAIN}/guide", f"{DOMAIN}/about", f"{DOMAIN}/privacy"]
urls += [f"{DOMAIN}/{s['slug']}-sales-tax-calculator" for s in sorted(states.values(), key=lambda x: x["name"])]
prio = {f"{DOMAIN}/": "1.0", f"{DOMAIN}/guide": "0.8", f"{DOMAIN}/about": "0.3", f"{DOMAIN}/privacy": "0.3"}
entries = "\n".join(
    f"  <url>\n    <loc>{u}</loc>\n    <changefreq>{'yearly' if prio.get(u)=='0.3' else 'monthly'}</changefreq>\n    <priority>{prio.get(u,'0.8')}</priority>\n  </url>"
    for u in urls
)
(PUB / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n', encoding="utf-8")

print(f"Generated {len(states)} state pages, sitemap ({len(urls)} URLs), and index links block.")
