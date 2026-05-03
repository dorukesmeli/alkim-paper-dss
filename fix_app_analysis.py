import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

analysis_code = """
# ===========================================================================
# PAGE: GÖRSEL ANALİZ
# ===========================================================================
def page_analysis():
    section_header("📈", "Görsel Analiz", "Sonuçların grafiksel değerlendirmesi")
    
    result = st.session_state.solver_result
    if not result or result.get("status") == "error":
        st.info("Lütfen önce bir çözüm oluşturun.")
        return
        
    roll_data = result.get("roll_data", [])
    if not roll_data:
        st.info("Kullanılan reel verisi bulunamadı.")
        return
        
    used_rolls = [r for r in roll_data if r["used"]]
    
    # 1. KPI Cards
    st.markdown('<div class="dss-card">', unsafe_allow_html=True)
    st.markdown("#### Temel Performans Göstergeleri")
    total_time = sum(r["time_waste"] for r in used_rolls)
    total_paper = sum(r["paper_waste"] for r in used_rolls)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Toplam Zaman Kaybı", f"{int(total_time)}")
    with c2:
        st.metric("Toplam Kağıt Kaybı", f"{total_paper:.2f} cm")
    with c3:
        st.metric("Kullanılan Reel Sayısı", f"{len(used_rolls)}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2. Kesim Diyagramı
    st.markdown('<div class="dss-card">', unsafe_allow_html=True)
    st.markdown("#### Kesim Diyagramı (Gantt)")
    
    import plotly.graph_objects as go
    fig_gantt = go.Figure()
    
    for i, r in enumerate(used_rolls):
        x_start = 0
        for demand_id, cnt in r["assignments"].items():
            length = st.session_state.data_dict["LD"][demand_id]
            for _ in range(cnt):
                fig_gantt.add_trace(go.Bar(
                    y=[f"Reel {r['reel_id']}"],
                    x=[length],
                    name=f"Tip {st.session_state.data_dict['TD'][demand_id]} ({length}cm)",
                    orientation='h',
                    marker=dict(line=dict(color='white', width=1))
                ))
                x_start += length
        if r["last_demand"] is not None:
            ld = r["last_demand"]
            length = st.session_state.data_dict["LD"][ld]
            fig_gantt.add_trace(go.Bar(
                y=[f"Reel {r['reel_id']}"],
                x=[length],
                name=f"Tip {st.session_state.data_dict['TD'][ld]} ({length}cm)",
                orientation='h',
                marker=dict(line=dict(color='white', width=1))
            ))
            
    fig_gantt.update_layout(barmode='stack', showlegend=False, height=max(300, len(used_rolls)*40), margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig_gantt, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

"""

if "def page_analysis():" not in content:
    content = content.replace("# MAIN ROUTING", analysis_code + "\n# MAIN ROUTING")

# add it to the routing
content = content.replace('elif page == "results":\n        page_results()', 'elif page == "results":\n        page_results()\n    elif page == "analysis":\n        page_analysis()')

# remove the temporary debug line
content = content.replace('st.write("APP LOADED") # Temporary debug line', '')

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)

print("Analysis page restored")
