# Angsuman Das: projects dashboard

Live at **https://angsumandas.angsumi.online/**: every research and coding project explained in plain words, with what is done, what comes next and what each could become, and a year of GitHub activity.

- `projects.json`: the plain-language layer. Edit this to change what the page says.
- `build.py`: merges it with live GitHub data (languages, dates, commit activity) into `index.html`. Standard library only.
- `template.html`, `style.css`: page and design (light and dark mode).
- `.github/workflows/refresh.yml`: rebuilds every Monday and whenever the files above change.

Run locally: `GITHUB_TOKEN=$(gh auth token) python3 build.py`.
