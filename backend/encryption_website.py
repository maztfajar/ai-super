from cryptography.fernet import Fernet

def generate_key() -> bytes:
    """Generate a key for encryption."""
    return Fernet.generate_key()

def encrypt_data(data: str, key: bytes) -> bytes:
    """Encrypt the given data using the provided key."""
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """Decrypt the given encrypted data using the provided key."""
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data).decode()
    return decrypted_data

# Contoh penggunaan
if __name__ == "__main__":
    # Generate a key
    key = generate_key()
    print(f"Generated Key: {key.decode()}")

    # Data yang ingin dienkripsi
    data = "Ini adalah data sensitif yang perlu dienkripsi."

    # Enkripsi data
    encrypted = encrypt_data(data, key)
    print(f"Encrypted Data: {encrypted.decode()}")

    # Dekripsi data
    decrypted = decrypt_data(encrypted, key)
    print(f"Decrypted Data: {decrypted}")