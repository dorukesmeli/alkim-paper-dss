import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

# 1. Update main routing to include sidebar, page_export, etc.
old_main = """def main():
    if "active_page" not in st.session_state:
        st.session_state.active_page = "home"
        
    page = st.session_state.active_page
    
    # Routing logic
    if page == "home":
        page_home()
    elif page == "orders":
        page_orders()
    elif page == "settings":
        page_settings()
    elif page == "results":
        page_results()
    elif page == "analysis":
        page_analysis()
    else:
        st.session_state.active_page = "home"
        page_home()"""

new_main = """def main():
    if "active_page" not in st.session_state:
        st.session_state.active_page = "home"
        
    render_sidebar()
        
    page = st.session_state.active_page
    
    # Routing logic
    if page == "home":
        page_home()
    elif page == "orders":
        page_orders()
    elif page == "settings":
        page_settings()
    elif page == "results":
        page_results()
    elif page == "analysis":
        page_analysis()
    elif page == "export":
        page_export()
    else:
        st.session_state.active_page = "home"
        page_home()"""

content = content.replace(old_main, new_main)

export_code = """
# ===========================================================================
# PAGE: DIŞA AKTARMA
# ===========================================================================
def page_export():
    section_header("💾", "Dışa Aktarma", "Sonuçları Excel veya CSV olarak indirin")
    
    result = st.session_state.solver_result
    if not result or result.get("status") == "error":
        st.info("İndirilecek veri yok. Lütfen önce optimizasyonu çalıştırın.")
        return
        
    roll_data = result.get("roll_data", [])
    if not roll_data:
        st.info("Kullanılan reel verisi bulunamadı.")
        return
        
    st.markdown('<div class="dss-card dss-card-gray">', unsafe_allow_html=True)
    st.markdown("#### Çözüm Sonuçları")
    
    import pandas as pd
    from io import BytesIO
    
    # Simple export df
    export_df = pd.DataFrame(roll_data)
    
    # Convert dicts/lists to strings for Excel
    for col in export_df.columns:
        if export_df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            export_df[col] = export_df[col].astype(str)
            
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 CSV Olarak İndir",
        data=csv,
        file_name='alkim_kesim_sonuclari.csv',
        mime='text/csv',
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

"""

if "def page_export():" not in content:
    content = content.replace("# MAIN ROUTING", export_code + "\n# MAIN ROUTING")

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)

print("Layout fixed")
