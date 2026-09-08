import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Pencatat Keuangan", 
    page_icon="💰", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# MASUKKAN LINK GOOGLE SHEETS KAMU DI SINI
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/18MBeS5NSczt_rQKXg8yZsyRc1NIX6253VW2qyT4i9PA/edit?usp=sharing"

# Koneksi ke Google Sheets
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
            df_existing = load_data()
            new_data = pd.DataFrame([{
                "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Tipe": tipe,
                "Kategori": kategori,
                "Jumlah": int(jumlah),
                "Keterangan": keterangan if keterangan else "-"
            }])
            
            updated_df = pd.concat([df_existing, new_data], ignore_index=True)
            conn.update(spreadsheet=SPREADSHEET_URL, data=updated_df)
            st.success(f"{tipe} sebesar Rp {jumlah:,.0f}".replace(",", ".") + " berhasil disimpan!")
            st.rerun()
        else:
            st.warning("Masukkan nominal jumlah terlebih dahulu.")

st.markdown("---")

# --- MEMUAT DATA UNTUK DASBOR ---
df = load_data()

if not df.empty and "Jumlah" in df.columns:
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
    
    # Konversi kolom teks "Tanggal" menjadi tipe datetime untuk difilter
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
            df_filtered = df # Tampilkan semua jika tanggal belum lengkap
    else:
        df_filtered = df # Semua Waktu

    st.write(f"*(Menampilkan data untuk: **{filter_waktu}**)*")

    # --- RINGKASAN SALDO ---
    total_masuk = df_filtered[df_filtered["Tipe"] == "Pemasukan"]["Jumlah"].sum()
    total_keluar = df_filtered[df_filtered["Tipe"] == "Pengeluaran"]["Jumlah"].sum()
    saldo = total_masuk - total_keluar

    # Indikator Warna
    if total_keluar > total_masuk:
        st.error(f"⚠️ **PERINGATAN: Defisit!**\n\n"
                 f"Masuk: Rp {total_masuk:,.0f} | Keluar: Rp {total_keluar:,.0f} | Saldo: Rp {saldo:,.0f}".replace(",", "."))
    else:
        st.success(f"✅ **Keuangan Aman**\n\n"
                   f"Masuk: Rp {total_masuk:,.0f} | Keluar: Rp {total_keluar:,.0f} | Saldo: Rp {saldo:,.0f}".replace(",", "."))

    # --- GRAFIK PIE PENGELUARAN ---
    df_keluar = df_filtered[df_filtered["Tipe"] == "Pengeluaran"]
    
    if not df_keluar.empty and df_keluar["Jumlah"].sum() > 0:
        grouped = df_keluar.groupby("Kategori")["Jumlah"].sum()
        
        fig, ax = plt.subplots(figsize=(5, 5))
        # Penyesuaian agar tampilan grafik lebih rapi di HP
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        
        wedges, texts, autotexts = ax.pie(
            grouped, 
            labels=grouped.index, 
            autopct='%1.1f%%', 
            startangle=140
        )
        ax.axis('equal')
        st.pyplot(fig)
    else:
        st.info("Tidak ada pengeluaran pada rentang waktu ini.")

    # --- TABEL RIWAYAT TRANSAKSI ---
    st.subheader("📋 Rincian Transaksi")
    # Buang kolom bantuan datetime agar tabel tampil bersih
    df_tampil = df_filtered.drop(columns=["Tanggal_DT"]).iloc[::-1]
    
    if not df_tampil.empty:
        st.dataframe(df_tampil, use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada data pada periode ini.")
else:
    st.info("Belum ada transaksi tersimpan.")