# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import get_db_connection
from datetime import date
import logging
import bcrypt
import math

app = FastAPI()
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROLE_CONFIG = {
    "admin":    {"id_col": "id_admin"},
    "karyawan": {"id_col": "id_karyawan"},
    "owner":    {"id_col": "id_owner"},
}

# ─── MODELS ───────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TransaksiRequest(BaseModel):
    kode_barang: str
    jumlah_terjual: int
    tanggal_penjualan: str
    id_admin: int

class BobotRequest(BaseModel):
    bobot_c1: float
    bobot_c2: float
    bobot_c3: float
    bobot_c4: float

class BarangRequest(BaseModel):
    kode_barang: str
    nama_barang: str
    jumlah_stok: int

class BarangEditRequest(BaseModel):
    nama_barang: str
    jumlah_stok: int

# ─── HELPER ───────────────────────────────────────────────────
def normalize_bcrypt_hash(php_hash: str) -> str:
    if php_hash.startswith("$2y$"):
        return "$2b$" + php_hash[4:]
    return php_hash

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            normalize_bcrypt_hash(hashed).encode("utf-8")
        )
    except Exception as e:
        logging.error(f"Error verifikasi password: {e}")
        return False

def get_conn():
    return get_db_connection()

# ─── HOME ─────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "Backend Toko Rama Collection Menyala!"}

# ─── LOGIN ────────────────────────────────────────────────────
@app.post("/login")
async def login(req: LoginRequest):
    user_input = req.username.strip()
    pass_input = req.password.strip()
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        for role, cfg in ROLE_CONFIG.items():
            cursor.execute(f"SELECT * FROM `{role}` WHERE username = %s", (user_input,))
            user = cursor.fetchone()
            if user:
                if verify_password(pass_input, user["password"]):
                    cursor.close()
                    return {
                        "status": "success",
                        "message": f"Welcome {user_input}",
                        "role": role,
                        "username": user_input,
                        "id": user[cfg["id_col"]],
                    }
                else:
                    break
        cursor.close()
        raise HTTPException(status_code=401, detail="Username atau password salah")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── BARANG ───────────────────────────────────────────────────
@app.get("/barang")
def get_barang():
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM data_barang ORDER BY kode_barang")
        data = cursor.fetchall()
        cursor.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.post("/barang")
def tambah_barang(req: BarangRequest):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO data_barang (kode_barang, nama_barang, jumlah_stok) VALUES (%s, %s, %s)",
            (req.kode_barang, req.nama_barang, req.jumlah_stok)
        )
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Barang berhasil ditambahkan"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.put("/barang/{kode}")
def edit_barang(kode: str, req: BarangEditRequest):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE data_barang SET nama_barang=%s, jumlah_stok=%s WHERE kode_barang=%s",
            (req.nama_barang, req.jumlah_stok, kode)
        )
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Barang berhasil diupdate"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.delete("/barang/{kode}")
def hapus_barang(kode: str):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM data_barang WHERE kode_barang=%s", (kode,))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Barang berhasil dihapus"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── TRANSAKSI ────────────────────────────────────────────────
@app.get("/transaksi")
def get_transaksi():
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, b.nama_barang 
            FROM transaksi_penjualan t
            JOIN data_barang b ON t.kode_barang = b.kode_barang
            ORDER BY t.tanggal_penjualan DESC
            LIMIT 100
        """)
        data = cursor.fetchall()
        cursor.close()
        for row in data:
            if isinstance(row.get('tanggal_penjualan'), date):
                row['tanggal_penjualan'] = str(row['tanggal_penjualan'])
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.post("/transaksi")
def tambah_transaksi(req: TransaksiRequest):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nama_barang FROM data_barang WHERE kode_barang = %s", (req.kode_barang,))
        barang = cursor.fetchone()
        if not barang:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
        cursor.execute("""
            INSERT INTO transaksi_penjualan 
            (id_admin, kode_barang, nama_barang, jumlah_terjual, tanggal_penjualan)
            VALUES (%s, %s, %s, %s, %s)
        """, (req.id_admin, req.kode_barang, barang['nama_barang'],
              req.jumlah_terjual, req.tanggal_penjualan))
        cursor.execute("""
            UPDATE data_barang SET jumlah_stok = jumlah_stok - %s
            WHERE kode_barang = %s
        """, (req.jumlah_terjual, req.kode_barang))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Transaksi berhasil disimpan"}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── PERAMALAN: HITUNG & SIMPAN SES ──────────────────────────
# Endpoint baru: POST /peramalan/hitung?bulan=YYYY-MM
# Cara kerja:
#   1. Ambil total penjualan per barang untuk bulan target
#   2. Ambil data historis bulan-bulan sebelumnya untuk inisialisasi SES
#   3. Hitung forecast SES dengan alpha optimal (grid search 0.1-0.9)
#   4. Hitung MAD dan MSE dari data historis
#   5. Simpan/update hasil ke tabel peramalan
@app.post("/peramalan/hitung")
def hitung_peramalan(bulan: str):
    """
    Hitung SES untuk semua barang pada bulan tertentu dan simpan ke tabel peramalan.
    Gunakan ini sebelum melihat hasil peramalan atau menghitung TOPSIS.
    """
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Ambil semua barang
        cursor.execute("SELECT kode_barang, nama_barang FROM data_barang")
        barang_list = cursor.fetchall()

        if not barang_list:
            raise HTTPException(status_code=404, detail="Tidak ada data barang")

        hasil = []

        for barang in barang_list:
            kode = barang['kode_barang']

            # ── Ambil data penjualan historis semua bulan (urut asc) ──
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(tanggal_penjualan, '%%Y-%%m') as bln,
                    SUM(jumlah_terjual) as total
                FROM transaksi_penjualan
                WHERE kode_barang = %s
                  AND DATE_FORMAT(tanggal_penjualan, '%%Y-%%m') <= %s
                GROUP BY bln
                ORDER BY bln ASC
            """, (kode, bulan))
            history = cursor.fetchall()

            if len(history) == 0:
                # Tidak ada transaksi sama sekali, skip
                continue

            aktuals = [float(h['total']) for h in history]
            bulan_list = [h['bln'] for h in history]

            # Nilai aktual bulan target (0 jika belum ada transaksi bulan ini)
            if bulan_list[-1] == bulan:
                aktual_target = aktuals[-1]
                train_data = aktuals[:-1]  # historis tanpa bulan target
            else:
                aktual_target = 0.0
                train_data = aktuals  # semua historis sebagai training

            # ── Pilih alpha terbaik via grid search ──
            best_alpha = 0.3
            best_mse = float('inf')

            if len(train_data) >= 2:
                for alpha_candidate in [i / 10 for i in range(1, 10)]:  # 0.1 ~ 0.9
                    f = train_data[0]
                    errors_sq = []
                    errors_abs = []
                    for i in range(1, len(train_data)):
                        e = train_data[i] - f
                        errors_sq.append(e ** 2)
                        errors_abs.append(abs(e))
                        f = alpha_candidate * train_data[i] + (1 - alpha_candidate) * f
                    if errors_sq:
                        mse_candidate = sum(errors_sq) / len(errors_sq)
                        if mse_candidate < best_mse:
                            best_mse = mse_candidate
                            best_alpha = alpha_candidate

            alpha = best_alpha

            # ── Hitung SES dengan alpha terbaik ──
            if len(train_data) == 0:
                # Hanya ada 1 data (bulan target itu sendiri)
                forecast = aktual_target
                mad = 0.0
                mse_val = 0.0
            elif len(train_data) == 1:
                forecast = train_data[0]
                mad = abs(aktual_target - forecast) if aktual_target > 0 else 0.0
                mse_val = mad ** 2
            else:
                # Jalankan SES pada train_data
                f = train_data[0]
                errors_sq = []
                errors_abs = []
                for i in range(1, len(train_data)):
                    e = train_data[i] - f
                    errors_sq.append(e ** 2)
                    errors_abs.append(abs(e))
                    f = alpha * train_data[i] + (1 - alpha) * f

                # f sekarang adalah forecast untuk periode berikutnya
                forecast = alpha * train_data[-1] + (1 - alpha) * f

                mad = sum(errors_abs) / len(errors_abs) if errors_abs else 0.0
                mse_val = sum(errors_sq) / len(errors_sq) if errors_sq else 0.0

            forecast = round(forecast, 4)
            mad = round(mad, 4)
            mse_val = round(mse_val, 4)

            # ── Simpan atau update ke tabel peramalan ──
            cursor.execute("""
                SELECT id_peramalan FROM peramalan 
                WHERE kode_barang = %s AND bulan = %s
            """, (kode, bulan))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE peramalan 
                    SET aktual=%s, forecast=%s, mad=%s, mse=%s, alpha=%s
                    WHERE kode_barang=%s AND bulan=%s
                """, (aktual_target, forecast, mad, mse_val, alpha, kode, bulan))
            else:
                cursor.execute("""
                    INSERT INTO peramalan (kode_barang, bulan, aktual, forecast, mad, mse, alpha)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (kode, bulan, aktual_target, forecast, mad, mse_val, alpha))

            conn.commit()

            hasil.append({
                "kode_barang": kode,
                "nama_barang": barang['nama_barang'],
                "bulan": bulan,
                "aktual": aktual_target,
                "forecast": forecast,
                "mad": mad,
                "mse": mse_val,
                "alpha": alpha,
            })

        cursor.close()

        if not hasil:
            raise HTTPException(
                status_code=404,
                detail="Tidak ada data transaksi untuk dihitung. Pastikan ada transaksi terlebih dahulu."
            )

        return {
            "status": "success",
            "message": f"Berhasil menghitung peramalan {len(hasil)} barang untuk bulan {bulan}",
            "total_barang": len(hasil),
            "data": hasil
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Hitung peramalan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── PERAMALAN: BACA HASIL ────────────────────────────────────
@app.get("/peramalan")
def get_peramalan(bulan: str):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, b.nama_barang 
            FROM peramalan p
            JOIN data_barang b ON p.kode_barang = b.kode_barang
            WHERE p.bulan = %s
            ORDER BY p.kode_barang
        """, (bulan,))
        data = cursor.fetchall()
        cursor.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── LAPORAN SES PER ITEM ─────────────────────────────────────
@app.get("/peramalan/laporan")
def laporan_ses_per_item(kode_barang: str):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.bulan, p.aktual, p.forecast, p.mad, p.mse, p.alpha,
                   b.nama_barang, b.kode_barang
            FROM peramalan p
            JOIN data_barang b ON p.kode_barang = b.kode_barang
            WHERE p.kode_barang = %s
            ORDER BY p.bulan ASC
        """, (kode_barang,))
        data = cursor.fetchall()

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data peramalan untuk barang {kode_barang}"
            )

        avg_mad = sum(d['mad'] for d in data) / len(data)
        avg_mse = sum(d['mse'] for d in data) / len(data)

        cursor.close()
        return {
            "kode_barang": kode_barang,
            "nama_barang": data[0]['nama_barang'],
            "alpha": data[0]['alpha'],
            "avg_mad": round(avg_mad, 4),
            "avg_mse": round(avg_mse, 4),
            "detail": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── BOBOT ────────────────────────────────────────────────────
@app.get("/bobot")
def get_bobot():
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pengaturan_bobot ORDER BY id_bobot DESC LIMIT 1")
        data = cursor.fetchone()
        cursor.close()
        return data or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.post("/bobot/update")
def update_bobot(req: BobotRequest):
    total = req.bobot_c1 + req.bobot_c2 + req.bobot_c3 + req.bobot_c4
    if abs(total - 1.0) > 0.001:
        raise HTTPException(status_code=400,
            detail=f"Total bobot harus 1.0, sekarang {total:.3f}")
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pengaturan_bobot 
            SET bobot_c1=%s, bobot_c2=%s, bobot_c3=%s, bobot_c4=%s
            WHERE id_bobot = 1
        """, (req.bobot_c1, req.bobot_c2, req.bobot_c3, req.bobot_c4))
        conn.commit()
        cursor.close()
        return {"status": "success", "message": "Bobot berhasil diperbarui"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

# ─── TOPSIS ───────────────────────────────────────────────────
@app.post("/topsis/hitung")
def hitung_topsis(bulan: str):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pengaturan_bobot ORDER BY id_bobot DESC LIMIT 1")
        bobot = cursor.fetchone()
        if not bobot:
            raise HTTPException(status_code=404, detail="Bobot belum diatur. Atur bobot terlebih dahulu.")
        w = [bobot['bobot_c1'], bobot['bobot_c2'],
             bobot['bobot_c3'], bobot['bobot_c4']]
        cursor.execute("""
            SELECT p.kode_barang, b.nama_barang,
                   p.forecast as c1, p.aktual as c2,
                   p.mad as c3, p.mse as c4
            FROM peramalan p
            JOIN data_barang b ON p.kode_barang = b.kode_barang
            WHERE p.bulan = %s
        """, (bulan,))
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Tidak ada data peramalan untuk bulan {bulan}. Hitung peramalan terlebih dahulu."
            )
        cols = ['c1', 'c2', 'c3', 'c4']
        norms = [math.sqrt(sum(r[c]**2 for r in rows)) for c in cols]
        for r in rows:
            for i, c in enumerate(cols):
                r[f'n_{c}'] = r[c] / norms[i] if norms[i] != 0 else 0
                r[f'w_{c}'] = r[f'n_{c}'] * w[i]
        a_plus  = [max(r['w_c1'] for r in rows), max(r['w_c2'] for r in rows),
                   min(r['w_c3'] for r in rows), min(r['w_c4'] for r in rows)]
        a_minus = [min(r['w_c1'] for r in rows), min(r['w_c2'] for r in rows),
                   max(r['w_c3'] for r in rows), max(r['w_c4'] for r in rows)]
        results = []
        for r in rows:
            vals = [r['w_c1'], r['w_c2'], r['w_c3'], r['w_c4']]
            d_plus  = math.sqrt(sum((vals[i] - a_plus[i])**2  for i in range(4)))
            d_minus = math.sqrt(sum((vals[i] - a_minus[i])**2 for i in range(4)))
            ci = d_minus / (d_plus + d_minus) if (d_plus + d_minus) != 0 else 0
            results.append({
                "kode_barang": r['kode_barang'],
                "nama_barang": r['nama_barang'],
                "nilai_c1": round(r['c1'], 4),
                "nilai_c2": round(r['c2'], 4),
                "nilai_c3": round(r['c3'], 4),
                "nilai_c4": round(r['c4'], 4),
                "nilai_ci": round(ci, 4),
            })
        results.sort(key=lambda x: x['nilai_ci'], reverse=True)
        for i, r in enumerate(results):
            r['ranking'] = i + 1
        cursor.close()
        return results
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"TOPSIS error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()