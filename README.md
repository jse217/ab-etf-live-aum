
# AB ETF Live AUM Dashboard (Streamlit + Yahoo Finance)

Intraday estimate of AllianceBernstein total ETF assets via Yahoo Finance:
per‑fund AUM ≈ last price × shares outstanding, summed across ETFs.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then open on your iPad (same Wi‑Fi) at: `http://<your-computer-ip>:8501?kiosk=1`

## Deploy on Streamlit Community Cloud (for iPad)
1. Push this folder to a GitHub repo.
2. In Streamlit Cloud, select the repo and set the main file to `app.py`.
3. Open the app URL on your iPad and add `?kiosk=1` to the end of the URL.

## iPad Tips
- In Safari: Share → **Add to Home Screen** for a full‑screen display.
- Settings → Display & Brightness → **Auto‑Lock: Never** (for desk display).
- Optional: **Guided Access** to lock the screen to the app (Accessibility settings).

## Overrides
Edit `shares_overrides.csv` with columns: `ticker,shares_outstanding`
