import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

start_str = """    # Warning banner
    if result.get("warning"):
        st.markdown(
            f'<div class="warn-banner">⚠️ {result["warning"]}</div>', unsafe_allow_html=True
        )"""

new_content = """    # Warning banner
    if result.get("warning"):
        st.markdown(
            f'<div class="warn-banner">⚠️ {result["warning"]}</div>', unsafe_allow_html=True
        )

    est_min = st.session_state.get("_prev_est_min", 0)
    used_cnt = result.get("used_reel_count", 0)
    if used_cnt > est_min and est_min > 0:
        if "dismiss_reel_warn" not in st.session_state:
            st.session_state.dismiss_reel_warn = False
            
        if not st.session_state.dismiss_reel_warn:
            col_w1, col_w2 = st.columns([8, 1])
            with col_w1:
                st.warning(
                    "**Girilen reel sayısı bu çözüm için yeterli olmadı. Sistem çözümü tamamlamak için ek reel kullanmıştır.**\\n\\n"
                    f"Girilen reel değeri: {est_min}\\n\\n"
                    f"Model için gereken minimum reel sayısı: {used_cnt}", icon="⚠️"
                )
            with col_w2:
                if st.button("Kapat", key="btn_dismiss_reel_warn"):
                    st.session_state.dismiss_reel_warn = True
                    st.rerun()"""

content = content.replace(start_str, new_content)

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)
print("Warning inserted")
