"""Render index.html from projects.json + icons.json + live GitHub data. Standard library only.

  GITHUB_TOKEN=... python3 build.py      # token optional locally, set automatically in Actions
"""
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
import json, os, time, urllib.request

OWNER = 'Angsumi'
ROOT = Path(__file__).parent
SITE = 'https://angsumandas.angsumi.online/'
CAT_ICON = {'research': 'flask', 'learning': 'book-open', 'build': 'laptop-code'}


def api(path, tries=6):
    req = urllib.request.Request('https://api.github.com/' + path, headers={'Accept': 'application/vnd.github+json'})
    if os.environ.get('GITHUB_TOKEN'):
        req.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    for _ in range(tries):
        with urllib.request.urlopen(req) as r:
            if r.status != 202:  # 202: GitHub is still computing statistics
                return json.load(r)
        time.sleep(3)
    return []


def icon(name, cls='i'):
    return f'<svg class="{cls}" aria-hidden="true"><use href="#fa-{name}"/></svg>'


def sprite():
    icons = json.loads((ROOT / 'icons.json').read_text())
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">' +
            ''.join(f'<symbol id="fa-{k}" viewBox="{v[0]}"><path fill="currentColor" d="{v[1]}"/></symbol>' for k, v in icons.items() if not k.startswith('_')) + '</svg>')


def ago(stamp, today):
    days = (today - datetime.fromisoformat(stamp.replace('Z', '+00:00')).date()).days
    if days < 1: return 'today'
    if days < 30: return f'{days} d ago'
    if days < 365: return f'{days // 30} mo ago'
    return f'{days // 365} y ago'


def ring(done, total, size=56):
    r = size / 2 - 4; c = 2 * 3.14159 * r; h = size / 2
    return (f'<svg class="ring" viewBox="0 0 {size} {size}" aria-hidden="true"><circle class="track" cx="{h}" cy="{h}" r="{r}"/>'
            f'<circle class="fill" cx="{h}" cy="{h}" r="{r}" stroke-dasharray="{done / total * c:.2f} {c:.2f}"/></svg>')


def tracker(steps, done):
    """Step tracker: green tick for each completed step, open circle for the rest."""
    items = ''.join(f'<li class="{"ok" if i < done else "todo"}">' + (icon('circle-check') if i < done else '<i></i>') + f'<span>{s}</span></li>'
                    for i, s in enumerate(steps))
    return f'<ol class="track" aria-label="{done} of {len(steps)} steps done: {", ".join(steps[:done]) or "none yet"}">{items}</ol>'


def months_chart(days, today):
    keys, (y, m) = [], (today.year, today.month)
    for _ in range(12):
        keys.append((y, m)); m -= 1
        if m == 0: y, m = y - 1, 12
    keys.reverse()
    totals = {k: 0 for k in keys}
    for d, n in days.items():
        if (d.year, d.month) in totals: totals[(d.year, d.month)] += n
    peak = max(totals.values()) or 1
    bars = ''.join(f'<rect x="{i * 30 + 6}" y="{60 - totals[k] / peak * 54:.1f}" width="18" height="{max(totals[k] / peak * 54, 1.5):.1f}" rx="2"><title>{totals[k]} commits in {date(k[0], k[1], 1):%B %Y}</title></rect>'
                   f'<text x="{i * 30 + 15}" y="74">{date(k[0], k[1], 1):%b}</text>' for i, k in enumerate(keys))
    return f'<svg class="months" viewBox="0 0 360 78" role="img" aria-label="Commits per month over the last year">{bars}</svg>', sum(totals.values())


def build():
    data = json.loads((ROOT / 'projects.json').read_text())
    cats, tracks, today = data['categories'], data['tracks'], date.today()
    repos = {r['name']: r for r in api(f'users/{OWNER}/repos?per_page=100&type=owner') if not r['private']}
    projects = [p for p in data['projects'] if p['repo'] in repos]
    days, langs_used = {}, set()
    rows = {c: [] for c in cats}
    board = {t: {i: [] for i in range(1, len(s) + 1)} for t, s in tracks.items()}
    for p in projects:
        r = repos[p['repo']]
        track = 'research' if p['category'] == 'research' else 'build'
        steps, s, c = tracks[track], p['stage'], p['category']
        langs = api(f'repos/{OWNER}/{p["repo"]}/languages') or {}
        total = sum(langs.values()) or 1
        main_langs = [k for k, v in sorted(langs.items(), key=lambda kv: -kv[1]) if v / total >= .05][:3]
        langs_used.update(main_langs)
        for week in api(f'repos/{OWNER}/{p["repo"]}/stats/commit_activity') or []:
            for i, n in enumerate(week['days']):
                if n:
                    d = datetime.fromtimestamp(week['week'], timezone.utc).date() + timedelta(days=i)
                    days[d] = days.get(d, 0) + n
        links = []
        if r.get('homepage'): links.append(f'<a class="open" href="{escape(r["homepage"])}">{icon("arrow-up-right-from-square")}Open</a>')
        if p.get('pdf'): links.append(f'<a href="{p["pdf"]}">{icon("file-pdf")}PDF</a>')
        if p.get('doi'): links.append(f'<a href="https://doi.org/{p["doi"]}">{icon("link")}DOI</a>')
        links.append(f'<a href="{r["html_url"]}">{icon("github")}Code</a>')
        anchor = 'p-' + p['repo'].lower().replace('.', '-').replace('_', '-')
        board[track][s].append(f'<li class="{c}"><a href="#{anchor}">{escape(p["title"])}</a></li>')
        badge = f'<span class="badge {"pub" if p["status"] == "Published" else ""}">{icon("circle-check") if p["status"] == "Published" else ""}{escape(p["status"])}</span>'
        rows[c].append(f'''<article class="row {c}" id="{anchor}">
<div class="what"><h3>{escape(p["title"])}{badge}</h3><p>{escape(p["plain"])}</p>{tracker(steps, s)}
<p class="meta">{escape(" · ".join(main_langs) or "—")} · updated {ago(r["pushed_at"], today)}</p><p class="links">{"".join(links)}</p></div>
<div class="cell done"><span class="lbl">Done</span>{escape(p["done"])}</div>
<div class="cell next"><span class="lbl">Next</span>{escape(p["next"])}</div>
<div class="cell could"><span class="lbl">Could become</span>{escape(p["could"])}</div>
</article>''')
    n = len(projects)
    ready = sum(1 for p in projects if p['stage'] >= 4)
    live = sum(1 for p in projects if repos[p['repo']].get('homepage'))
    research = sum(1 for p in projects if p['category'] == 'research')
    pubs = sum(1 for p in projects if p['status'] == 'Published')
    drafts = sum(1 for p in projects if p['status'] == 'Manuscript draft')
    submitted = sum(1 for p in projects if p['status'] == 'Submitted')
    chart, commits = months_chart(days, today)

    def board_html(t, label):
        cols = ''.join(f'<div class="col"><h4><b>{i}</b>{step}</h4><ol>{"".join(board[t][i])}</ol></div>'
                       for i, step in enumerate(tracks[t], 1))
        return f'<div class="pipe"><h3>{label}</h3><div class="stages s{len(tracks[t])}">{cols}</div></div>'

    groups = ''.join(f'<section class="group {c}" id="{c}"><header><h2>{icon(CAT_ICON[c])}{cats[c]["label"]}</h2><p>{cats[c]["blurb"]}</p></header>'
                     f'<div class="cols" aria-hidden="true"><span>What it is · progress</span><span>Done</span><span>Next</span><span>Could become</span></div>{"".join(rows[c])}</section>' for c in cats if rows[c])
    tries = ''.join(f'<a class="try" href="{u}"><b>{escape(t)}{icon("arrow-up-right-from-square")}</b><span>{escape(s)}</span></a>' for t, u, s in data['try'])
    road = ''.join(f'<div class="phase"><h3>{k}</h3><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in v) + '</ul></div>' for k, v in data['roadmap'].items())
    person = {'@context': 'https://schema.org', '@type': 'ProfilePage', 'url': SITE, 'dateModified': today.isoformat(),
              'mainEntity': {'@type': 'Person', '@id': 'https://angsumi.online/#person', 'name': 'Angsuman Das',
                             'url': 'https://angsumi.online/cv/', 'affiliation': 'Pachhunga University College, Mizoram University',
                             'sameAs': ['https://orcid.org/0000-0001-8146-7697', 'https://www.linkedin.com/in/angsumi/',
                                        'https://www.researchgate.net/profile/Angsuman-Das-2', 'https://github.com/Angsumi', 'https://x.com/angsumi_online']}}
    values = {'SPRITE': sprite(), 'SCHEMA': json.dumps(person), 'N': str(n), 'READY': str(ready), 'READY_RING': ring(ready, n),
              'LIVE': str(live), 'RESEARCH': str(research), 'BUILT': str(n - research), 'PUBS': str(pubs), 'DRAFTS': str(drafts), 'SUBMITTED': str(submitted),
              'LANGS': str(len(langs_used)), 'COMMITS': f'{commits:,}', 'CHART': chart,
              'BOARD': board_html('research', 'Research') + board_html('build', 'Websites, tools &amp; courses'),
              'GROUPS': groups, 'TRY': tries, 'ROADMAP': road, 'DATE': f'{today:%d %B %Y}', 'ISO': today.isoformat()}
    html = (ROOT / 'template.html').read_text()
    for key, value in values.items():
        html = html.replace('{{' + key + '}}', value)
    (ROOT / 'index.html').write_text(html)
    build_repos(repos, today)
    print(f'index.html: {n} projects, {pubs} published, {ready} with results or live, {commits} commits in 12 months')


HIDDEN = {'document-library'}  # kept public by owner choice, but out of navigation


def build_repos(repos, today):
    """repos.html: every public repository, its GitHub Pages site (if any) and its code."""
    live, code = [], []
    for name, r in sorted(repos.items(), key=lambda kv: kv[0].lower()):
        if name in HIDDEN or r.get('fork'):
            continue
        site = r.get('homepage') or ''
        if r.get('has_pages') and not site:
            site = (api(f'repos/{OWNER}/{name}/pages') or {}).get('html_url', '').replace('http://', 'https://')
        links = (f'<a class="open" href="{escape(site)}">{icon("arrow-up-right-from-square")}{escape(site.split("//")[-1].rstrip("/"))}</a>' if site else '') + \
                f'<a href="{r["html_url"]}">{icon("github")}Code</a>'
        row = (f'<li class="repo"><div><h3>{escape(name)}</h3><p>{escape(r.get("description") or "")}</p></div>'
               f'<p class="meta">{escape(r.get("language") or "—")} · updated {ago(r["pushed_at"], today)}</p><p class="links">{links}</p></li>')
        (live if site else code).append(row)
    html = (ROOT / 'repos.template.html').read_text()
    for key, value in {'SPRITE': sprite(), 'LIVE': ''.join(live), 'CODE': ''.join(code), 'NLIVE': str(len(live)),
                       'NCODE': str(len(code)), 'N': str(len(live) + len(code)), 'DATE': f'{today:%d %B %Y}', 'ISO': today.isoformat()}.items():
        html = html.replace('{{' + key + '}}', value)
    (ROOT / 'repos.html').write_text(html)


if __name__ == '__main__':
    build()
