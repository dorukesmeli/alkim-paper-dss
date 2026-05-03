import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

start_str = """    # ── Jumbo Reel Type input (Model 1 / Heuristic 1 only) ────────────────
    method = st.session_state.method
    if method in ("Model 1", "Heuristic Model 1"):
        import pandas as pd
        st.markdown("<hr class='dss-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="dss-card dss-card-gray">', unsafe_allow_html=True)"""

end_str = """        st.markdown("</div>", unsafe_allow_html=True)

    # ── Run button ─────────────────────────────────────────────────────────"""

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx == -1 or end_idx == -1:
    print("Could not find bounds")
    print(start_idx, end_idx)
    exit(1)

new_content = """    # ── Jumbo Reel Type input (Model 1 / Heuristic 1 only) ────────────────
    method = st.session_state.method
    if method in ("Model 1", "Heuristic Model 1"):
        st.markdown("<hr class='dss-divider'>", unsafe_allow_html=True)
        st.markdown('<div class="dss-card dss-card-gray">', unsafe_allow_html=True)
        section_header("🔢", "Jumbo Reel Tip Ataması",
                        "Model 1 / Heuristic Model 1: Hangi reele hangi kağıt tipi atanacak?")

        unique_types = sorted(df["paper_type"].astype(str).unique())
        type_int_map = {t: i + 1 for i, t in enumerate(unique_types)}
        n_reels = st.session_state.safe_count

        col_tj_l, col_tj_r = st.columns(2)
        with col_tj_l:
            st.caption(f"Toplam reel sayısı: {n_reels} | Kağıt tipleri: {', '.join(unique_types)}")

            counts = {}
            remaining_reels = n_reels
            for i, tp in enumerate(unique_types):
                if i < len(unique_types) - 1:
                    max_cnt = remaining_reels - (len(unique_types) - i - 1)
                    val = st.number_input(
                        f"Tip '{tp}' Reel Sayısı",
                        min_value=1, max_value=max(1, max_cnt),
                        value=max(1, remaining_reels // len(unique_types)),
                        step=1, key=f"tj_cnt_{tp}",
                    )
                    counts[tp] = val
                    remaining_reels -= val
                else:
                    counts[tp] = max(1, remaining_reels)
                    st.markdown(
                        f'<div style="padding:8px;background:#F3F4F6;border-radius:8px;margin-top:8px">'
                        f"Tip '{tp}': {counts[tp]} reel (kalan)</div>",
                        unsafe_allow_html=True,
                    )

        with col_tj_r:
            # Build and display TJ dict
            tj = {}
            s_idx = 1
            for tp in unique_types:
                for _ in range(counts.get(tp, 1)):
                    if s_idx <= n_reels:
                        tj[s_idx] = type_int_map[tp]
                        s_idx += 1
            while s_idx <= n_reels:
                tj[s_idx] = type_int_map[unique_types[-1]]
                s_idx += 1

            st.session_state.tj_table = tj
            import pandas as pd
            tj_df = pd.DataFrame([(k, v) for k, v in tj.items()],
                                  columns=["Reel ID", "Tip Numarası"])
            st.caption("Oluşturulan atama tablosu (ilk 15 satır)")
            st.dataframe(tj_df.head(15), use_container_width=True, hide_index=True, height=300)

"""

content = content[:start_idx] + new_content + content[end_idx:]

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)
print("TJ Reverted")
