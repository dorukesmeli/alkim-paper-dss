import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

# 9. Reorganize "Ekstra Çözüm Yöntemleri"
start_str = '        with st.expander("⚙️ Ekstra Çözüm Yöntemleri"):'
end_str = '        st.markdown("</div>", unsafe_allow_html=True)'

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

new_expander = """        with st.expander("⚙️ Ekstra Çözüm Yöntemleri"):
            st.caption("Farklı bir algoritma seçmek için aşağıdaki yöntemlerden birini kullanabilirsiniz.")
            
            st.markdown("##### Verilen Üretim Sırasına Göre Çözüm")
            st.caption("Bu yöntemlerde jumbo reel tipleri önceden kullanıcı tarafından belirlenir.")
            for mname in ["Model 1", "Heuristic Model 1"]:
                minfo = method_opts[mname]
                is_sel = st.session_state.method == mname
                rec_badge = '<span class="recommended-badge">ÖNERİLEN</span>' if minfo["rec"] else ""
                border = "border: 2px solid #C8102E; background: #FFF5F5;" if is_sel else "border: 2px solid #E5E7EB;"
                st.markdown(
                    f'''<div class="method-card" style="{border}">
                            <span class="method-title">{mname}</span>{rec_badge}
                            <div class="method-desc">{minfo["desc"]}</div>
                        </div>''',
                    unsafe_allow_html=True,
                )
                if st.button(f"Seç: {mname}", key=f"sel_{mname}", use_container_width=True, type="primary" if is_sel else "secondary"):
                    st.session_state.method = mname; st.session_state.solver_result = None; st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Otomatik Reel Tipi Seçimli Çözüm")
            st.caption("Bu yöntemlerde jumbo reel tipleri model tarafından otomatik seçilir.")
            for mname in ["Model 2", "Heuristic Model 2"]:
                minfo = method_opts[mname]
                is_sel = st.session_state.method == mname
                rec_badge = '<span class="recommended-badge">ÖNERİLEN</span>' if minfo["rec"] else ""
                border = "border: 2px solid #C8102E; background: #FFF5F5;" if is_sel else "border: 2px solid #E5E7EB;"
                st.markdown(
                    f'''<div class="method-card" style="{border}">
                            <span class="method-title">{mname}</span>{rec_badge}
                            <div class="method-desc">{minfo["desc"]}</div>
                        </div>''',
                    unsafe_allow_html=True,
                )
                if st.button(f"Seç: {mname}", key=f"sel_{mname}", use_container_width=True, type="primary" if is_sel else "secondary"):
                    st.session_state.method = mname; st.session_state.solver_result = None; st.rerun()

"""
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_expander + content[end_idx:]


# 10 & 11: Jumbo Reel Tip Ataması Redesign
tj_start = content.find('    # ── Jumbo Reel Type input (Model 1 / Heuristic 1 only) ────────────────')
tj_end = content.find('    # ── Run button ─────────────────────────────────────────────────────────')

new_tj = """    # ── Jumbo Reel Type input (Model 1 / Heuristic 1 only) ────────────────
    method = st.session_state.method
    if method in ("Model 1", "Heuristic Model 1"):
        import pandas as pd
        st.markdown("<hr class='dss-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="dss-card dss-card-gray">', unsafe_allow_html=True)
        section_header("🔢", "Jumbo Reel Tip Ataması",
                        "Hangi reele hangi kağıt tipi atanacak? (Tahmini gerekli sayı baz alınmıştır)")

        unique_types = sorted(df["paper_type"].astype(str).unique())
        type_int_map = {t: i + 1 for i, t in enumerate(unique_types)}
        n_reels = est_min  # Use estimated count for UI
        
        # Initialize default dataframe if not exists or if n_reels changed
        if "tj_data" not in st.session_state or len(st.session_state.tj_data) != n_reels:
            init_rows = []
            s_idx = 1
            for i, tp in enumerate(unique_types):
                if i < len(unique_types) - 1:
                    cnt = max(1, n_reels // len(unique_types))
                else:
                    cnt = max(1, n_reels - len(init_rows))
                for _ in range(cnt):
                    if s_idx <= n_reels:
                        init_rows.append({"Reel ID": s_idx, "Tip Numarası": type_int_map[tp]})
                        s_idx += 1
            while s_idx <= n_reels:
                init_rows.append({"Reel ID": s_idx, "Tip Numarası": type_int_map[unique_types[-1]]})
                s_idx += 1
            st.session_state.tj_data = pd.DataFrame(init_rows)

        col_tj_l, col_tj_r = st.columns(2)
        
        with col_tj_r:
            st.caption("Tabloyu doğrudan düzenleyebilirsiniz (Örn: 1,2,3,1,2)")
            edited_df = st.data_editor(
                st.session_state.tj_data,
                use_container_width=True,
                hide_index=True,
                height=300,
                num_rows="fixed",
                key="tj_table_editor"
            )
            # Save exact order for solver
            st.session_state.tj_data = edited_df
            tj = {row["Reel ID"]: row["Tip Numarası"] for _, row in edited_df.iterrows()}
            st.session_state.tj_table = tj

        with col_tj_l:
            st.caption(f"Tahmini Gerekli Reel Sayısı: {n_reels} | Kağıt tipleri: {', '.join(unique_types)}")
            
            # Count current types from edited df
            current_counts = {}
            for tp in unique_types:
                tp_int = type_int_map[tp]
                current_counts[tp] = (edited_df["Tip Numarası"] == tp_int).sum()
                
            def rebuild_tj_data():
                new_list = []
                s_idx = 1
                for t in unique_types:
                    cnt = st.session_state[f"tj_in_{t}"]
                    for _ in range(cnt):
                        new_list.append({"Reel ID": s_idx, "Tip Numarası": type_int_map[t]})
                        s_idx += 1
                if len(new_list) == n_reels:
                    st.session_state.tj_data = pd.DataFrame(new_list)

            for tp in unique_types:
                st.number_input(
                    f"Tip '{tp}' Reel Sayısı",
                    min_value=0, max_value=n_reels,
                    value=int(current_counts.get(tp, 0)),
                    step=1, key=f"tj_in_{tp}",
                    on_change=rebuild_tj_data
                )
            
            total_sum = sum(st.session_state.get(f"tj_in_{t}", current_counts.get(t,0)) for t in unique_types)
            if total_sum != n_reels:
                st.error(f"Toplam sayı {n_reels} olmalıdır! Şu an: {total_sum}")

        st.markdown("</div>", unsafe_allow_html=True)

"""

if tj_start != -1 and tj_end != -1:
    content = content[:tj_start] + new_tj + content[tj_end:]

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)

print("Advanced edits done")
