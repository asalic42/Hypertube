import re

_YEAR = re.compile(r"(?<!\d)(18[89]\d|19\d\d|20\d\d)(?!\d)")
_BRACKETED = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")
_NOISE = re.compile(
    r"\b(full movie|full film|hd|hq|dvdrip|dvd|720p|1080p|480p|x264|h264|xvid|divx|"
    r"public domain|remastered|restored|colorized|widescreen)\b",
    re.IGNORECASE,
)


def clean_title(raw_title, year=None):
    """
    Split a messy source title ("Night of the Living Dead (1968) [HD]") into a
    display title and a production year.
    """
    raw_title = (raw_title or "").replace("_", " ").strip()
    if year is None:
        # Years are usually appended, so the last one is the production year.
        matches = _YEAR.findall(raw_title)
        year = int(matches[-1]) if matches else None

    title = _BRACKETED.sub(" ", raw_title)
    title = _NOISE.sub(" ", title)
    if year is not None:
        without_year = re.sub(rf"(?<!\d){year}(?!\d)", " ", title)
        # Keep the year when it is the title itself ("1984").
        if re.search(r"[A-Za-z0-9]", without_year):
            title = without_year
    title = re.sub(r"\s+", " ", title).strip(" -–:|,.")
    return (title or raw_title)[:512], year


def parse_year(value):
    """Extract a plausible production year from a loosely typed source field."""
    match = _YEAR.search(str(value or ""))
    return int(match.group(1)) if match else None
