# Alkım Kağıt — Kağıt Dilme Optimizasyonu DSS

Alkım Kağıt A.Ş. için geliştirilmiş karar destek sistemi. Müşteri siparişlerini girdi olarak alır, jumbo reellerin nasıl kesileceğine dair optimum kararlar üretir. Hem kağıt kaybı (Paper Waste) hem de zaman kaybı (Time Waste) minimize edilir.

---

## Klasör Yapısı

```
ALKİM DSS/
├── app.py                    ← Ana Streamlit uygulaması
├── solver_wrappers.py        ← Birleşik solver arayüzü
├── data_utils.py             ← Veri doğrulama ve dönüştürme
├── requirements.txt
├── example_orders.csv        ← Örnek sipariş dosyası
├── .streamlit/
│   └── config.toml           ← Streamlit tema ve ayarları
├── assets/
│   └── logo.png              ← Alkım Kağıt logosu
└── models/
    ├── model1.py             ← Model 1 (Gurobi — kesin)
    ← model2.py             ← Model 2 (Gurobi — kesin, tip kararı dahil)
    ├── heuristic1.py         ← Heuristic Model 1
    └── heuristic2.py         ← Heuristic Model 2
```

---

## Kurulum

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Uygulamayı başlat
streamlit run app.py
```

### Gurobi Lisansı (Model 1 & Model 2 için gerekli)

Model 1 ve Model 2 Gurobi kütüphanesini kullanır. Lisans olmadan bu modeller çalışmaz; **Heuristic Model 1 & 2** herhangi bir lisans gerektirmez.

**Akademik lisans:** https://www.gurobi.com/academia/academic-program-and-licenses/  
**WLS lisansı (Cloud):** Ortam değişkenleri ile ayarlanır:

```bash
export WLSACCESSID="..."
export WLSSECRET="..."
export LICENSEID="..."
```

---

## Streamlit Cloud Deployment

1. GitHub'a push edin (gizli bilgiler olmadan).
2. [share.streamlit.io](https://share.streamlit.io) adresinden yeni uygulama ekleyin.
3. Repository, branch ve `app.py` dosyasını seçin.
4. **Secrets** bölümüne Gurobi WLS değişkenlerini ekleyin (opsiyonel):
   ```toml
   WLSACCESSID = "..."
   WLSSECRET   = "..."
   LICENSEID   = "..."
   ```
5. Heuristic modeller Gurobi olmadan tam çalışır.

> **Not:** Streamlit Cloud'da ücretsiz tier Gurobi WLS lisansını destekler ancak büyük modeller için yeterli bellek olmayabilir. Kesin modeller için VPS/Docker önerilir.

---

## Docker / VPS Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build & run
docker build -t alkim-dss .
docker run -p 8501:8501 \
  -e WLSACCESSID="..." \
  -e WLSSECRET="..." \
  alkim-dss
```

**QR kod ile paylaşmak için:** Sunucu IP'nizi veya domain adresinizi bir QR kod üreticisine girin (örn. `http://IP:8501`).

---

## Çözüm Yöntemleri

| Yöntem | Gurobi | Hız | Reel Tipi |
|---|---|---|---|
| Model 1 | ✅ Gerekli | Yavaş | Önceden belirlenir |
| Model 2 | ✅ Gerekli | Yavaş | Otomatik (karar değişkeni) |
| Heuristic Model 1 | ❌ Gerekmez | Hızlı | Önceden belirlenir |
| **Heuristic Model 2** | ❌ Gerekmez | **En Hızlı** | **Otomatik** |

**Önerilen yöntem:** Heuristic Model 2 (büyük veri setleri dahil saniyeler içinde çalışır).

---

## Sipariş Dosyası Formatı

```csv
paper_type,length,quantity
1,140,5
1,104,3
2,170,4
```

- `paper_type`: Kağıt tipi (rakam veya metin)
- `length`: Rulo uzunluğu (cm, ondalıklı olabilir)
- `quantity`: Talep adedi (pozitif tam sayı)
- `order_id`: Opsiyonel, varsa göz ardı edilir

---

## Parametreler

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| L | 348 cm | Jumbo Reel uzunluğu |
| B | 6 | Maksimum Blade sayısı |
| CT | 5 | CT parametresi |
| λ (lambda) | 0.5 | Kağıt kaybı ağırlığı (0→zaman, 1→kağıt) |
| Zaman limiti | 3600 sn | Gurobi için zaman limiti |

---

## Bitirme Projesi Bilgisi

**Şirket:** Alkım Kağıt A.Ş.  
**Konu:** Kağıt Dilme Optimizasyonu Karar Destek Sistemi  
**Yıl:** 2026
