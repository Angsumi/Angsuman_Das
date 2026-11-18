"""Render index.html from projects.json + live GitHub data. Standard library only.

  GITHUB_TOKEN=... python3 build.py      # token optional locally, set automatically in Actions
"""
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
import json, os, time, urllib.request

OWNER = 'Angsumi'
ROOT = Path(__file__).parent
SITE = 'https://angsumandas.angsumi.online/'
STAGE_HELP = ['set up', 'data or code in progress', 'results exist', 'public and usable', 'peer-reviewed or delivered']


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


def ago(stamp, today):
    days = (today - datetime.fromisoformat(stamp.replace('Z', '+00:00')).date()).days
    if days < 1: return 'today'
    if days < 30: return f'{days} d ago'
    if days < 365: return f'{days // 30} mo ago'
    return f'{days // 365} y ago'


def ring(done, total=5, size=20, segmented=True):
    """Circular progress: segmented for project stage, continuous for shares."""
    r = size / 2 - 2; c = 2 * 3.14159 * r; h = size / 2
    if not segmented:
        return (f'<svg class="ring" viewBox="0 0 {size} {size}" aria-hidden="true"><circle class="track" cx="{h}" cy="{h}" r="{r}"/>'
                f'<circle class="fill" cx="{h}" cy="{h}" r="{r}" stroke-dasharray="{done / total * c:.2f} {c:.2f}"/></svg>')
    arc, gap = c / total, 2
    segs = ''.join(f'<circle class="{"fill" if i < done else "track"}" cx="{h}" cy="{h}" r="{r}" stroke-dasharray="{arc - gap:.2f} {c - arc + gap:.2f}" stroke-dashoffset="{-i * arc:.2f}"/>' for i in range(total))
    return f'<svg class="ring" viewBox="0 0 {size} {size}" aria-hidden="true">{segs}</svg>'


def months_chart(days, today):
    """Twelve bars: commits per calendar month, oldest on the left."""
    keys = []
    y, m = today.year, today.month
    for _ in range(12):
        keys.append((y, m)); m -= 1
        if m == 0: y, m = y - 1, 12
    keys.reverse()
    totals = {k: 0 for k in keys}
    for d, n in days.items():
        if (d.year, d.month) in totals: totals[(d.year, d.month)] += n
    peak = max(totals.values()) or 1
    bars = ''.join(f'<g><rect x="{i * 30 + 4}" y="{70 - totals[k] / peak * 62:.1f}" width="22" height="{max(totals[k] / peak * 62, 1.5):.1f}" rx="3"><title>{totals[k]} commits in {date(k[0], k[1], 1):%B %Y}</title></rect>'
                   f'<text x="{i * 30 + 15}" y="86">{date(k[0], k[1], 1):%b}</text></g>' for i, k in enumerate(keys))
    return f'<svg class="months" viewBox="0 0 360 90" role="img" aria-label="Commits per month over the last year">{bars}</svg>', sum(totals.values())


def build():
    data = json.loads((ROOT / 'projects.json').read_text())
    cats, stages, today = data['categories'], data['stages'], date.today()
    repos = {r['name']: r for r in api(f'users/{OWNER}/repos?per_page=100&type=owner') if not r['private']}
    projects = [p for p in data['projects'] if p['repo'] in repos]
    days, langs_used, rows, board = {}, set(), {c: [] for c in cats}, {i: [] for i in range(1, 6)}
    for p in projects:
        r = repos[p['repo']]
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
        if r.get('homepage'): links.append(f'<a class="open" href="{escape(r["homepage"])}">Open</a>')
        if p.get('doi'): links.append(f'<a href="https://doi.org/{p["doi"]}">DOI</a>')
        links.append(f'<a href="{r["html_url"]}">Code</a>')
        anchor = 'p-' + p['repo'].lower().replace('.', '-').replace('_', '-')
        c, s = p['category'], p['stage']
        board[s].append(f'<li class="{c}"><a href="#{anchor}">{escape(p["title"])}</a></li>')
        rows[c].append(f'''<article class="row {c}" id="{anchor}">
<div class="what"><div class="head">{ring(s)}<h3>{escape(p["title"])}</h3></div>
<p>{escape(p["plain"])}</p>
<p class="meta"><span class="st">{stages[s - 1]}</span> · {escape(p["status"])} · {escape(" · ".join(main_langs) or "—")} · updated {ago(r["pushed_at"], today)}</p>
<p class="links">{"".join(links)}</p></div>
<div class="cell done"><span class="lbl">Done</span>{escape(p["done"])}</div>
<div class="cell next"><span class="lbl">Next</span>{escape(p["next"])}</div>
<div class="cell could"><span class="lbl">Could become</span>{escape(p["could"])}</div>
</article>''')
    n = len(projects)
    public = sum(1 for p in projects if p['stage'] >= 4)
    live = sum(1 for p in projects if repos[p['repo']].get('homepage'))
    research = sum(1 for p in projects if p['category'] == 'research')
    drafts = sum(1 for p in projects if p['status'] == 'Manuscript draft')
    dois = sum(1 for p in projects if p.get('doi'))
    chart, commits = months_chart(days, today)
    board_html = ''.join(f'<div class="col"><h3>{ring(i)}<span>{stages[i - 1]}</span></h3><p>{STAGE_HELP[i - 1]}</p><ol>{"".join(board[i])}</ol></div>' for i in range(1, 6))
    groups = ''.join(f'<section class="group {c}" id="{c}"><header><h2>{cats[c]["label"]}</h2><p>{cats[c]["blurb"]}</p></header>'
                     f'<div class="cols" aria-hidden="true"><span>What it is</span><span>Done</span><span>Next</span><span>Could become</span></div>{"".join(rows[c])}</section>' for c in cats if rows[c])
    tries = ''.join(f'<a class="try" href="{u}"><b>{escape(t)}</b><span>{escape(s)}</span></a>' for t, u, s in data['try'])
    road = ''.join(f'<div class="phase"><h3>{k}</h3><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in v) + '</ul></div>' for k, v in data['roadmap'].items())
    person = {'@context': 'https://schema.org', '@type': 'ProfilePage', 'url': SITE, 'dateModified': today.isoformat(),
              'mainEntity': {'@type': 'Person', '@id': 'https://angsumi.online/#person', 'name': 'Angsuman Das',
                             'url': 'https://angsumi.online/cv/', 'affiliation': 'Pachhunga University College, Mizoram University',
                             'sameAs': ['https://orcid.org/0000-0001-8146-7697', 'https://www.linkedin.com/in/angsumi/',
                                        'https://www.researchgate.net/profile/Angsuman-Das-2', 'https://github.com/Angsumi', 'https://x.com/angsumi_online']}}
    values = {'SCHEMA': json.dumps(person), 'N': str(n), 'PUBLIC': str(public), 'PUBLIC_RING': ring(public, n, 64, False),
              'LIVE': str(live), 'RESEARCH': str(research), 'BUILT': str(n - research), 'DRAFTS': str(drafts), 'DOIS': str(dois),
              'LANGS': str(len(langs_used)), 'COMMITS': f'{commits:,}', 'CHART': chart, 'BOARD': board_html, 'GROUPS': groups,
              'TRY': tries, 'ROADMAP': road, 'DATE': f'{today:%d %B %Y}', 'ISO': today.isoformat()}
    html = (ROOT / 'template.html').read_text()
    for key, value in values.items():
        html = html.replace('{{' + key + '}}', value)
    (ROOT / 'index.html').write_text(html)
    print(f'index.html: {n} projects, {public} public, {commits} commits in 12 months, {len(langs_used)} languages')


if __name__ == '__main__':
    build()
