import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import requests
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Pencatat Keuangan", 
    page_icon="💰", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# LINK BACA (Google Sheets Publik)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/18MBeS5NSczt_rQKXg8yZsyRc1NIX6253VW2qyT4i9PA/edit?usp=sharing"

# LINK TULIS (WEB APP URL Dari Google Apps Script)
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwQPPe2hOJlbWQiAE0Dfq1tBE-ieli0F_QRte8sXZMPJ6GnF0A8neB3zNthewUpcleW/exec"

# Koneksi untuk MENGAMBIL data
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl="0")
        return df
    except Exception:
        return pd.DataFrame(columns=["Tanggal", "Tipe", "Kategori", "Jumlah", "Keterangan"])

st.title("💰 Catatan Keuangan")

# --- FORM INPUT ---
with st.expander("➕ Tambah Transaksi Baru", expanded=False):
    tipe = st.radio("Jenis Transaksi", ["Pengeluaran", "Pemasukan"], horizontal=True)

    if tipe == "Pengeluaran":
        kategori_opts = ["Makanan & Minuman", "Transportasi", "Belanja", "Tagihan", "Hiburan", "Lainnya"]
    else:
        kategori_opts = ["Gaji", "Bonus", "Investasi", "Penjualan", "Lainnya"]

    kategori = st.selectbox("Kategori", kategori_opts)
    jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=5000, format="%d")
    keterangan = st.text_input("Keterangan", placeholder="Contoh: Makan siang")

    if st.button("Simpan Transaksi", use_container_width=True, type="primary"):
        if jumlah > 0:
            payload = {
                "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Tipe": tipe,
                "Kategori": kategori,
                "Jumlah": int(jumlah),
                "Keterangan": keterangan if keterangan else "-"
            }
            
            response = requests.post(WEB_APP_URL, json=payload)
            
            if response.status_code == 200:
                st.success(f"{tipe} sebesar Rp {jumlah:,.0f}".replace(",", ".") + " berhasil disimpan!")
                st.rerun()
            else:
                st.error("Gagal menyimpan data ke Google Sheets. Cek kembali Web App URL.")
        else:
            st.warning("Masukkan nominal jumlah terlebih dahulu.")

st.markdown("---")

# --- MEMUAT DATA UNTUK DASBOR ---
df = load_data()
df_tampil = pd.DataFrame()  # Inisialisasi awal agar tidak timbul NameError

if not df.empty and "Jumlah" in df.columns:
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
    df["Tanggal_DT"] = pd.to_datetime(df["Tanggal"], format="%Y-%m-%d %H:%M", errors="coerce")
    sekarang = datetime.now()

    # --- FILTER RENTANG TANGGAL ---
    st.subheader("📅 Laporan Keuangan")
    filter_waktu = st.selectbox(
        "Pilih Rentang Waktu:",
        ["Semua Waktu", "Harian (Hari Ini)", "Mingguan (7 Hari Terakhir)", "Bulanan (Bulan Ini)", "Pilih Tanggal Manual"]
    )

    if filter_waktu == "Harian (Hari Ini)":
        df_filtered = df[df["Tanggal_DT"].dt.date == sekarang.date()]
    elif filter_waktu == "Mingguan (7 Hari Terakhir)":
        batas_minggu = sekarang.date() - timedelta(days=7)
        df_filtered = df[df["Tanggal_DT"].dt.date >= batas_minggu]
    elif filter_waktu == "Bulanan (Bulan Ini)":
        df_filtered = df[(df["Tanggal_DT"].dt.month == sekarang.month) & (df["Tanggal_DT"].dt.year == sekarang.year)]
    elif filter_waktu == "Pilih Tanggal Manual":
        rentang_tanggal = st.date_input("Pilih Tanggal Mulai & Akhir", [])
        if len(rentang_tanggal) == 2:
            mulai, akhir = rentang_tanggal
            df_filtered = df[(df["Tanggal_DT"].dt.date >= mulai) & (df["Tanggal_DT"].dt.date <= akhir)]
        else:
            df_filtered = df
    else:
        df_filtered = df

    st.write(f"*(Menampilkan data untuk: **{filter_waktu}**)*")

    # --- RINGKASAN SALDO ---
    total_masuk = df_filtered[df_filtered["Tipe"] == "Pemasukan"]["Jumlah"].sum()
    total_keluar = df_filtered[df_filtered["Tipe"] == "Pengeluaran"]["Jumlah"].sum()
    saldo = total_masuk - total_keluar

    if total_keluar > total_masuk:
        st.error(f"⚠️ **PERINGATAN: Defisit!**\n\n"
                 f"Masuk: Rp {total_masuk:,.0f} | Keluar: Rp {total_keluar:,.0f} | Saldo: Rp {saldo:,.0f}".replace(",", "."))
    else:
        st.success(f"✅ **Keuangan Aman**\n\n"
                   f"Masuk: Rp {total_masuk:,.0f} | Keluar: Rp {total_keluar:,.0f} | Saldo: Rp {saldo:,.0f}".replace(",", "."))

    # --- GRAFIK PIE ---
    df_keluar = df_filtered[df_filtered["Tipe"] == "Pengeluaran"]
    
    if not df_keluar.empty and df_keluar["Jumlah"].sum() > 0:
        grouped = df_keluar.groupby("Kategori")["Jumlah"].sum()
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        wedges, texts, autotexts = ax.pie(grouped, labels=grouped.index, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.info("Tidak ada pengeluaran pada rentang waktu ini.")

    # --- TABEL RIWAYAT TRANSAKSI ---
    st.subheader("📋 Rincian Transaksi")
    df_tampil = df_filtered.drop(columns=["Tanggal_DT"]).iloc[::-1]
    
    if not df_tampil.empty:
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada data pada periode ini.")
else:
    st.info("Belum ada transaksi tersimpan.")

# --- MENGHAPUS TRANSAKSI ---
with st.expander("🗑️ Hapus Transaksi"):
    if not df_tampil.empty:
        pilihan_hapus = st.selectbox(
            "Pilih transaksi yang ingin dihapus:",
            options=df_tampil.index,
            format_func=lambda i: f"[{df_tampil.loc[i, 'Tanggal']}] {df_tampil.loc[i, 'Kategori']} - Rp {df_tampil.loc[i, 'Jumlah']:,} ({df_tampil.loc[i, 'Keterangan']})"
        )
        
        if st.button("Hapus Transaksi Ini", type="primary"):
            row_excel = int(pilihan_hapus) + 2
            payload = {
                "action": "delete",
                "rowIndex": row_excel
            }
            res = requests.post(WEB_APP_URL, json=payload)
            if res.status_code == 200:
                st.success("Transaksi berhasil dihapus!")
                st.rerun()
            else:
                st.error("Gagal menghapus transaksi.")
    else:
        st.write("Tidak ada transaksi yang dapat dihapus.")
