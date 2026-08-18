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
        "tfCombined": (lambda f: float(f.group(1)) if f else None)(re.search(r"tfCombined: ([\d.]+)", flags)),
    }
assert len(states) == 51, f"expected 51 states, parsed {len(states)}"

def fmt_rate(r):
    s = f"{r:.3f}".rstrip("0").rstrip(".")
    return s

from decimal import Decimal, ROUND_HALF_UP

def money(n):
    # snap binary float noise at 6 decimals, then round half-up to cents:
    # matches the JS engine's r2 exactly (f-string round-half-even and raw
    # float noise both disagreed on half-cent boundaries)
    snapped = Decimal(str(n)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return "${:,.2f}".format(snapped.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def write_if_changed(path, content):
    """Skip identical writes so file mtimes stay honest (sitemap lastmod reads
    them) and reruns are true no-ops."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True

# data source, verified live 2026-07-26 (real browser: exact report page)
TF_URL = "https://taxfoundation.org/data/all/state/2026-sales-tax-rates-midyear/"
TF_LINK = f'<a href="{TF_URL}">Tax Foundation\'s July 1, 2026 midyear table</a>'

index_template = (PUB / "index.html").read_text(encoding="utf-8")

# ---- static state links block (for index and each state page) ----
links = " ".join(
    f'<a href="{s["slug"]}-sales-tax-calculator">{s["name"]}</a>'
    for s in sorted(states.values(), key=lambda x: x["name"])
)
index_out = re.sub(r'<p id="stateLinks"[^>]*>.*?</p>',
                   f'<p id="stateLinks" style="font-size:0.9rem;line-height:2">{links}</p>',
                   index_template, flags=re.S)
write_if_changed(PUB / "index.html", index_out)

# ---- per-state pages ----
ordered = sorted(states.values(), key=lambda x: x["name"])
for code, s in states.items():
    name, slug = s["name"], s["slug"]
    # alphabetical neighbors keep the 51-page mesh connected (audit 2026-07-26:
    # zero state-to-state links existed)
    i = next(j for j, o in enumerate(ordered) if o["slug"] == slug)
    sibs = [ordered[(i - 1) % len(ordered)], ordered[(i + 1) % len(ordered)]]
    sibling_links = " · ".join(
        f'<a href="{o["slug"]}-sales-tax-calculator">{o["name"]} sales tax</a>' for o in sibs)
    combined = s["state"] + s["local"]
    cr, sr, lr = fmt_rate(combined), fmt_rate(s["state"]), fmt_rate(s["local"])
    fname = f"{slug}-sales-tax-calculator.html"
    clean = f"{slug}-sales-tax-calculator"  # Cloudflare Pages serves the extensionless URL

    if s["none"] and s["local"] > 0:
        # Alaska. The old sentence was a tautology ("average local rate is
        # 1.82%, so ... taxed at about 1.82%") because state rate is 0; it
        # shipped in the meta description too (audit 2026-07-26).
        rate_sentence = f"{name} has no statewide sales tax, but its cities and boroughs levy their own local sales taxes, which average {lr}% statewide. Your actual rate depends on where you buy."
        faq1 = f"{name} has no statewide sales tax. Local governments levy their own sales taxes, which average {lr}% across the state, so most purchases are taxed at a low single-digit rate that varies by city."
    elif s["none"]:
        rate_sentence = f"{name} has no state or local sales tax. The price on the tag is the price you pay."
        faq1 = f"{name} has no state or local sales tax. It is one of the five NOMAD states (New Hampshire, Oregon, Montana, Alaska, Delaware) with no statewide sales tax, and unlike Alaska it allows no local sales taxes either."
    elif s["get"]:
        # Hawaii. Lead with the GET truth instead of calling it a "sales tax
        # rate" and correcting one sentence later (audit 2026-07-26).
        rate_sentence = f"{name} levies a {sr}% general excise tax (GET) on businesses rather than a true sales tax. It is usually passed through to buyers: the combined GET-plus-surcharge burden averages {cr}%, and because the GET applies to the passed-on tax as well, sellers may lawfully pass on up to 4.712%, so a $100 purchase can ring up as much as $104.71 at the register."
        faq1 = f"{name} does not levy a traditional sales tax. Its {sr}% general excise tax (GET) falls on businesses and is usually passed on to buyers; with average local surcharges of {lr}%, the combined burden is about {cr}% as of July 1, 2026, and the maximum lawful pass-on rate is 4.712%."
    elif s["uez"]:
        tfc = f"{s['tfCombined']:.2f}"  # cite the source figure verbatim (6.60, not 6.6)
        rate_sentence = f"The {name} state sales tax rate is {sr}%. There are no general local sales taxes, though urban enterprise zones charge half the state rate on qualifying purchases, which pulls the published average combined rate to {tfc}%."
        faq1 = f"The statewide rate is {sr}% with no general local sales taxes. Qualifying sellers in urban enterprise zones charge half the state rate, so the population-weighted average combined rate is {tfc}% as of July 1, 2026."
    else:
        rate_sentence = f"The {name} state sales tax rate is {sr}%. Local rates average {lr}%, for a combined average of {cr}%."
        faq1 = f"The statewide rate is {sr}%. With local taxes included, the average combined rate is {cr}% as of July 1, 2026, though your exact rate depends on your city and county."

    notes = []
    if s["mandatoryLocal"]:
        notes.append(f"The {sr}% state rate shown includes a mandatory statewide local rate of {fmt_rate(s['mandatoryLocal'])}%.")
    # (Hawaii's GET note now lives in rate_sentence itself, not a trailing note)
    # (New Jersey's UEZ caveat now lives in its rate_sentence branch)
    notes_html = (' ' + " ".join(notes)) if notes else ""

    rows = "\n".join(
        f"          <tr><td>{money(a)}</td><td>{money(a*combined/100)}</td><td>{money(a*(1+combined/100))}</td></tr>"
        for a in (100, 500, 1000)
    )

    faq2 = f"At the average combined rate of {cr}%, sales tax on a $100 purchase in {name} is {money(100*combined/100)}, for a total of {money(100*(1+combined/100))}."
    if s["uez"]:
        faq2 = f"At the standard statewide rate of {sr}%, sales tax on a $100 purchase in {name} is {money(100*combined/100)}, for a total of {money(100*(1+combined/100))}. Qualifying urban enterprise zone sellers charge half that rate."
    if s["get"]:
        faq2 = f"The combined GET-plus-surcharge burden of {cr}% on a $100 purchase is {money(100*combined/100)}, a total of {money(100*(1+combined/100))}; sellers passing on the tax at the lawful maximum of 4.712% would charge $104.71."
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
    if len(title) > 60:  # District of Columbia / Massachusetts overflow the suffix
        title = f"{name} Sales Tax Calculator 2026 ({cr}%)"

    # short desc branches (<=155 even for District of Columbia; the old
    # template concatenated rate_sentence and ran 192-258 chars sitewide)
    if s["none"] and s["local"] > 0:
        desc = f"Free {name} sales tax calculator, July 2026 rates. No statewide tax; local rates average {lr}%. Add tax to a price or work backwards from a total."
    elif s["none"]:
        desc = f"Free {name} sales tax calculator. {name} has no state or local sales tax; the tag price is what you pay. Reverse mode included."
    elif s["get"]:
        desc = f"Free {name} sales tax calculator, July 2026 rates: {sr}% GET plus {lr}% average local, about {cr}% at the register. Reverse mode included."
    elif s["local"] == 0:
        desc = f"Free {name} sales tax calculator, July 2026 rates: {sr}% statewide with no local add-ons. Add tax to a price or work backwards from a total."
    else:
        desc = f"Free {name} sales tax calculator, July 2026 rates: state {sr}%, average local {lr}%. Add tax to a price or work backwards from a total."

    page = index_template
    page = page.replace("<title>Sales Tax Calculator 2026 - All 50 States &amp; Local Rates</title>", f"<title>{title}</title>")
    page = page.replace('content="Free sales tax calculator with July 2026 rates for all 50 states and DC. Add tax to a price or work backwards from a total, with state and average local rates built in."', f'content="{desc}"')
    page = page.replace('href="https://salestaxcalculatorhq.com/" />', f'href="{DOMAIN}/{clean}" />')
    page = page.replace('content="Sales Tax Calculator 2026 - All 50 States &amp; Local Rates" />', f'content="{title}" />')
    page = page.replace('content="https://salestaxcalculatorhq.com/" />', f'content="{DOMAIN}/{clean}" />')
    page = page.replace('<h1 id="pageH1">Sales Tax Calculator</h1>', f'<h1 id="pageH1">{name} Sales Tax Calculator</h1>')
    page = page.replace('<p class="subtitle">2026 rates for every state, plus local taxes.</p>', f'<p class="subtitle">2026 rates: state {sr}%, average local {lr}%.</p>' if not (s["none"] and s["local"]==0) else '<p class="subtitle">No sales tax. Lucky you.</p>')
    page = page.replace('<script src="script.js?v=2"></script>', f'<script>window.PRESET_STATE = "{code}";</script>\n  <script src="script.js?v=2"></script>')

    info = f'''    <section class="doc" style="max-width:760px;padding:26px 28px">
      <h2 style="font-size:1.05rem;font-weight:700;margin-bottom:10px">Sales tax in {name} (2026)</h2>
      <p style="font-size:0.94rem">{rate_sentence}{notes_html} Rates from the {TF_LINK}.</p>
      <div class="table-wrap">
      <table>
        <thead><tr><th>Purchase</th><th>Sales tax ({("avg " + cr) if not s["uez"] else sr}%)</th><th>Total</th></tr></thead>
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
      <p style="font-size:0.9rem;margin-top:10px"><a href="/">All states</a> · <a href="sales-tax-by-state">Rates by state table</a> · <a href="guide">How US sales tax works</a></p>
      <p style="font-size:0.9rem">More states: {sibling_links}</p>
    </section>
'''
    # swap the state-links section for the state info section, and add FAQ schema
    page = re.sub(r'    <section class="doc" style="max-width:760px;padding:26px 28px">\n      <h2[^>]*>Sales tax calculator by state</h2>.*?</section>\n', info, page, flags=re.S)
    page = page.replace("  </script>\n</head>", f'  </script>\n  <script type="application/ld+json">\n  {faq_schema}\n  </script>\n</head>')
    write_if_changed(PUB / fname, page)

# ---- /reverse-sales-tax-calculator (Phase 3, audit 2026-07-26) ----
# The top cluster gap: a dedicated tool page for "reverse sales tax
# calculator" queries, opening in Reverse mode via the PRESET_MODE hook.
# Owns the deep reverse-math explainer, ending the guide/faq overlap.
def reverse_page():
    slug = "reverse-sales-tax-calculator"
    title = "Reverse Sales Tax Calculator - Price Before Tax (2026)"
    desc = ("Work backwards from a receipt total: divide by 1 plus the rate to get the "
            "pre-tax price. Free reverse sales tax calculator with 2026 state rates.")

    rev_rows = "\n".join(
        f"          <tr><td>{r}%</td><td>{money(100 / (1 + r / 100))}</td><td>{money(100 - 100 / (1 + r / 100))}</td></tr>"
        for r in (5, 6, 7, 8, 9, 10)
    )

    faqs = [
        ("How do I calculate sales tax backwards from a total?",
         "Divide the total by 1 plus the tax rate written as a decimal. For a $216.40 receipt at "
         "8.2%, divide by 1.082: the pre-tax price is $200.00 and the tax is $16.40. The "
         "calculator above does this for any total, state, and local rate."),
        ("Why can't I just multiply the total by the tax rate?",
         "Because tax was charged on the pre-tax price, not on the total. Multiplying $216.40 by "
         "8.2% gives $17.74, which overstates the real $16.40 tax by $1.34. Dividing by 1.082 "
         "recovers the true split."),
        ("What is the reverse sales tax formula?",
         "Pre-tax price = total divided by (1 + rate as a decimal), and tax = total minus pre-tax "
         "price. At 7%, a $107.00 total is $100.00 plus $7.00 tax."),
    ]
    faq_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs],
    }, ensure_ascii=False)

    page = index_template
    page = page.replace("<title>Sales Tax Calculator 2026 - All 50 States &amp; Local Rates</title>", f"<title>{title}</title>")
    page = page.replace('content="Free sales tax calculator with July 2026 rates for all 50 states and DC. Add tax to a price or work backwards from a total."', f'content="{desc}"')
    page = page.replace('href="https://salestaxcalculatorhq.com/" />', f'href="{DOMAIN}/{slug}" />')
    page = page.replace('content="Sales Tax Calculator 2026 - All 50 States &amp; Local Rates" />', f'content="{title}" />')
    page = page.replace('content="https://salestaxcalculatorhq.com/" />', f'content="{DOMAIN}/{slug}" />')
    page = page.replace('<h1 id="pageH1">Sales Tax Calculator</h1>', '<h1 id="pageH1">Reverse Sales Tax Calculator</h1>')
    page = page.replace('<p class="subtitle">2026 rates for every state, plus local taxes.</p>', '<p class="subtitle">Enter a total; get the pre-tax price and the tax.</p>')
    page = page.replace('<script src="script.js?v=2"></script>', '<script>window.PRESET_MODE = "reverse";</script>\n  <script src="script.js?v=2"></script>')

    info = f'''    <section class="doc" style="max-width:760px;padding:26px 28px">
      <h2 style="font-size:1.05rem;font-weight:700;margin-bottom:10px">How reverse sales tax works</h2>
      <p style="font-size:0.94rem">A receipt total already includes tax, so you cannot get the tax
      back by multiplying the total by the rate; the tax was charged on the smaller pre-tax price.
      Divide instead: <strong>pre-tax price = total &divide; (1 + rate)</strong>. For a $216.40 total
      at a combined 8.2% rate, $216.40 &divide; 1.082 = $200.00, so the tax was $16.40. Multiplying
      the total would have claimed $17.74, overstating the tax by $1.34.</p>
      <div class="table-wrap">
      <table>
        <thead><tr><th>Rate</th><th>Pre-tax price of a $100 total</th><th>Tax inside it</th></tr></thead>
        <tbody>
{rev_rows}
        </tbody>
      </table>
      </div>
      <p style="font-size:0.94rem">The calculator above is preset to reverse mode: pick your state
      (and your city's exact local rate if you know it), enter the receipt total, and it splits the
      pre-tax price from the tax for you. Bookkeepers use this to separate deductible tax from
      expense amounts; shoppers use it to check a receipt.</p>
      <div class="faq">
        {"".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faqs)}
      </div>
      <p style="font-size:0.9rem;margin-top:10px"><a href="/">Forward calculator</a> · <a href="sales-tax-by-state">Rates by state table</a> · <a href="guide">How US sales tax works</a></p>
    </section>
'''
    page = re.sub(r'    <section class="doc" style="max-width:760px;padding:26px 28px">\n      <h2[^>]*>Sales tax calculator by state</h2>.*?</section>\n', info, page, flags=re.S)
    page = page.replace("  </script>\n</head>", f'  </script>\n  <script type="application/ld+json">\n  {faq_schema}\n  </script>\n</head>')
    write_if_changed(PUB / (slug + ".html"), page)

reverse_page()

# ---- machine-readable rates file (CC BY 4.0, from the same STATES table) ----
rates_data = {
    "about": "US state and local sales tax rates used by salestaxcalculatorhq.com. State rate, average local rate, and combined rate for all 50 states and DC.",
    "asOf": "2026-07-01",
    "source": "Tax Foundation, State and Local Sales Tax Rates, Midyear 2026",
    "sourceUrl": TF_URL,
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": "Sales Tax Calculator HQ",
    "states": {
        code: {
            "name": s["name"],
            "stateRate": s["state"],
            "avgLocalRate": s["local"],
            "combinedAvgRate": (s["tfCombined"] if s["tfCombined"]
                                else round(s["state"] + s["local"], 3)),
            **({"noSalesTax": True} if s["none"] and s["local"] == 0 else {}),
            **({"noStatewideSalesTax": True} if s["none"] else {}),
            **({"avgBelowStateRateNote":
                "Urban enterprise zones charge half the state rate on qualifying purchases, pulling the population-weighted average combined rate below the state rate."}
               if s["tfCombined"] else {}),
            **({"generalExciseTax": True} if s["get"] else {}),
            **({"stateRateIncludesMandatoryLocal": s["mandatoryLocal"]} if s["mandatoryLocal"] else {}),
        }
        for code, s in sorted(states.items())
    },
}
(PUB / "data").mkdir(exist_ok=True)
write_if_changed(PUB / "data" / "sales-tax-rates.json", json.dumps(rates_data, indent=1) + "\n")

# ---- sitemap ----
urls = [f"{DOMAIN}/", f"{DOMAIN}/guide", f"{DOMAIN}/sales-tax-by-state", f"{DOMAIN}/reverse-sales-tax-calculator", f"{DOMAIN}/faq", f"{DOMAIN}/about", f"{DOMAIN}/privacy"]
urls += [f"{DOMAIN}/{s['slug']}-sales-tax-calculator" for s in sorted(states.values(), key=lambda x: x["name"])]
# lastmod from real file mtimes (honest via write_if_changed above);
# deprecated priority/changefreq dropped (audit 2026-07-26)
import datetime, os

def lastmod(u):
    rel = u.replace(DOMAIN, "").strip("/") or "index"
    return datetime.date.fromtimestamp(os.path.getmtime(PUB / (rel + ".html"))).isoformat()

entries = "\n".join(
    f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{lastmod(u)}</lastmod>\n  </url>"
    for u in urls
)
write_if_changed(PUB / "sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n')

print(f"Generated {len(states)} state pages, sitemap ({len(urls)} URLs), and index links block.")
