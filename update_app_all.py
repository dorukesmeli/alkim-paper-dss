import re
import math

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

app = read_file('app.py')
utils = read_file('data_utils.py')
wrapper = read_file('solver_wrappers.py')

# 1. Global text replacement (dilme -> kesme)
app = app.replace("dilme", "kesme").replace("Dilme", "Kesme")
utils = utils.replace("dilme", "kesme").replace("Dilme", "Kesme")
wrapper = wrapper.replace("dilme", "kesme").replace("Dilme", "Kesme")

# 2. Home page title to Bobin Kesme Optimizasyonu
app = app.replace("Kağıt Kesme Optimizasyonu", "Bobin Kesme Optimizasyonu")

# 3. Swap 1st/2nd notes on Home page and update heuristic note.
old_notes = """                    <li><b>Model 2 / Heuristic Model 2</b> — Ana odak yöntemleri; Jumbo Reel tipini otomatik belirler.</li>
                    <li><b>Model 1 / Heuristic Model 1</b> — Reel tipleri önceden tanımlanmış olmalıdır.</li>
                    <li><b>Model 1 & 2</b> — Gurobi lisansı gerektirir (kesin çözüm).</li>
                    <li><b>Heuristic Model 1 & 2</b> — Lisans gerektirmez, saniyeler içinde çalışır.</li>
                    <li>Büyük veri setleri için <b>Heuristic Model 2</b> önerilir.</li>"""
new_notes = """                    <li><b>Model 1 / Heuristic Model 1</b> — Reel tipleri önceden tanımlanmış olmalıdır.</li>
                    <li><b>Model 2 / Heuristic Model 2</b> — Ana odak yöntemleri; Jumbo Reel tipini otomatik belirler.</li>
                    <li><b>Model 1 & 2</b> — Gurobi lisansı gerektirir (kesin çözüm).</li>
                    <li><b>Heuristic Model 1 & 2</b> — Lisans gerektirmez, saniyeler içinde çalışır.</li>
                    <li>Büyük veri setleri için <b>Heuristic Model 1 ve Heuristic Model 2</b> önerilir.</li>"""
app = app.replace(old_notes, new_notes)

# 4. Remove "Toplam Rulo Adedi" from Sipariş Girişi
app = app.replace("""            metric_card(int(df["quantity"].sum()), "Toplam Rulo Adedi")""", "")

# 5. Remove "Kullanılmayan Reeller" section from Results
unused_start = app.find('        with st.expander(f"Kullanılmayan Reeller')
if unused_start != -1:
    unused_end = app.find('    # ── Export ──', unused_start)
    app = app[:unused_start] + app[unused_end:]

# 6. Fix "Çözüm Yok" logic (ensure it says "Uygun Çözüm" for valid results)
# In app.py around line 1030
app = app.replace('        if status in ("optimal", "feasible"):', '        if status in ("optimal", "feasible", "Uygun Çözüm"):')
app = app.replace('        if result.get("status") in ("optimal", "feasible"):', '        if result.get("status") in ("optimal", "feasible", "Uygun Çözüm"):')
# Wait, let's fix solver_wrappers.py
# If roll_data is not empty and objective is there, it's feasible
wrapper = wrapper.replace('            return {"status": "infeasible", "error": "Uygun çözüm bulunamadı."}', 
                          '            if len(roll_data) > 0:\n                return {"status": "Uygun Çözüm", "objective_value": obj_val, "roll_data": roll_data, "used_reel_count": used_cnt, "total_paper_waste": pw_tot, "total_time_waste": tw_tot}\n            else:\n                return {"status": "infeasible", "error": "Uygun çözüm bulunamadı."}')

wrapper = wrapper.replace('        return {\n            "status": "optimal" if status == GRB.OPTIMAL else "feasible",',
                          '        st_status = "Uygun Çözüm" if len(roll_data) > 0 else "infeasible"\n        if status == GRB.OPTIMAL: st_status = "optimal"\n        return {\n            "status": st_status,')

app = app.replace('        "optimal":               \'<span class="badge-optimal">✓ Optimal Çözüm</span>\',',
                  '        "optimal":               \'<span class="badge-optimal">✓ Optimal Çözüm</span>\',\n        "Uygun Çözüm":           \'<span class="badge-feasible">✓ Uygun Çözüm</span>\',')

# 7. Hide "Model için oluşturulan üst sınır" in Advanced Settings
# Already changed this previously, let's just make sure it only shows est_min
app = app.replace('f"Model için oluşturulan üst sınır: **{safe_count}**"', '""')

# 8. Remove `S ≤ X reel` info in bottom card
app = app.replace('f\'S ≤ <b>{st.session_state.safe_count}</b> reel</div>\',', '""')

# 15. Check CSS to remove empty white space around section_header
app = app.replace('.section-header {\n    display: flex;\n    align-items: center;\n    gap: 10px;\n    margin-bottom: 1.2rem;\n    padding-bottom: 10px;\n    border-bottom: 2px solid #E5E7EB;\n}',
                  '.section-header {\n    display: flex;\n    align-items: center;\n    gap: 10px;\n    margin-bottom: 0.5rem;\n    padding-bottom: 10px;\n    border-bottom: 2px solid #E5E7EB;\n}')

# 14. Adjust Sidebar logo size & CSS (stable scrolling).
# Search for logo img
app = app.replace('width: 140px; margin-bottom: 30px; display: block;',
                  'width: 160px; margin-bottom: 20px; display: block; position: sticky; top: 0;')
app = app.replace('        f\'<img src="data:image/png;base64,{logo}" style="width: 140px; margin-bottom: 30px; display: block;">\'',
                  '        f\'<div style="position: sticky; top: 0; background: #111827; padding-top: 20px; padding-bottom: 10px; z-index: 100;"><img src="data:image/png;base64,{logo}" style="width: 160px; display: block;"></div>\'')

app = app.replace('        f\'<div style="margin-top: auto; padding-top: 40px; font-size: 0.75rem; color: #9CA3AF;">\'',
                  '        f\'<div style="margin-top: 40px; padding-bottom: 20px; font-size: 0.75rem; color: #9CA3AF;">\'')


write_file('app.py', app)
write_file('data_utils.py', utils)
write_file('solver_wrappers.py', wrapper)
print("Basic replacements done")
