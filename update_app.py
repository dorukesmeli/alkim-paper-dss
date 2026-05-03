import re

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'r') as f:
    content = f.read()

# Chunk 1: CSS
target_css = """/* ── Metric card ──────────────────────────────────────────────── */
.metric-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 3px 10px rgba(0,0,0,.05);
    text-align: center;
    border-top: 3px solid #C8102E;
}"""
replacement_css = """/* ── Metric card ──────────────────────────────────────────────── */
.metric-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 3px 10px rgba(0,0,0,.05);
    text-align: center;
    border-top: 3px solid #C8102E;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}"""
content = content.replace(target_css, replacement_css)

# Chunk 2: metric_card function
target_func = """def metric_card(value, label, sub=None, color="#C8102E"):
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(
        f\"\"\"<div class="metric-card" style="border-top-color:{color}">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
                {sub_html}
            </div>\"\"\",
        unsafe_allow_html=True,
    )"""
replacement_func = """def metric_card(value, label, sub=None, color="#C8102E"):
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="metric-card" style="border-top-color:{color}">'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )"""
content = content.replace(target_func, replacement_func)

# Chunk 3: Tabs in page_analysis
# We find the start of tabs and end of Tab 4.
start_str = """    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Kağıt Kaybı & Kullanım",
        "📦 Talep Dağılımı",
        "🔁 Desen Tekrarı",
        "🎨 Kesim Diyagramı",
    ])"""

end_str = """            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.error(f"Grafik oluşturulurken hata: {e}")"""

start_idx = content.find(start_str)
end_idx = content.find(end_str) + len(end_str)

replacement_tabs = """    tab1, tab2 = st.tabs([
        "📊 Genel Görsel Analiz",
        "🎨 Kesim Diyagramı",
    ])

    # ── Tab 1: Genel Görsel Analiz ─────────────────────────────────────────
    with tab1:
        # Section: Kağıt Kaybı & Kullanım
        st.markdown("### 1. Kağıt Kaybı & Kullanım")
        try:
            col_a, col_b = st.columns(2)

            with col_a:
                fig_a = go.Figure()
                # Horizontal stacked bar
                fig_a.add_trace(go.Bar(name="Kullanılan Uzunluk", y=labels, x=used_len,
                                       orientation='h', marker_color=DARK, opacity=0.85))
                fig_a.add_trace(go.Bar(name="Kağıt Kaybı", y=labels, x=pw_vals,
                                       orientation='h', marker_color=RED, opacity=0.85))
                fig_a.update_layout(
                    barmode="stack", title="Kullanılan Uzunluk & Kağıt Kaybı (cm)",
                    height=max(380, len(labels) * 30 + 100), xaxis_title="Uzunluk (cm)",
                    yaxis_title="Reel",
                    **plotly_theme,
                )
                st.plotly_chart(fig_a, use_container_width=True)

            with col_b:
                tw_total = result.get("total_time_waste", 0)
                n_used   = result.get("used_reel_count", 1) or 1
                colors_tw = [RED if t > 0 else DARK for t in tw_vals]
                fig_b = go.Figure()
                fig_b.add_trace(go.Bar(x=labels, y=tw_vals,
                                       marker_color=colors_tw, name="Zaman Kaybı"))
                fig_b.update_layout(
                    title="Zaman Kaybı (0 = Aynı Desen, 1 = Değişim)",
                    yaxis=dict(tickvals=[0, 1], ticktext=["0", "1"]),
                    height=max(380, len(labels) * 30 + 100), **plotly_theme,
                )
                st.plotly_chart(fig_b, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card(f'{result.get("total_paper_waste", 0):.1f}', "Toplam Kağıt Kaybı", sub="cm")
            with c2:
                metric_card(tw_total, "Toplam Zaman Kaybı")
            with c3:
                metric_card(
                    f"{tw_total / n_used * 100:.1f}%",
                    "Desen Değişim Oranı",
                    color=DARK,
                )
        except Exception as e:
            st.error(f"Kağıt Kaybı grafiği oluşturulurken hata: {e}")

        st.markdown("<hr class='dss-divider'>", unsafe_allow_html=True)
        
        # Section: Talep Dağılımı
        st.markdown("### 2. Talep Dağılımı")
        if orders_df is not None and not orders_df.empty:
            try:
                df_viz = orders_df.copy()
                df_viz["paper_type"]   = df_viz["paper_type"].astype(str)
                df_viz["total_length"] = pd.to_numeric(df_viz["length"], errors="coerce") * \
                                         pd.to_numeric(df_viz["quantity"], errors="coerce")

                by_type = df_viz.groupby("paper_type").agg(
                    total_len=("total_length", "sum"),
                    total_qty=("quantity",     "sum"),
                ).reset_index()

                colors_list = [RED, DARK, "#6B7280", "#9CA3AF", "#D1D5DB"]
                clr = colors_list[:len(by_type)]

                col_p, col_b2 = st.columns(2)

                with col_p:
                    fig_pie = go.Figure(go.Pie(
                        labels=by_type["paper_type"],
                        values=by_type["total_len"],
                        marker_colors=clr,
                        hole=0.4,
                        textinfo="label+percent",
                    ))
                    fig_pie.update_layout(
                        title="Tip Bazında Toplam Talep (cm)",
                        height=360, **plotly_theme,
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_b2:
                    fig_bar2 = go.Figure(go.Bar(
                        x=by_type["paper_type"],
                        y=by_type["total_qty"],
                        marker_color=[colors_list[i % len(colors_list)] for i in range(len(by_type))],
                    ))
                    fig_bar2.update_layout(
                        title="Tip Bazında Sipariş Adedi",
                        xaxis_title="Kağıt Tipi",
                        yaxis_title="Adet",
                        height=360, **plotly_theme,
                    )
                    st.plotly_chart(fig_bar2, use_container_width=True)
            except Exception as e:
                st.error(f"Talep grafiği oluşturulurken hata: {e}")
        else:
            st.markdown(
                '<div class="info-banner">ℹ️ Sipariş verisi bulunamadı.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr class='dss-divider'>", unsafe_allow_html=True)
        
        # Section: Desen Tekrarı
        st.markdown("### 3. Desen Tekrarı")
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
                [(p, c) for p, c in pattern_counts.most_common()],
                columns=["Kesim Deseni", "Tekrar Sayısı"],
            )

            fig4 = go.Figure(go.Bar(
                x=pat_df["Tekrar Sayısı"],
                y=pat_df["Kesim Deseni"],
                orientation="h",
                marker_color=RED,
                text=pat_df["Tekrar Sayısı"],
                textposition="outside",
            ))
            fig4.update_layout(
                title="Kesim Deseni Tekrar Sayıları",
                height=max(320, len(pat_df) * 36 + 100),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Tekrar",
                **plotly_theme,
            )
            st.plotly_chart(fig4, use_container_width=True)

            col_s, _ = st.columns([1, 3])
            with col_s:
                metric_card(len(pattern_counts), "Benzersiz Desen Sayısı", color=DARK)
        except Exception as e:
            st.error(f"Desen grafiği oluşturulurken hata: {e}")

    # ── Tab 2: Cutting diagram ─────────────────────────────────────────────
    with tab2:
        try:
            st.caption(
                "Her reel için kesim segmentleri görselleştirilmiştir. "
                "Gri alanlar = Normal Kesim | Kırmızı alan = Kağıt Kaybı"
            )

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
                            name="Kesim",
                            marker_color=color,
                            marker_line=dict(color='white', width=1.5),
                            showlegend=False,
                            text=f"d{d} ({seg_len}cm)",
                            textposition="inside",
                            insidetextanchor="middle",
                            textfont=dict(color="white" if color == "#9CA3AF" else "#374151"),
                            hovertemplate=f"Talep: d{d}<br>Uzunluk: {seg_len}cm<extra></extra>",
                        ))
                        segment_idx += 1

                if r["last_demand"] is not None:
                    ld_v = LD.get(r["last_demand"], 0)
                    d    = r["last_demand"]
                    color = neutral_colors[segment_idx % 2]
                    fig5.add_trace(go.Bar(
                        x=[ld_v], y=[y_lbl],
                        orientation="h",
                        name="Kesim",
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
                legend=dict(orientation="h", y=-0.15),
                **plotly_theme,
            )
            fig5.add_vline(
                x=L, line_dash="dash", line_color=GRAY,
                annotation_text=f"L={L} cm",
                annotation_position="top right",
            )
            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.error(f"Grafik oluşturulurken hata: {e}")"""

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + replacement_tabs + content[end_idx:]
else:
    print("Could not find Tab replacement markers")
    print(start_idx, end_idx)

with open('/Users/dorukesmeli/Desktop/ALKİM DSS/app.py', 'w') as f:
    f.write(content)
print("Updated app.py")
