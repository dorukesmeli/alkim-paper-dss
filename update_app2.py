import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

start_str = """    tab1, tab2 = st.tabs(["""
end_str = """            st.error(f"Grafik oluşturulurken hata: {e}")"""

start_idx = content.find(start_str)
end_idx = content.find(end_str) + len(end_str)

if start_idx == -1 or end_idx == -1:
    print("Could not find bounds")
    exit(1)

new_content = """    tab1, tab2 = st.tabs([
        "📊 Genel Görsel Analiz",
        "🎨 Kesim Diyagramı",
    ])

    # ── Tab 1: Genel Görsel Analiz ─────────────────────────────────────────
    with tab1:
        # Section 1: Kağıt Kaybı & Kullanım + KPIs
        st.markdown('<div class="dss-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Kağıt Kaybı & Kullanım")
        st.caption("Her bir jumbo reel için kullanılan uzunluk ve oluşan kağıt kaybı.")
        
        try:
            col_chart, col_kpi = st.columns([2.5, 1])

            with col_chart:
                fig_a = go.Figure()
                fig_a.add_trace(go.Bar(name="Kullanılan Uzunluk", y=labels, x=used_len,
                                       orientation='h', marker_color=DARK, width=0.6))
                fig_a.add_trace(go.Bar(name="Kağıt Kaybı", y=labels, x=pw_vals,
                                       orientation='h', marker_color=RED, width=0.6))
                
                total_used = sum(used_len)
                total_waste = sum(pw_vals)
                utilization = total_used / (total_used + total_waste) * 100 if (total_used + total_waste) > 0 else 0
                
                fig_a.update_layout(
                    barmode="stack",
                    height=max(350, len(labels) * 35 + 80),
                    xaxis_title="Uzunluk (cm)",
                    yaxis_title="",
                    margin=dict(l=0, r=0, t=30, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    **plotly_theme,
                )
                st.plotly_chart(fig_a, use_container_width=True, config={'displayModeBar': False})

            with col_kpi:
                tw_total = result.get("total_time_waste", 0)
                n_used   = result.get("used_reel_count", 1) or 1
                
                st.markdown("<br>", unsafe_allow_html=True)
                metric_card(tw_total, "Toplam Zaman Kaybı", sub="Değişim Sayısı")
                st.markdown("<br>", unsafe_allow_html=True)
                metric_card(f"{tw_total / n_used * 100:.1f}%", "Desen Değişim Oranı", color=DARK)
                st.markdown("<br>", unsafe_allow_html=True)
                metric_card(n_used - tw_total, "Aynı Desen Kullanım", sub="Adet", color=GRAY)
                st.markdown("<br>", unsafe_allow_html=True)
                metric_card(f"{utilization:.1f}%", "Genel Verimlilik", color=DARK)

        except Exception as e:
            st.error(f"Kağıt Kaybı grafiği oluşturulurken hata: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Section 2: Talep Dağılımı
        if orders_df is not None and not orders_df.empty:
            st.markdown('<div class="dss-card">', unsafe_allow_html=True)
            st.markdown("### 📦 Talep Dağılımı")
            st.caption("Kağıt tiplerine göre toplam uzunluk talebi ve sipariş adetleri.")
            try:
                df_viz = orders_df.copy()
                df_viz["paper_type"]   = df_viz["paper_type"].astype(str)
                df_viz["total_length"] = pd.to_numeric(df_viz["length"], errors="coerce") * \
                                         pd.to_numeric(df_viz["quantity"], errors="coerce")

                by_type = df_viz.groupby("paper_type").agg(
                    total_len=("total_length", "sum"),
                    total_qty=("quantity",     "sum"),
                ).reset_index()

                colors_list = [RED, DARK, "#6B7280", "#9CA3AF", "#D1D5DB", "#E5E7EB"]
                clr = colors_list[:len(by_type)]

                col_p, col_b2 = st.columns(2)

                with col_p:
                    fig_pie = go.Figure(go.Pie(
                        labels=by_type["paper_type"],
                        values=by_type["total_len"],
                        marker_colors=clr,
                        hole=0.5,
                        textinfo="label+percent",
                        textfont=dict(color="white"),
                    ))
                    fig_pie.update_layout(
                        title="Tip Bazında Toplam Talep (cm)",
                        height=320,
                        margin=dict(l=20, r=20, t=40, b=20),
                        **plotly_theme,
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

                with col_b2:
                    fig_bar2 = go.Figure(go.Bar(
                        x=by_type["paper_type"],
                        y=by_type["total_qty"],
                        marker_color=DARK,
                        width=0.5,
                    ))
                    fig_bar2.update_layout(
                        title="Tip Bazında Sipariş Adedi",
                        xaxis_title="Kağıt Tipi",
                        yaxis_title="Adet",
                        height=320,
                        margin=dict(l=20, r=20, t=40, b=20),
                        **plotly_theme,
                    )
                    st.plotly_chart(fig_bar2, use_container_width=True, config={'displayModeBar': False})
            except Exception as e:
                st.error(f"Talep grafiği oluşturulurken hata: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        # Section 3: Desen Tekrarı
        st.markdown('<div class="dss-card">', unsafe_allow_html=True)
        st.markdown("### 🔁 Desen Tekrarı")
        st.caption("Optimizasyon sonucunda oluşan kesim desenleri ve kullanım sıklıkları.")
        try:
            from collections import Counter
            pattern_strs = []
            for r in roll_data:
                parts = []
                for d, cnt in sorted(r["assignments"].items()):
                    parts.extend([str(int(LD[d]) if float(LD[d]) == int(LD[d]) else LD[d])] * cnt)
                if r["last_demand"] is not None:
                    v = LD[r["last_demand"]]
                    parts.append(str(int(v) if float(v) == int(v) else v))
                pattern_strs.append(" + ".join(parts) if parts else "boş")

            pattern_counts = Counter(pattern_strs)
            pat_df = pd.DataFrame(
                [(p, c) for p, c in pattern_counts.most_common(15)], # Show top 15 max for compactness
                columns=["Kesim Deseni", "Tekrar Sayısı"],
            )

            fig4 = go.Figure(go.Bar(
                x=pat_df["Tekrar Sayısı"],
                y=pat_df["Kesim Deseni"],
                orientation="h",
                marker_color=RED,
                text=pat_df["Tekrar Sayısı"],
                textposition="outside",
                width=0.6,
            ))
            fig4.update_layout(
                height=max(280, len(pat_df) * 35 + 60),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Tekrar Sayısı",
                margin=dict(l=0, r=0, t=20, b=0),
                **plotly_theme,
            )
            st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})
        except Exception as e:
            st.error(f"Desen grafiği oluşturulurken hata: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 2: Cutting diagram ─────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="dss-card">', unsafe_allow_html=True)
        st.markdown("### 🎨 Kesim Diyagramı")
        st.caption("Her reel için kesim segmentleri görselleştirilmiştir. Gri alanlar Normal Kesim, Kırmızı alanlar Kağıt Kaybını temsil eder.")
        try:
            fig5 = go.Figure()
            seen_legends = set()
            
            # Using alternating neutral colors for adjacent segments to distinguish them
            neutral_colors = ["#D1D5DB", "#9CA3AF"]

            for r in roll_data:
                y_lbl = f"R{r['reel_id']} T{r['reel_type']}"
                
                segment_idx = 0

                for d, cnt in sorted(r["assignments"].items()):
                    seg_len = LD.get(d, 0)
                    for _ in range(cnt):
                        color = neutral_colors[segment_idx % 2]
                        fig5.add_trace(go.Bar(
                            x=[seg_len], y=[y_lbl],
                            orientation="h",
                            name="Kesilen Parça",
                            marker_color=color,
                            marker_line=dict(color='white', width=1.5),
                            showlegend=("normal" not in seen_legends),
                            text=f"d{d} ({seg_len}cm)",
                            textposition="inside",
                            insidetextanchor="middle",
                            textfont=dict(color="white" if color == "#9CA3AF" else "#374151"),
                            hovertemplate=f"Talep: d{d}<br>Uzunluk: {seg_len}cm<extra></extra>",
                        ))
                        seen_legends.add("normal")
                        segment_idx += 1

                if r["last_demand"] is not None:
                    ld_v = LD.get(r["last_demand"], 0)
                    d    = r["last_demand"]
                    color = neutral_colors[segment_idx % 2]
                    fig5.add_trace(go.Bar(
                        x=[ld_v], y=[y_lbl],
                        orientation="h",
                        name="Kesilen Parça",
                        marker_color=color,
                        marker_line=dict(color='white', width=1.5),
                        showlegend=False,
                        text=f"d{d} ({ld_v}cm)",
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(color="white" if color == "#9CA3AF" else "#374151"),
                        hovertemplate=f"Talep: d{d} [son]<br>Uzunluk: {ld_v}cm<extra></extra>",
                    ))

                if r["paper_waste"] > 0.01:
                    show_waste = "waste" not in seen_legends
                    if show_waste:
                        seen_legends.add("waste")
                    fig5.add_trace(go.Bar(
                        x=[r["paper_waste"]], y=[y_lbl],
                        orientation="h",
                        name="Kağıt Kaybı",
                        marker_color="rgba(200,16,46,0.6)",
                        marker_line=dict(color='white', width=1.5),
                        legendgroup="waste",
                        showlegend=show_waste,
                        text=f"Kayıp ({r['paper_waste']:.1f}cm)",
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(color="white"),
                        hovertemplate=f"Kağıt Kaybı: {r['paper_waste']:.2f} cm<extra></extra>",
                    ))

            fig5.update_layout(
                barmode="stack",
                height=max(380, len(roll_data) * 45 + 120),
                xaxis_title="Uzunluk (cm)",
                xaxis_range=[0, L * 1.05],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=40, b=0),
                **plotly_theme,
            )
            fig5.add_vline(
                x=L, line_dash="dash", line_color=GRAY,
                annotation_text=f"L={L} cm",
                annotation_position="top right",
            )
            st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})
        except Exception as e:
            st.error(f"Grafik oluşturulurken hata: {e}")
        st.markdown('</div>', unsafe_allow_html=True)"""

content = content[:start_idx] + new_content + content[end_idx:]

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)
print("Done")
