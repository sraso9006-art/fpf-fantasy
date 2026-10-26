# FPF Fantasy — Fantasy Points First

NFL usage trends, weekly start/sit rankings (Full and Half PPR), a player compare tool, and scheme profiles for every offense. Built from free nflverse data and rebuilt automatically every Tuesday and Friday morning.

---

## How it works

Every Tuesday and Friday morning, GitHub runs a small "robot" (called a **workflow**, in `.github/workflows/update-site.yml`) that:

1. Downloads the newest NFL data from nflverse
2. Runs the scripts in `scripts/` to calculate usage trends, projections and scheme profiles
3. Puts the numbers into the page design (`site/template.html`)
4. Publishes the finished page to your website

You don't have to do anything once it's set up. It's free.

| File | What it does |
|---|---|
| `scripts/build_data.py` | Usage trends and start/sit projections |
| `scripts/build_schemes.py` | Team scheme profiles |
| `scripts/assemble.py` | Puts the data into the page |
| `site/template.html` | The page design (colors, layout, text) |
| `.github/workflows/update-site.yml` | The weekly robot |

---

## Setup guide (about 30–60 minutes the first time)

### Step 1: Create the repository (the folder that holds your site)

1. Sign in to GitHub and click the **+** in the top right, then **New repository**.
2. Name it `fpf-fantasy`.
3. Choose **Public**. (Free GitHub accounts can only publish websites from public repositories.)
4. Click **Create repository**.

### Step 2: Upload the files

1. Unzip `fpf-fantasy.zip` on your computer.
2. On your new repository page, click **uploading an existing file** (or **Add file → Upload files**).
3. Open the unzipped `fpf-fantasy` folder and drag **everything inside it** onto the page: the `scripts` folder, the `site` folder, the `.github` folder, `README.md` and `.gitignore`.
4. Scroll down and click **Commit changes**.

**Important: the `.github` folder is hidden on Mac.** In Finder, press **Command + Shift + .** (period) to show hidden files, then drag it in. On Windows it shows normally.

**If the `.github` folder won't upload,** create the file by hand instead:
1. Click **Add file → Create new file**.
2. In the file name box, type exactly: `.github/workflows/update-site.yml`
3. Open `update-site.yml` from the zip in a text editor (TextEdit or Notepad), copy everything, and paste it in.
4. Click **Commit changes**.

### Step 3: Turn on GitHub Pages

1. In your repository, click **Settings** (top bar).
2. Click **Pages** in the left menu.
3. Under **Build and deployment → Source**, choose **GitHub Actions**.

### Step 4: Build the site for the first time

1. Click the **Actions** tab. If GitHub asks, click the green button to enable workflows.
2. Click **Update FPF Fantasy** on the left.
3. Click **Run workflow → Run workflow**.
4. Wait 2–4 minutes. A green check means it worked. A red X means something failed; click it to see which step.

Your site is now live at:

**`https://YOUR-USERNAME.github.io/fpf-fantasy/`**

(Replace YOUR-USERNAME with your GitHub username. The link also shows up in **Settings → Pages**.)

### Step 5 (optional): Use your own domain, like fpffantasy.com

1. Buy the domain from a registrar such as Namecheap, Porkbun or Cloudflare (about $10–15 a year).
2. In GitHub: **Settings → Pages → Custom domain**, type your domain (for example `fpffantasy.com`) and click **Save**.
3. At your registrar, open the domain's **DNS settings** and add these records:

   | Type | Host / Name | Value |
   |---|---|---|
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | CNAME | www | YOUR-USERNAME.github.io |

   These are GitHub's addresses. Double-check them in GitHub's help article "Managing a custom domain for your GitHub Pages site" in case they've changed.
4. Wait up to a few hours for DNS to update, then go back to **Settings → Pages** and check **Enforce HTTPS**.

---

## Keeping it running

- **It updates itself** every Tuesday and Friday morning. You can also update it anytime with **Actions → Update FPF Fantasy → Run workflow**.
- **Each new season:** open `.github/workflows/update-site.yml`, click the pencil icon, change `SEASON: "2026"` to the new year, and commit.
- **GitHub pauses scheduled workflows** on public repositories after 60 days with no changes to the repository. If updates stop, go to the Actions tab and re-enable the workflow, or make any small edit (like this README) to keep it active.
- **If a run fails,** the usual cause is the data source changing a column name. Open the failed run, copy the red error message, and ask Claude to fix the script.
- **Once this is running,** you can turn off the Claude scheduled task ("FPF Fantasy weekly update") so the two don't both do the same job.

## Changing the design or text

Edit `site/template.html` (click it, then the pencil icon), commit, and the site rebuilds automatically within a few minutes. Colors are at the top of the file, under `:root`.

---

## Data credits and licenses

- **nflverse** (play-by-play, snap counts, player stats, schedules and betting lines): licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). https://github.com/nflverse
- **FTN charting data** (play-action, motion, screens): provided by **FTN Data via nflverse**, licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). https://ftnfantasy.com/data
  - "SA" (share-alike) means anything built from FTN's data that you share publicly must be shared under the same license. The site's footer says this.
- Keep the credit line at the bottom of the page. It's what these licenses require.

Projections, rankings, tags and scheme labels are FPF Fantasy's own analysis.
