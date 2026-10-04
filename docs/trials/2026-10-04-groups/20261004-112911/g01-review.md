The greeting implementation is correct, but slugification violates its stated behavior for non-ASCII alphanumeric input.

Review comment:

- [P2] Preserve non-ASCII alphanumeric characters — app/slug.py:5-5
  For titles containing Unicode letters or digits, this ASCII-only character class replaces valid alphanumeric characters with hyphens (for example, `slugify("Café")` returns `"caf"`). The documented contract says only non-alphanumeric runs should be replaced (`.taskets/t2.md:13`), so the implementation should use Unicode-aware alphanumeric matching.
