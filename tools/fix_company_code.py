import pathlib, re

def patch_file(path, replacements, regex_repls=()):
    p = pathlib.Path(path)
    if not p.exists():
        print(f"skip (not found): {path}")
        return
    src = p.read_text(encoding="utf-8")
    orig = src
    for a,b in replacements:
        src = src.replace(a,b)
    for pattern, repl in regex_repls:
        src = re.sub(pattern, repl, src)
    if src != orig:
        p.with_suffix(p.suffix + ".bak").write_text(orig, encoding="utf-8")
        p.write_text(src, encoding="utf-8")
        print(f"patched: {path} (backup: {p.name}.bak)")
    else:
        print(f"no changes: {path}")

# --- main.py: вернуть company_code -> code ---
main_repls = [
    ("CompanyModel.company_code", "CompanyModel.code"),
    (".company_code.ilike(", ".code.ilike("),
    ('"company_code": company.company_code', '"code": company.code'),
    ('"company_code": c.company_code', '"code": c.code'),
]
main_regex = [
    (r'"company_code"\s*:', '"code":'),  # в sample_companies ключ
]

patch_file("backend/app/main.py", main_repls, main_regex)

# --- pdf_generator.py: компания ---
pdf_repls = [
    ('getattr(company, "company_code", "-")', 'getattr(company, "code", "-")'),
]
patch_file("backend/app/services/pdf_generator.py", pdf_repls)
