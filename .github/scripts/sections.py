"""Which sections of a protocol have actually been written.

Gate 2 is the one gate where "the file changed" is a poor proxy for the work. A
lead can add a sentence to a 16-section protocol and the file differs from the
template — but the protocol is not drafted.

The OHDSI protocol template makes this checkable, because its sections ship
*empty*: a heading with nothing under it. So a section is written when its body
differs from the body the template shipped, which handles both the empty ones and
the couple that arrive with boilerplate (`Study Design` starts with a sentence
about CohortMethod).

Comparing against the template rather than merely "is it non-empty" matters: it
means boilerplate left untouched never counts as work.
"""

import re

__all__ = ["split_sections", "outstanding_sections", "normalise"]

# `# Outcomes {#outcomes}` and `## Analysis` alike. The trailing {#anchor} is
# pandoc's cross-reference syntax and is not part of the section's name.
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ANCHOR = re.compile(r"\s*\{[^}]*\}\s*$")


def normalise(title):
    """A heading's comparable name: anchors and markers stripped."""
    title = ANCHOR.sub("", title).strip()
    # `# (APPENDIX) Appendix {-}` and similar bookdown markers.
    title = re.sub(r"^\(\w+\)\s*", "", title).strip()
    return title


def split_sections(text):
    """{section name: body text} for every heading in the document.

    A section runs until the next heading at its own level or higher, so text a
    lead puts under a sub-heading of their own still belongs to the section
    above it. A protocol that opens `# Study Objectives` with `## Primary
    objective` and a paragraph has written its objectives, and has to count as
    having done so — cutting the section off at the first heading of any level
    made exactly that lead's work invisible.
    """
    sections, open_ = {}, []  # open_: [(name, level, body lines)]

    def close(level):
        while open_ and open_[-1][1] >= level:
            name, _, lines = open_.pop()
            sections[name] = (chr(10).join(lines)).strip()

    for line in (text or "").split(chr(10)):
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            close(level)
            for _, _, lines in open_:
                lines.append(line)
            open_.append((normalise(m.group(2)), level, []))
        else:
            for _, _, lines in open_:
                lines.append(line)
    close(0)
    return sections


def outstanding_sections(study_text, template_text, required):
    """Required sections that are missing, empty, or still the template's text.

    Returns them in the order given, so the comment reads in document order
    rather than whatever order a set iterates in.
    """
    study = split_sections(study_text)
    template = split_sections(template_text)

    out = []
    for name in required:
        key = normalise(name)
        if key not in study:
            out.append(name)          # heading deleted or renamed
            continue
        written = study[key]
        if not written:
            out.append(name)          # heading with nothing under it
            continue
        if written == template.get(key, ""):
            out.append(name)          # template boilerplate, untouched
    return out


def _self_test():
    # Shaped like the upstream protocol: the `##` sections sit under Research
    # Methods, not under Study Objectives.
    template = chr(10).join([
        "# Rationale and Background", "", "# Study Objectives", "",
        "# Research Methods", "",
        "## Study Design", "", "This study uses `CohortMethod`.", "",
        "## Data Sources", "", "# Outcomes {#outcomes}", "",
    ])
    study = chr(10).join([
        "# Rationale and Background", "",
        "Gestational diabetes is under-characterised in this population.", "",
        "# Study Objectives", "",
        "# Research Methods", "",
        "## Study Design", "", "This study uses `CohortMethod`.", "",
        "## Data Sources", "", "Three CDM databases.", "",
        "# Outcomes {#outcomes}", "",
    ])
    required = ["Rationale and Background", "Study Objectives", "Study Design",
                "Data Sources", "Outcomes"]
    got = outstanding_sections(study, template, required)

    # A lead's own sub-headings must not swallow the section above them.
    nested_template = chr(10).join([
        "# Study Objectives", "", "# Research Methods", "",
        "## Study Design", "", "## Data Sources", "",
    ])
    nested_study = chr(10).join([
        "# Study Objectives", "", "## Primary objective", "",
        "Characterise gestational diabetes.", "",
        "# Research Methods", "",
        "## Study Design", "", "### Cohorts", "", "Two cohorts.", "",
        "## Data Sources", "",
    ])
    nested = outstanding_sections(nested_study, nested_template,
                                  ["Study Objectives", "Study Design", "Data Sources"])

    checks = [
        ("text under an added sub-heading counts for the section above it",
         "Study Objectives" not in nested and "Study Design" not in nested),
        ("a section still ends at the next heading of its own level",
         "Data Sources" in nested),
        ("a written section is not outstanding",
         "Rationale and Background" not in got),
        ("an empty section is outstanding",
         "Study Objectives" in got),
        ("untouched template boilerplate is outstanding",
         "Study Design" in got),
        ("a filled section is not outstanding",
         "Data Sources" not in got),
        ("an anchored heading is matched by its plain name",
         "Outcomes" in got),
        ("order follows the required list",
         got == ["Study Objectives", "Study Design", "Outcomes"]),
        ("a missing heading counts as outstanding",
         outstanding_sections("", template, ["Study Objectives"]) == ["Study Objectives"]),
        ("anchors are stripped when naming sections",
         normalise("Outcomes {#outcomes}") == "Outcomes"),
        ("bookdown markers are stripped",
         normalise("(APPENDIX) Appendix {-}") == "Appendix"),
    ]
    failed = [n for n, ok in checks if not ok]
    if failed:
        raise AssertionError("sections self-test failed:" + chr(10) + "  " +
                             (chr(10) + "  ").join(failed))
    return len(checks)


if __name__ == "__main__":
    print(f"sections self-test passed ({_self_test()} cases)")
