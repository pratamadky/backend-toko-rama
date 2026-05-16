import bcrypt

# Hash admin dari database
php_hash = "$2y$12$9Qu9AoFm1dJsb9yPbHDmP.O6I/3Hp5tR07OshBhZ5JGRlhIbCJQvO"
py_hash = "$2b$" + php_hash[4:]

print("=== TEST VERIFY ===")
print("admin123  :", bcrypt.checkpw("admin123".encode(), py_hash.encode()))
print("admin     :", bcrypt.checkpw("admin".encode(), py_hash.encode()))

print("\n=== BUAT HASH BARU ===")
for user, pwd in [("admin","admin123"), ("karyawan","karyawan123"), ("owner","owner123")]:
    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(12)).decode()
    print(f"{user}: {hashed}")