"""
Generate self-signed SSL certificates for HTTPS
"""
import os
import subprocess
import sys
import ipaddress
import socket

def generate_ssl_certificates():
    """Generate self-signed SSL certificates using Python cryptography"""
    cert_dir = os.path.dirname(os.path.abspath(__file__))
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    # Check if certificates already exist
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("SSL certificates already exist.")
        return cert_file, key_file
    
    print("Generating self-signed SSL certificates...")
    
    try:
        # Try using cryptography library (pure Python)
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Get local hostname and IP
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "127.0.0.1"
        
        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Garden"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Garden Dashboard"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])
        
        # Add Subject Alternative Names for local network access
        san_list = [
            x509.DNSName("localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
        ]
        
        # Try to add the local IP
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except:
            pass
        
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
            .sign(key, hashes.SHA256(), default_backend())
        )
        
        # Write private key
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print(f"SSL certificates generated successfully!")
        print(f"  Certificate: {cert_file}")
        print(f"  Private Key: {key_file}")
        return cert_file, key_file
        
    except ImportError:
        print("cryptography library not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
        # Retry after installation
        return generate_ssl_certificates()


if __name__ == '__main__':
    generate_ssl_certificates()
