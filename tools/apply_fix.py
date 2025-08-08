import re, pathlib

p = pathlib.Path("backend/app/main.py")
src = p.read_text(encoding="utf-8")
orig = src

# 1) Дубликат-проверка компании по company_code
src = src.replace(
    "CompanyModel.name == company.company_code",
    "CompanyModel.company_code == company.company_code"
)

# 2) /companies/search — дублирующий ключ name -> company_code
src = re.sub(r'"name":\s*c\.company_code', '"company_code": c.company_code', src)

# 3) /companies/filter — фильтр по коду должен идти по company_code
src = src.replace(
    "query = query.filter(CompanyModel.name.ilike(f\"%{code}%\"))",
    "query = query.filter(CompanyModel.company_code.ilike(f\"%{code}%\"))"
)

# 4) /companies/filter — ответ с company_code вместо второго name
src = re.sub(r'"name"\s*:\s*c\.company_code', '"company_code": c.company_code', src)

# 5) /wps/search — поле base_material_spec (не base_metal_specification)
src = src.replace("base_metal_specification", "base_material_spec")

# 6) /wps/by-company и /wpqr/by-company — убрать второй name
src = re.sub(r'"name":\s*company\.company_code', '"company_code": company.company_code', src)

# 7) sample_companies: "code" -> "company_code"
src = re.sub(r'"code"\s*:', '"company_code":', src)

# 8) Нормализация для create_sample_wps (если ещё нет)
if "def normalize_wps_payload(" not in src:
    norm_block = '''
    # --- Нормализация ключей и значений под модель WPS ---
    KEY_MAP = {
        "amperage_range_min": "current_range_min",
        "amperage_range_max": "current_range_max",
        "shielding_gas_flow_rate": "gas_flow_rate",
    }

    def normalize_wps_payload(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            k2 = KEY_MAP.get(k, k)
            out[k2] = v
        # welding_positions: массив -> строка "PA,PB,PC"
        if isinstance(out.get("welding_positions"), list):
            out["welding_positions"] = ",".join(out["welding_positions"])
        return out
'''
    src = src.replace("created_wps = []", norm_block + "\n    created_wps = []")

# 9) Применить нормализацию в цикле for wps_data in sample_wps
src = src.replace(
    "for wps_data in sample_wps:",
    "for wps_data in sample_wps:\n        wps_data = normalize_wps_payload(wps_data)"
)

if src == orig:
    print("Ничего не изменено — возможно, правки уже применены.")
else:
    p.with_suffix(".py.bak").write_text(orig, encoding="utf-8")
    p.write_text(src, encoding="utf-8")
    print("✅ Патч применён. Бэкап: backend/app/main.py.bak")
