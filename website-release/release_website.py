# Bestand: release_website.py
# Locatie: Informatica-2627/website-release/release_website.py
# Doel: geplande weekreleases voor de publieke leerlingwebsite voorbereiden

import csv
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import yaml


# =========================================================
# CONFIGURATIE
# =========================================================

# Veiligheidsstand.
# True = alleen tonen wat er ZOU gebeuren.
DRY_RUN = False

# GitHub Pages-account waaronder de jaarwebsite wordt gepubliceerd.
GITHUB_PAGES_OWNER = "oncparkdreef"


# =========================================================
# PADEN
# =========================================================

SCRIPT_DIR = Path(__file__).parent

INFORMATICA_DIR = SCRIPT_DIR.parent

# Schooljaar volgt uit de naam van de jaarrepository,
# bijvoorbeeld Informatica-2627.
school_year_match = re.fullmatch(
    r"Informatica-(\d{4})",
    INFORMATICA_DIR.name,
    flags=re.IGNORECASE,
)

if school_year_match is None:
    raise RuntimeError(
        "Schooljaar kan niet uit de repositorynaam "
        "worden bepaald:\n"
        f"  {INFORMATICA_DIR.name}"
    )

SCHOOL_YEAR = school_year_match.group(1)

# Tijdelijke checkout van de officiële ONC-jaarbron.
SOURCE_REPO_ROOT = (
    Path(tempfile.gettempdir())
    / f"ONC-informatica-{SCHOOL_YEAR}-source"
)

SOURCE_REPO_URL = (
    f"git@github.com:"
    f"oncparkdreef/informatica-{SCHOOL_YEAR}-source.git"
)

SOURCE_SSH_KEY = (
    Path.home()
    / ".ssh"
    / f"onc_informatica_{SCHOOL_YEAR}_source"
)

# De huidige website-release werkt nog alleen met Module01.
SOURCE_ROOT = (
    SOURCE_REPO_ROOT
    / "module01"
)


# Tijdelijk samengesteld publicatiepakket.
# Dit is uitsluitend een testpakket en niet public-site.
PUBLICATION_PACKAGE_ROOT = (
    Path(tempfile.gettempdir())
    / "ONC-public-site-publication-package"
)

TARGET_ROOT = INFORMATICA_DIR / "public-site"

RELEASE_PLAN_FILE = (
    SCRIPT_DIR
    / "release-plans"
    / "website.csv"
)

RELEASE_WEBSITE_ROOT = (
    SCRIPT_DIR
    / "website"
)

RELEASE_404_IMAGE = (
    RELEASE_WEBSITE_ROOT
    / "assets"
    / "images"
    / "404.png"
)

RELEASE_404_OVERRIDE = (
    RELEASE_WEBSITE_ROOT
    / "overrides"
    / "404.html"
)

DOCS_DIR = SOURCE_ROOT / "docs"
DOCS_NL_DIR = DOCS_DIR / "nl"

UNDERSTANDING_ROOT = (
    DOCS_NL_DIR
    / "understanding"
)

UNDERSTANDING_CATALOG_FILE = (
    DOCS_NL_DIR
    / "data"
    / "understanding.yml"
)


# =========================================================
# OFFICIËLE ONC-BRON
# =========================================================

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def prepare_onc_source():
    """
    Haal de actuele officiële ONC-jaarbron op
    en geef de gebruikte commit terug.

    Iedere release begint met een verse tijdelijke
    checkout van de main-branch van de jaarbron.
    """

    if not SOURCE_SSH_KEY.is_file():
        raise RuntimeError(
            "Deploy key voor ONC-jaarbron niet gevonden:\n"
            f"  {SOURCE_SSH_KEY}"
        )

    if SOURCE_REPO_ROOT.exists():
        try:
            shutil.rmtree(
                SOURCE_REPO_ROOT,
                onexc=remove_readonly,
            )
        except OSError as error:
            raise RuntimeError(
                "Oude tijdelijke checkout van de ONC-jaarbron "
                "kon niet worden verwijderd:\n"
                f"  {SOURCE_REPO_ROOT}"
            ) from error

    environment = os.environ.copy()

    environment["GIT_SSH_COMMAND"] = (
        f'ssh -i "{SOURCE_SSH_KEY}" '
        "-o IdentitiesOnly=yes"
    )

    result = subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "clone",
            "--branch",
            "main",
            "--single-branch",
            "--depth",
            "1",
            SOURCE_REPO_URL,
            str(SOURCE_REPO_ROOT),
        ],
        text=True,
        capture_output=True,
        env=environment,
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Onbekende Git-fout."
        )

        raise RuntimeError(
            "ONC-jaarbron kon niet worden opgehaald:\n\n"
            f"{message}"
        )

    if not SOURCE_ROOT.is_dir():
        raise RuntimeError(
            "Modulebron niet gevonden:\n"
            f"  {SOURCE_ROOT}"
        )

    if not (SOURCE_ROOT / "mkdocs.yml").is_file():
        raise RuntimeError(
            "mkdocs.yml niet gevonden in modulebron:\n"
            f"  {SOURCE_ROOT}"
        )

    if not (SOURCE_ROOT / "docs").is_dir():
        raise RuntimeError(
            "docs-map niet gevonden in modulebron:\n"
            f"  {SOURCE_ROOT}"
        )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(SOURCE_REPO_ROOT),
            "rev-parse",
            "HEAD",
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Onbekende Git-fout."
        )

        raise RuntimeError(
            "Commit van ONC-jaarbron "
            "kon niet worden bepaald:\n\n"
            f"{message}"
        )

    return result.stdout.strip()


# =========================================================
# HULPFUNCTIES
# =========================================================

def parse_release_date(value):
    """
    Verwacht DD-MM-YYYY.
    Lege waarde betekent: nog niet gepland.
    """

    value = value.strip()

    if not value:
        return None

    return datetime.strptime(
        value,
        "%d-%m-%Y",
    ).date()


def is_true(value):
    return value.strip().lower() == "true"


def parse_slug(slug):
    """
    Vertaal bijvoorbeeld:

        m1-w06

    naar:

        module = 1
        week   = 06
    """

    match = re.fullmatch(
        r"m(\d+)-w(\d{2})",
        slug,
    )

    if not match:
        raise ValueError(
            f"Ongeldige slug: {slug}"
        )

    module = int(
        match.group(1)
    )

    week = match.group(2)

    return module, week


def get_week_paths(week):
    """
    Geef de bekende weekgebonden bronmappen
    van Module01 terug.
    """

    return {
        "week": (
            DOCS_NL_DIR
            / "weeks"
            / week
        ),
        "tsets": (
            DOCS_NL_DIR
            / "tsets"
            / week
        ),
        "psets": (
            DOCS_NL_DIR
            / "psets"
            / week
        ),
        "pdf_resources": (
            DOCS_NL_DIR
            / "pdf-resources"
            / week
        ),
    }


def load_understanding_catalog():
    """
    Lees de bestaande Understanding-catalogus
    van Module01.
    """

    if not UNDERSTANDING_CATALOG_FILE.is_file():
        raise RuntimeError(
            "Understanding-catalogus niet gevonden:\n"
            f"  {UNDERSTANDING_CATALOG_FILE}"
        )

    with UNDERSTANDING_CATALOG_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        catalog = yaml.safe_load(file)

    if not isinstance(catalog, dict):
        raise RuntimeError(
            "understanding.yml bevat geen geldige catalogus."
        )

    return catalog


def read_frontmatter(path):
    """
    Lees YAML-frontmatter uit een Markdown-bestand.
    """

    text = path.read_text(
        encoding="utf-8-sig"
    )

    match = re.match(
        r"\A---\s*\r?\n"
        r"(.*?)"
        r"\r?\n---\s*(?:\r?\n|\Z)",
        text,
        flags=re.DOTALL,
    )

    if not match:
        return {}, text

    metadata = yaml.safe_load(
        match.group(1)
    )

    if metadata is None:
        metadata = {}

    if not isinstance(metadata, dict):
        raise RuntimeError(
            f"Ongeldige frontmatter in:\n  {path}"
        )

    return metadata, text


def get_understanding_entry(item, catalog):
    """
    Zoek een Understanding-ID op in de bestaande
    understanding.yml-structuur.
    """

    try:
        domain, key = item.split(
            ".",
            1,
        )

        return catalog[
            domain
        ][
            key
        ]

    except (
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        raise RuntimeError(
            "Understanding-ID niet gevonden:\n"
            f"  {item}"
        ) from error


def get_understanding_paths(item, catalog):
    """
    Bepaal voor een Understanding-ID zowel:

    - de centrale _content-bron;
    - de zelfstandige wrapperpagina.

    Dit volgt dezelfde structuur als
    helpers/understanding.py van Module01.
    """

    entry = get_understanding_entry(
        item,
        catalog,
    )

    source_value = entry.get(
        "source"
    )

    if not source_value:
        raise RuntimeError(
            "Understanding-entry bevat geen source:\n"
            f"  {item}"
        )

    content_path = (
        DOCS_DIR
        / Path(source_value)
    )

    source_parts = list(
        Path(source_value).parts
    )

    if "_content" not in source_parts:
        raise RuntimeError(
            "Understanding-source bevat geen "
            f"_content-map:\n  {source_value}"
        )

    source_parts.remove(
        "_content"
    )

    wrapper_path = (
        DOCS_DIR
        / Path(*source_parts)
    )

    return content_path, wrapper_path


def get_content_path_for_wrapper(wrapper_path):
    """
    Zoek bij een zelfstandige Understanding-wrapper
    de bijbehorende _content-bron.

    Als die niet bestaat, geef None terug.
    """

    try:
        relative = wrapper_path.relative_to(
            UNDERSTANDING_ROOT.resolve()
        )
    except ValueError:
        return None

    content_path = (
        UNDERSTANDING_ROOT
        / "_content"
        / relative
    )

    if content_path.is_file():
        return content_path

    return None


def find_direct_understanding_links(
    source_path,
    text,
):
    """
    Zoek gewone Markdown-links naar .md-bestanden
    binnen docs/nl/understanding.
    """

    targets = set()

    link_pattern = re.compile(
        r"\]\(([^)]+?\.md(?:#[^)]+)?)\)"
    )

    for match in link_pattern.finditer(
        text
    ):
        target_value = match.group(1)

        target_value = target_value.split(
            "#",
            1,
        )[0]

        if (
            target_value.startswith("http://")
            or target_value.startswith("https://")
        ):
            continue

        target_path = (
            source_path.parent
            / target_value
        ).resolve()

        try:
            target_path.relative_to(
                UNDERSTANDING_ROOT.resolve()
            )
        except ValueError:
            continue

        targets.add(
            target_path
        )

    return targets


def collect_week_markdown_files(paths):
    """
    Verzamel alle Markdown-bestanden uit de
    weekgebonden bronmappen.
    """

    files = set()

    for path in paths.values():
        if not path.is_dir():
            continue

        for markdown_file in path.rglob(
            "*.md"
        ):
            files.add(
                markdown_file.resolve()
            )

    return files


def collect_understanding_dependencies(
    week_files,
    catalog,
):
    """
    Vind de Understanding-afhankelijkheden die
    rechtstreeks vanuit de weekbestanden nodig zijn.

    We volgen alleen:
    - understanding: [...] in frontmatter;
    - gewone Markdown-links naar Understanding.

    Links vanuit gevonden Understanding-pagina's
    worden bewust NIET verder gevolgd.
    """

    understanding_ids = set()
    direct_links = set()
    dependencies = set()

    for source_path in week_files:
        source_path = source_path.resolve()

        if not source_path.is_file():
            continue

        metadata, text = read_frontmatter(
            source_path
        )

        # ---------------------------------------------
        # Understanding via frontmatter
        # ---------------------------------------------

        items = metadata.get(
            "understanding",
            [],
        )

        if isinstance(
            items,
            str,
        ):
            items = [items]

        if items:
            if not isinstance(
                items,
                list,
            ):
                raise RuntimeError(
                    "understanding moet een lijst zijn in:\n"
                    f"  {source_path}"
                )

            for item in items:
                if not isinstance(
                    item,
                    str,
                ):
                    raise RuntimeError(
                        "Ongeldig Understanding-ID in:\n"
                        f"  {source_path}"
                    )

                understanding_ids.add(
                    item
                )

                content_path, wrapper_path = (
                    get_understanding_paths(
                        item,
                        catalog,
                    )
                )

                dependencies.add(
                    content_path.resolve()
                )

                dependencies.add(
                    wrapper_path.resolve()
                )

        # ---------------------------------------------
        # Directe Markdown-links naar Understanding
        # ---------------------------------------------

        for target in find_direct_understanding_links(
            source_path,
            text,
        ):
            target = target.resolve()

            direct_links.add(
                target
            )

            dependencies.add(
                target
            )

            content_path = (
                get_content_path_for_wrapper(
                    target
                )
            )

            if content_path is not None:
                dependencies.add(
                    content_path.resolve()
                )

    return {
        "ids": understanding_ids,
        "direct_links": direct_links,
        "files": dependencies,
    }


def display_relative(path):
    """
    Toon een bronpad relatief aan Module01.
    """

    try:
        return path.relative_to(
            SOURCE_ROOT.resolve()
        )
    except ValueError:
        return path


def get_publication_weeks(
    rows,
    today,
):
    """
    Bepaal welke weken in de publieke leerlingwebsite
    aanwezig moeten zijn.

    Een week wordt opgenomen als:
    - published = true;
    OF
    - ready = true en release_date <= vandaag.

    Een week met ready=false wordt nooit nieuw vrijgegeven.
    """

    included = []
    excluded = []

    for row in rows:
        slug = row["slug"].strip()

        try:
            module, week = parse_slug(
                slug
            )
        except ValueError:
            excluded.append(
                (slug, None, "ongeldige slug")
            )
            continue

        if module != 1:
            continue

        if is_true(
            row["published"]
        ):
            included.append(
                (slug, week, "al gepubliceerd")
            )
            continue

        if not is_true(
            row["ready"]
        ):
            excluded.append(
                (slug, week, "ready=false")
            )
            continue

        try:
            release_date = parse_release_date(
                row["release_date"]
            )
        except ValueError:
            excluded.append(
                (
                    slug,
                    week,
                    "ongeldige releasedatum",
                )
            )
            continue

        if release_date is None:
            excluded.append(
                (
                    slug,
                    week,
                    "geen releasedatum",
                )
            )
            continue

        if release_date > today:
            excluded.append(
                (
                    slug,
                    week,
                    f"release op {release_date}",
                )
            )
            continue

        included.append(
            (
                slug,
                week,
                "nieuwe release",
            )
        )

    return included, excluded


def show_publication_plan(
    rows,
    today,
    understanding_catalog,
):
    """
    Toon wat de publieke leerlingwebsite op basis van
    de officiële ONC-bron zou bevatten.

    Er wordt niets gekopieerd of gewijzigd.
    """

    included, excluded = get_publication_weeks(
        rows,
        today,
    )

    print()
    print("=" * 70)
    print("PUBLICATIEPLAN LEERLINGWEBSITE")
    print("=" * 70)
    print()

    print("Bron:")
    print(f"  {SOURCE_ROOT}")
    print()

    print("Algemene website:")
    print(
        "  volledige stabiele websiteconstructie "
        "(CSS, navigatie, guides, assets, helpers, templates, enz.)"
    )
    print()

    print("Weekinhoud die openbaar mag worden:")
    print()

    all_dependencies = set()

    if not included:
        print("  geen")

    for slug, week, reason in included:
        print(
            f"  {slug:<8} "
            f"week {week}  "
            f"({reason})"
        )

        paths = get_week_paths(
            week
        )

        for name, path in paths.items():
            status = (
                "gevonden"
                if path.is_dir()
                else "ONTBREEKT"
            )

            print(
                f"      {status:<10} "
                f"{display_relative(path)}"
            )

        week_files = collect_week_markdown_files(
            paths
        )

        dependencies = (
            collect_understanding_dependencies(
                week_files,
                understanding_catalog,
            )
        )

        all_dependencies.update(
            dependencies["files"]
        )

        print()

    print("Understanding die hiervoor nodig is:")
    print()

    if all_dependencies:
        for path in sorted(
            all_dependencies,
            key=lambda value: str(value),
        ):
            status = (
                "gevonden"
                if path.is_file()
                else "ONTBREEKT"
            )

            print(
                f"  {status:<10} "
                f"{display_relative(path)}"
            )
    else:
        print("  geen")

    print()
    print("Weekinhoud die NIET openbaar wordt:")
    print()

    if excluded:
        for slug, week, reason in excluded:
            week_text = (
                f"week {week}"
                if week is not None
                else ""
            )

            print(
                f"  {slug:<8} "
                f"{week_text:<8} "
                f"({reason})"
            )
    else:
        print("  geen")

    if DRY_RUN:
        print()
        print(
            "DRY RUN - er is niets gepubliceerd "
            "en public-site is niet gewijzigd."
        )
        print()


def prepare_publication_package(
    rows,
    today,
    understanding_catalog,
):
    """
    Maak een tijdelijk publicatiepakket op basis van
    de officiële ONC-bron.

    Het pakket bevat:
    - de stabiele algemene websiteconstructie;
    - alleen de weken die openbaar mogen zijn;
    - alleen de Understanding-bestanden die die weken nodig hebben.

    public-site wordt hierbij niet gewijzigd.
    """

    included, excluded = get_publication_weeks(
        rows,
        today,
    )

    included_weeks = {
        week
        for slug, week, reason in included
    }

    all_dependencies = set()

    for slug, week, reason in included:
        paths = get_week_paths(
            week
        )

        week_files = collect_week_markdown_files(
            paths
        )

        dependencies = (
            collect_understanding_dependencies(
                week_files,
                understanding_catalog,
            )
        )

        all_dependencies.update(
            dependencies["files"]
        )

    # Eerst controleren of alle benodigde
    # Understanding-bestanden werkelijk bestaan.
    missing_dependencies = [
        path
        for path in all_dependencies
        if not path.is_file()
    ]

    if missing_dependencies:
        lines = [
            "Publicatiepakket niet gemaakt.",
            "Benodigde Understanding-bestanden ontbreken:",
        ]

        for path in sorted(
            missing_dependencies,
            key=lambda value: str(value),
        ):
            lines.append(
                f"  {display_relative(path)}"
            )

        raise RuntimeError(
            "\n".join(lines)
        )

    # Iedere run begint met een volledig schoon pakket.
    if PUBLICATION_PACKAGE_ROOT.exists():
        shutil.rmtree(
            PUBLICATION_PACKAGE_ROOT
        )

    # Begin met de volledige officiële ONC-bron.
    shutil.copytree(
        SOURCE_ROOT,
        PUBLICATION_PACKAGE_ROOT,
    )

    # -----------------------------------------------------
    # Weekgebonden inhoud filteren
    # -----------------------------------------------------

    week_roots = [
        "weeks",
        "tsets",
        "psets",
        "pdf-resources",
    ]

    package_docs_nl = (
        PUBLICATION_PACKAGE_ROOT
        / "docs"
        / "nl"
    )

    for root_name in week_roots:
        root = (
            package_docs_nl
            / root_name
        )

        if not root.is_dir():
            continue

        for child in root.iterdir():
            if (
                child.is_dir()
                and re.fullmatch(
                    r"\d{2}",
                    child.name,
                )
                and child.name not in included_weeks
            ):
                shutil.rmtree(
                    child
                )

    # -----------------------------------------------------
    # Understanding filteren
    # -----------------------------------------------------

    package_understanding_root = (
        package_docs_nl
        / "understanding"
    )

    if package_understanding_root.exists():
        shutil.rmtree(
            package_understanding_root
        )

    package_understanding_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        UNDERSTANDING_ROOT / "index.md",
        package_understanding_root / "index.md",
    )

    for source_path in all_dependencies:
        relative_path = (
            source_path.resolve()
            .relative_to(
                SOURCE_ROOT.resolve()
            )
        )

        target_path = (
            PUBLICATION_PACKAGE_ROOT
            / relative_path
        )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source_path,
            target_path,
        )

    # -----------------------------------------------------
    # Eigen 404-pagina voor de publieke leerlingwebsite
    # -----------------------------------------------------

    release_files = [
        (
            RELEASE_404_IMAGE,
            PUBLICATION_PACKAGE_ROOT
            / "docs"
            / "assets"
            / "images"
            / "404.png",
        ),
        (
            RELEASE_404_OVERRIDE,
            PUBLICATION_PACKAGE_ROOT
            / "overrides"
            / "404.html",
        ),
    ]

    for source_path, target_path in release_files:
        if not source_path.is_file():
            raise RuntimeError(
                "404-bestand niet gevonden:\n"
                f"  {source_path}"
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source_path,
            target_path,
        )

    release_dates = {}

    for row in rows:
        slug = row["slug"].strip()

        try:
            module, week = parse_slug(slug)
        except ValueError:
            continue

        if module != 1:
            continue

        release_date = row["release_date"].strip()

        if not release_date:
            continue

        release_dates[str(int(week))] = release_date

    override_path = (
        PUBLICATION_PACKAGE_ROOT
        / "overrides"
        / "404.html"
    )

    override_text = override_path.read_text(
        encoding="utf-8"
    )

    override_text = override_text.replace(
        "__RELEASE_DATES__",
        json.dumps(
            release_dates,
            ensure_ascii=False,
        ),
    )

    override_path.write_text(
        override_text,
        encoding="utf-8",
    )

    return {
        "included": included,
        "excluded": excluded,
        "understanding_files": all_dependencies,
    }

def build_publication_package(module):
    """
    Bouw het tijdelijke publicatiepakket met
    de generieke informatica-exporter.

    Bij een fout stopt de release.
    public-site wordt hierbij niet gewijzigd.
    """

    module_name = f"module{module:02d}"

    publication_site_url = (
        f"https://{GITHUB_PAGES_OWNER}.github.io/"
        f"{INFORMATICA_DIR.name.lower()}/"
        f"{module_name}/"
    )

    output_root = (
        PUBLICATION_PACKAGE_ROOT
        / "site"
    )

    print()
    print("Publieke leerlingwebsite bouwen...")

    export_result = subprocess.run(
        [
            "informatica-export",
            "nl",
            "--source",
            str(PUBLICATION_PACKAGE_ROOT),
            "--output",
            str(output_root),
            "--site-url",
            publication_site_url,
        ],
    )

    if export_result.returncode != 0:
        raise RuntimeError(
            "Informatica-export is mislukt."
        )

def publish_website(module):
    """
    Vervang de gepubliceerde module door de zojuist
    gebouwde publieke leerlingwebsite.

    Er wordt eerst een volledige staging-kopie gemaakt.
    De bestaande module blijft als backup bestaan
    totdat de nieuwe versie succesvol op zijn plaats staat.
    """

    module_name = f"module{module:02d}"

    module_target_root = (
        TARGET_ROOT
        / module_name
    )

    site_root = (
        PUBLICATION_PACKAGE_ROOT
        / "site"
    )

    if not site_root.is_dir():
        raise RuntimeError(
            "Gebouwde website niet gevonden:\n"
            f"  {site_root}"
        )

    if not (site_root / "index.html").is_file():
        raise RuntimeError(
            "Gebouwde website bevat geen index.html:\n"
            f"  {site_root}"
        )

    site_404 = (
        site_root
        / "404.html"
    )

    if not site_404.is_file():
        raise RuntimeError(
            "Gebouwde 404-pagina niet gevonden:\n"
            f"  {site_404}"
        )    
    
    staging_root = (
        TARGET_ROOT
        / f"{module_name}-staging"
    )

    backup_root = (
        TARGET_ROOT
        / f"{module_name}-backup"
    )

    if backup_root.exists():
        raise RuntimeError(
            f"Bestaande backup voor {module_name} gevonden.\n"
            "Publicatie stopt om een mogelijke herstelkopie "
            "niet te overschrijven:\n"
            f"  {backup_root}"
        )

    if staging_root.exists():
        shutil.rmtree(
            staging_root
        )

    # Eerst de volledige nieuwe website klaarzetten.
    shutil.copytree(
        site_root,
        staging_root,
    )

    if module_target_root.exists():
        module_target_root.rename(
            backup_root
        )

    try:
        staging_root.rename(
            module_target_root
        )
    except Exception as error:
        # Als het vervangen mislukt, herstel dan
        # onmiddellijk de vorige modulewebsite.
        if (
            backup_root.exists()
            and not module_target_root.exists()
        ):
            backup_root.rename(
                module_target_root
            )

        raise RuntimeError(
            f"{module_name} kon niet veilig worden vervangen."
        ) from error

    shutil.copy2(
        site_404,
        TARGET_ROOT / "404.html",
    )

    # Pas na een geslaagde vervanging mag de backup weg.
    if backup_root.exists():
        shutil.rmtree(
            backup_root
        )

def mark_published(
    rows,
    fieldnames,
    slugs,
):
    """
    Markeer alleen de zojuist succesvol gepubliceerde
    weken als published=true in website.csv.
    """

    for row in rows:
        slug = row["slug"].strip()

        if slug in slugs:
            row["published"] = "true"

    temp_file = (
        RELEASE_PLAN_FILE.parent
        / "website.tmp.csv"
    )

    with temp_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    temp_file.replace(
        RELEASE_PLAN_FILE
    )

# =========================================================
# MAIN
# =========================================================

def main():
    try:
        source_commit = (
            prepare_onc_source()
        )
    except RuntimeError as error:
        print()
        print("RELEASE AFGEBROKEN")
        print()
        print(error)
        raise SystemExit(1)

    if not SOURCE_ROOT.is_dir():
        print("Fout: ONC-bron niet gevonden:")
        print(SOURCE_ROOT)
        raise SystemExit(1)

    if not RELEASE_PLAN_FILE.is_file():
        print("Fout: website.csv niet gevonden:")
        print(RELEASE_PLAN_FILE)
        raise SystemExit(1)

    try:
        understanding_catalog = (
            load_understanding_catalog()
        )
    except RuntimeError as error:
        print(f"Fout: {error}")
        raise SystemExit(1)

    with RELEASE_PLAN_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        print("Fout: website.csv bevat geen header.")
        raise SystemExit(1)

    required_columns = {
        "slug",
        "release_date",
        "ready",
        "published",
    }

    missing = required_columns - set(
        fieldnames
    )

    if missing:
        print(
            "Fout: ontbrekende kolommen "
            "in website.csv:"
        )

        for column in sorted(
            missing
        ):
            print(f"- {column}")

        raise SystemExit(1)

    today = date.today()
    found = False

    print()
    print("Website release")
    print(f"Datum:       {today.isoformat()}")
    print(f"Bron commit: {source_commit}")
    print(f"Bron repo:   {SOURCE_REPO_ROOT}")
    print(f"Schooljaar:  {SCHOOL_YEAR}")
    print(f"Modulebron:  {SOURCE_ROOT}")
    print(f"Doel:        {TARGET_ROOT}")
    print(f"Dry run:     {DRY_RUN}")
    print()

    for row in rows:
        slug = row["slug"].strip()

        if is_true(
            row["published"]
        ):
            continue

        if not is_true(
            row["ready"]
        ):
            continue

        try:
            release_date = parse_release_date(
                row["release_date"]
            )
        except ValueError:
            print(
                f"Fout datumformaat bij {slug}: "
                f"{row['release_date']}"
            )
            print()
            continue

        if release_date is None:
            continue

        if release_date > today:
            continue

        try:
            module, week = parse_slug(
                slug
            )
        except ValueError as error:
            print(f"Fout: {error}")
            print()
            continue

        # De huidige bronwebsite is Module01.
        if module != 1:
            continue

        found = True

        print(f"Release:      {slug}")
        print(f"Week:         {week}")
        print(f"Releasedatum: {release_date}")
        print()

        paths = get_week_paths(
            week
        )

        for name, path in paths.items():
            status = (
                "gevonden"
                if path.is_dir()
                else "ontbreekt"
            )

            print(
                f"  {name:<14} "
                f"{status:<10} "
                f"{path}"
            )

        week_files = (
            collect_week_markdown_files(
                paths
            )
        )

        print()
        print(
            "  Markdown-bestanden "
            f"in week: {len(week_files)}"
        )

        try:
            dependencies = (
                collect_understanding_dependencies(
                    week_files,
                    understanding_catalog,
                )
            )
        except RuntimeError as error:
            print()
            print(f"  FOUT: {error}")
            print()
            continue

        print()
        print("  Understanding-IDs:")

        if dependencies["ids"]:
            for item in sorted(
                dependencies["ids"]
            ):
                print(
                    f"    - {item}"
                )
        else:
            print("    geen")

        print()
        print(
            "  Directe Understanding-links:"
        )

        if dependencies["direct_links"]:
            for path in sorted(
                dependencies["direct_links"],
                key=lambda value: str(value),
            ):
                print(
                    "    - "
                    f"{display_relative(path)}"
                )
        else:
            print("    geen")

        print()
        print(
            "  Benodigde Understanding-bestanden:"
        )

        if dependencies["files"]:
            for path in sorted(
                dependencies["files"],
                key=lambda value: str(value),
            ):
                status = (
                    "gevonden"
                    if path.is_file()
                    else "ONTBREEKT"
                )

                print(
                    f"    {status:<10} "
                    f"{display_relative(path)}"
                )
        else:
            print("    geen")

        print()

        if DRY_RUN:
            print(
                "  DRY RUN - "
                "er wordt nog niets gekopieerd."
            )

        print()
        print("-" * 70)
        print()

    show_publication_plan(
        rows,
        today,
        understanding_catalog,
    )

    try:
        package = prepare_publication_package(
            rows,
            today,
            understanding_catalog,
        )
    except RuntimeError as error:
        print()
        print("PUBLICATIEPAKKET AFGEBROKEN")
        print()
        print(error)
        raise SystemExit(1)

    publication_modules = {
        parse_slug(slug)[0]
        for slug, week, reason in package["included"]
    }

    if len(publication_modules) != 1:
        print()
        print(
            "Fout: het publicatiepakket moet precies "
            "één module bevatten."
        )
        raise SystemExit(1)

    publication_module = next(
        iter(publication_modules)
    )

    try:
        build_publication_package(
            publication_module
        )
    except RuntimeError as error:
        print()
        print("BUILD AFGEBROKEN")
        print()
        print(error)
        raise SystemExit(1)

    if not DRY_RUN:
        try:
            publish_website(
                publication_module
            )
        except RuntimeError as error:
            print()
            print("PUBLICATIE AFGEBROKEN")
            print()
            print(error)
            raise SystemExit(1)

        newly_published_slugs = {
            slug
            for slug, week, reason in package["included"]
            if reason == "nieuwe release"
        }

        if newly_published_slugs:
            mark_published(
                rows,
                fieldnames,
                newly_published_slugs,
            )

    print()
    print("=" * 70)
    print("TIJDELIJK PUBLICATIEPAKKET")
    print("=" * 70)
    print()
    print(f"Locatie: {PUBLICATION_PACKAGE_ROOT}")
    print()
    print("Openbare weken:")

    for slug, week, reason in package["included"]:
        print(
            f"  {slug}  ({reason})"
        )

    print()
    if DRY_RUN:
        print(
            "public-site is niet gewijzigd."
        )
    else:
        print(
            "public-site is bijgewerkt."
        )
    print()

    if not found:
        print(
            "Geen nieuwe websiteweken klaar "
            "voor publicatie."
        )

    if DRY_RUN:
        print()
        print(
            "LET OP: DRY_RUN staat op True. "
            "public-site is niet gewijzigd."
        )


if __name__ == "__main__":
    main()

