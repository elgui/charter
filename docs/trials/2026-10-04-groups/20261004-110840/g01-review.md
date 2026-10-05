The greeting implementation and documented probe cases work, but `slugify` incorrectly removes Unicode alphanumeric characters despite the stated behavior.

Review comment:

- [P2] Preserve non-ASCII alphanumeric characters — app/slug.py:5-5
  For titles containing Unicode letters or digits, this ASCII-only character class treats valid alphanumeric characters as separators: for example, `slugify("Café")` returns `"caf"` and an all-CJK title becomes empty. This violates the requirement that only non-alphanumeric runs are replaced (`.taskets/t2.md:13`); use Unicode-aware alphanumeric detection instead.
