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
LANG_COLORS = {'Python': '#3572A5', 'HTML': '#e34c26', 'JavaScript': '#f1e05a', 'TypeScript': '#3178c6',
               'Jupyter Notebook': '#DA5B0B', 'CSS': '#563d7c', 'R': '#198CE7', 'Shell': '#89e051',
               'TeX': '#3D6117', 'Dockerfile': '#384d54', 'Makefile': '#427819'}
def ring(done, total=5, size=18, segmented=True):
    """Circular progress: segmented for stages, continuous for shares."""
    r = size / 2 - 2; c = 2 * 3.14159 * r; h = size / 2
    if not segmented:
        return (f'<svg class="ring" width="{size}" height="{size}" aria-hidden="true"><circle class="track" cx="{h}" cy="{h}" r="{r}"/>'
                f'<circle class="seg" cx="{h}" cy="{h}" r="{r}" stroke-dasharray="{done / total * c:.2f} {c:.2f}"/></svg>')
    arc, gap = c / total, 2.2
    segs = ''.join(f'<circle class="{"seg" if i < done else "track"}" cx="{h}" cy="{h}" r="{r}" stroke-dasharray="{arc - gap:.2f} {c - arc + gap:.2f}" stroke-dashoffset="{-i * arc:.2f}"/>' for i in range(total))
    return f'<svg class="ring" width="{size}" height="{size}" aria-hidden="true">{segs}</svg>'




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
    if days < 30: return f'{days} day{"s" * (days > 1)} ago'
    if days < 365: return f'{days // 30} month{"s" * (days >= 60)} ago'
    return f'{days // 365} year{"s" * (days >= 730)} ago'


def langbar(langs):
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    bar = ''.join(f'<span style="width:{v / total * 100:.1f}%;background:{LANG_COLORS.get(k, "#8b949e")}" title="{escape(k)} {v / total:.0%}"></span>' for k, v in top)
    legend = ''.join(f'<li><i style="background:{LANG_COLORS.get(k, "#8b949e")}"></i>{escape(k)} <b>{v / total:.0%}</b></li>' for k, v in top)
    return f'<div class="langbar" aria-hidden="true">{bar}</div><ul class="langs">{legend}</ul>'


def heatmap(days):
    """GitHub-style contribution grid (53 weeks x 7 days) as inline SVG."""
    peak = max(days.values() or [1])
    start = date.today() - timedelta(days=date.today().weekday() + 1 + 52 * 7)
    cells, months, total = [], [], 0
    for w in range(53):
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            if day > date.today(): continue
            n = days.get(day, 0); total += n
            level = 0 if n == 0 else min(4, 1 + int(3 * n / peak))
            cells.append(f'<rect x="{w * 13}" y="{d * 13 + 16}" width="10" height="10" rx="2" class="l{level}"><title>{n} commit{"s" * (n != 1)} on {day:%d %b %Y}</title></rect>')
        first = start + timedelta(days=w * 7)
        if first.day <= 7:
            months.append(f'<text x="{w * 13}" y="10">{first:%b}</text>')
    svg = f'<svg viewBox="0 0 {53 * 13} {7 * 13 + 18}" role="img" aria-label="{total} commits in the last year">{"".join(months)}{"".join(cells)}</svg>'
    return svg, total


def build():
    data = json.loads((ROOT / 'projects.json').read_text())
    today = date.today()
    repos = {r['name']: r for r in api(f'users/{OWNER}/repos?per_page=100&type=owner') if not r['private']}
    days, lang_repos, cards, timeline = {}, {}, {}, []
    for p in data['projects']:
        r = repos.get(p['repo'])
        if not r: continue
        langs = api(f'repos/{OWNER}/{p["repo"]}/languages') or {}
        total = sum(langs.values()) or 1
        for k, v in langs.items():
            if v / total >= .05: lang_repos[k] = lang_repos.get(k, 0) + 1
        for week in api(f'repos/{OWNER}/{p["repo"]}/stats/commit_activity') or []:
            for i, n in enumerate(week['days']):
                if n:
                    d = datetime.fromtimestamp(week['week'], timezone.utc).date() + timedelta(days=i)
                    days[d] = days.get(d, 0) + n
        links = [f'<a href="{r["html_url"]}">Code</a>']
        if r.get('homepage'): links.append(f'<a href="{escape(r["homepage"])}">Open ↗</a>')
        if p.get('doi'): links.append(f'<a href="https://doi.org/{p["doi"]}">DOI</a>')
        cat = p['category']
        cards.setdefault(cat, []).append(f'''<article class="card {cat}" data-cat="{cat}">
<header><svg class="ico" aria-hidden="true"><use href="#i-{cat}"/></svg><a class="repo" href="{r["html_url"]}">{escape(p["repo"])}</a><span class="stage" title="Stage {p["stage"]} of 5: {data["stages"][p["stage"] - 1]}">{ring(p["stage"])}{escape(p["status"])}</span></header>
<h3>{escape(p["title"])}</h3><p class="plain">{escape(p["plain"])}</p>
<ul class="triad"><li><span class="k done">✓</span><span><em>done</em>{escape(p["done"])}</span></li><li><span class="k next">→</span><span><em>next</em>{escape(p["next"])}</span></li><li><span class="k could">✦</span><span><em>could become</em>{escape(p["could"])}</span></li></ul>
{langbar(langs) if langs else ''}<footer><span>Updated {ago(r["pushed_at"], today)}</span><nav>{" · ".join(links)}</nav></footer></article>''')
        timeline.append((r['created_at'][:10], p['title'], cat))
    grid, commits = heatmap(days)
    cats = data['categories']
    shown = sum(len(v) for v in cards.values())
    live = sum(1 for p in data['projects'] if p['repo'] in repos and repos[p['repo']].get('homepage'))
    timeline.sort()
    years = {}
    for d, t, c in timeline: years.setdefault(d[:4], []).append((d, t, c))
    tl = ''.join(f'<li><h3>{y}</h3><ul>' + ''.join(f'<li class="{c}"><time datetime="{d}">{date.fromisoformat(d):%b}</time>{escape(t)}</li>' for d, t, c in items) + '</ul></li>' for y, items in years.items())
    langs = ''.join(f'<li><i style="background:{LANG_COLORS.get(k, "#8b949e")}"></i>{escape(k)}<b>{n}</b></li>' for k, n in sorted(lang_repos.items(), key=lambda kv: -kv[1]))
    tries = ''.join(f'<a class="try" href="{u}"><strong>{escape(t)} ↗</strong><span>{escape(s)}</span></a>' for t, u, s in data['try'])
    road = ''.join(f'<section class="col"><h3>{k}</h3><ol>' + ''.join(f'<li>{escape(x)}</li>' for x in v) + '</ol></section>' for k, v in data['roadmap'].items())
    sections = ''.join(f'<section class="group" id="{c}"><h3 class="gh"><svg class="ico" aria-hidden="true"><use href="#i-{c}"/></svg>{cats[c]["label"]} <small>{cats[c]["blurb"]}</small></h3><div class="cards">{"".join(cards[c])}</div></section>' for c in cats if c in cards)
    count = {c: len(cards.get(c, [])) for c in cats}
    person = {'@context': 'https://schema.org', '@type': 'ProfilePage', 'url': SITE, 'dateModified': today.isoformat(),
              'mainEntity': {'@type': 'Person', '@id': 'https://angsumi.online/#person', 'name': 'Angsuman Das',
                             'url': 'https://angsumi.online/cv/', 'affiliation': 'Pachhunga University College, Mizoram University',
                             'sameAs': ['https://orcid.org/0000-0001-8146-7697', 'https://www.linkedin.com/in/angsumi/',
                                        'https://www.researchgate.net/profile/Angsuman-Das-2', 'https://github.com/Angsumi', 'https://x.com/angsumi_online']}}
    html = (ROOT / 'template.html').read_text()
    for key, value in {'SCHEMA': json.dumps(person), 'HEATMAP': grid, 'COMMITS': f'{commits:,}', 'SHOWN': str(shown), 'LIVE': str(live),
                       'RESEARCH': str(count['research']), 'R_RING': ring(count['research'], shown, 36, False), 'L_RING': ring(live, shown, 36, False),
                       'STAGES': ' → '.join(f'{ring(i + 1, 5, 14)} {s}' for i, s in enumerate(data['stages'])), 'BUILD': str(count['build'] + count['learning']), 'LANGCOUNT': str(len(lang_repos)),
                       'GROUPS': sections, 'TIMELINE': tl, 'LANGS': langs, 'TRY': tries, 'ROADMAP': road,
                       'DATE': f'{today:%d %B %Y}', 'ISO': today.isoformat()}.items():
        html = html.replace('{{' + key + '}}', value)
    (ROOT / 'index.html').write_text(html)
    print(f'index.html: {shown} projects, {commits} commits in 12 months, {len(lang_repos)} languages')


if __name__ == '__main__':
    build()
