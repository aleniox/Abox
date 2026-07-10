import os
import sys
import subprocess

def install_and_import(package):
    try:
        import cryptography
    except ImportError:
        print(f"Package '{package}' not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Successfully installed '{package}'!")

if __name__ == "__main__":
    install_and_import("cryptography")
    
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import datetime
    import ipaddress

    cert_dir = os.path.join("storage", "certs")
    os.makedirs(cert_dir, exist_ok=True)
    
    key_path = os.path.join(cert_dir, "key.pem")
    cert_path = os.path.join(cert_dir, "cert.pem")
    
    print("Generating RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    print("Generating self-signed certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Hanoi"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Hanoi"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Stark Industries"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Valid for 365 days
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    print(f"Saving private key to {key_path}...")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        
    print(f"Saving certificate to {cert_path}...")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
        
    print("\nSuccess! Self-signed SSL certificate generated.")
    print(f"Private Key: {key_path}")
    print(f"Certificate: {cert_path}")
    print("Now you can run main.py and it will automatically load these certs and use HTTPS.")
