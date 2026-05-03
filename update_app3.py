import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

start_str = """    if safe_count > 10:
        st.markdown(
            '<div class="warn-banner">⚠️ <b>Büyük Veri Seti:</b> Bu veri seti büyük görünüyor. '
            'Model 1 ve Model 2 uzun sürebilir. Daha hızlı sonuç için <b>Heuristic Model 2</b> önerilir.</div>',
            unsafe_allow_html=True,
        )

    col_left, col_right = st.columns([1.2, 1])

    # ── Method selection ───────────────────────────────────────────────────
    with col_left:"""

end_str = """        st.markdown("</div>", unsafe_allow_html=True)

    # ── Lambda & advanced params ───────────────────────────────────────────
    with col_right:"""

start_idx = content.find(start_str)
end_idx = content.find(end_str) + len(end_str)

if start_idx == -1 or end_idx == -1:
    print("Could not find bounds")
    print("Start:", start_idx)
    print("End:", end_idx)
    exit(1)

new_content = """    col_left, col_right = st.columns([1.2, 1])

    # ── Method selection ───────────────────────────────────────────────────
    with col_left:
        st.markdown('<div class="dss-card">', unsafe_allow_html=True)
        st.markdown("#### Çözüm Yöntemi")
        
        method_opts = {
            "Model 1": {
                "desc": "Kesin model — Reel tipleri önceden belirlenir. Gurobi gerektirir.",
                "rec": False,
            },
            "Model 2": {
                "desc": "Kesin model — Reel tipini otomatik seçer. Gurobi gerektirir.",
                "rec": True,
            },
            "Heuristic Model 1": {
                "desc": "Hızlı sezgisel — Reel tipleri önceden belirlenir. Lisans gerektirmez.",
                "rec": False,
            },
            "Heuristic Model 2": {
                "desc": "Hızlı sezgisel — Reel tipini otomatik seçer. Lisans gerektirmez.",
                "rec": True,
            },
        }

        # Show currently selected method prominently
        sel_method = st.session_state.method
        sel_info = method_opts.get(sel_method, method_opts["Heuristic Model 2"])
        
        # Warnings for exact models
        if sel_method in ["Model 1", "Model 2"]:
            st.markdown(
                '<div class="warn-banner">⚠️ <b>Uyarı:</b> Bu yöntem Gurobi lisansı gerektirir. '
                'Bulut ortamında çalışması için Gurobi WLS lisansı tanımlanmalıdır.</div>',
                unsafe_allow_html=True,
            )
            if safe_count > 10:
                st.markdown(
                    '<div class="warn-banner">⚠️ <b>Büyük Veri Seti:</b> Bu veri seti büyük görünüyor. '
                    'Exact modeller uzun sürebilir. Daha hızlı sonuç için <b>Heuristic Model 2</b> önerilir.</div>',
                    unsafe_allow_html=True,
                )

        # Selected solver card
        prefix = "Önerilen Çözüm Yöntemi" if sel_info["rec"] else "Seçili Çözüm Yöntemi"
        st.markdown(
            f'''<div class="method-card selected" style="margin-bottom:1rem; padding: 20px;">
                <span class="method-title" style="font-size:1.1rem;">{prefix}: {sel_method}</span>
                <div class="method-desc" style="font-size:0.9rem; margin-top:8px;">{sel_info["desc"]}</div>
            </div>''',
            unsafe_allow_html=True,
        )

        with st.expander("⚙️ Ekstra Çözüm Yöntemleri"):
            st.caption("Farklı bir algoritma seçmek için aşağıdaki yöntemlerden birini kullanabilirsiniz.")
            for mname, minfo in method_opts.items():
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
                if st.button(f"Seç: {mname}", key=f"sel_{mname}",
                             use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.method = mname
                    st.session_state.solver_result = None
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Lambda & advanced params ───────────────────────────────────────────
    with col_right:"""

content = content[:start_idx] + new_content + content[end_idx:]

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)
print("Done")
