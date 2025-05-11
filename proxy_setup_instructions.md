# Konfiguracja proxy w Google Cloud Console

## 1. Utworzenie Virtual Private Cloud (VPC)

1. Wejdź na [Google Cloud Console](https://console.cloud.google.com/)
2. Przejdź do "VPC Network" > "VPC networks"
3. Kliknij "Create VPC Network"
4. Nadaj nazwę (np. "proxy-network")
5. Skonfiguruj subnets (np. wybierz region `us-central1` i przedział adresów `10.0.0.0/24`)
6. Kliknij "Create"

## 2. Konfiguracja Cloud NAT

1. Przejdź do "Network Services" > "Cloud NAT"
2. Kliknij "Get started" lub "Create NAT gateway"
3. Wybierz nazwę gateway (np. "proxy-nat-gateway")
4. Wybierz sieć VPC utworzoną wcześniej
5. Wybierz region (np. `us-central1`)
6. W "Cloud Router", wybierz "Create new router"
   - Nadaj nazwę routerowi (np. "proxy-router")
   - Kliknij "Create"
7. Pozostaw domyślne ustawienia NAT i kliknij "Create"

## 3. Utworzenie VM z odpowiednim skryptem proxy

1. Przejdź do "Compute Engine" > "VM instances"
2. Kliknij "Create instance"
3. Skonfiguruj:
   - Nadaj nazwę (np. "proxy-vm")
   - Wybierz region (np. `us-central1`)
   - Wybierz maszynę `e2-micro` (najtańsza opcja)
   - W sekcji "Boot disk" wybierz Debian lub Ubuntu
   - W sekcji "Networking", wybierz utworzoną wcześniej sieć VPC
   - W "Network interfaces" upewnij się, że "External IP" jest ustawione na "None" (ruch będzie szedł przez NAT)
   - W sekcji "Startup script" dodaj skrypt konfigurujący proxy (przykład poniżej)
4. Kliknij "Create"

## 4. Skrypt startowy dla serwera proxy (przykład dla Squid)

```bash
#!/bin/bash
apt-get update
apt-get install -y squid
cat > /etc/squid/squid.conf << EOF
http_port 3128
acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12
acl localnet src 192.168.0.0/16
acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 21
acl Safe_ports port 443
acl Safe_ports port 70
acl Safe_ports port 210
acl Safe_ports port 1025-65535
acl Safe_ports port 280
acl Safe_ports port 488
acl Safe_ports port 591
acl Safe_ports port 777
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localnet
http_access allow localhost
http_access deny all
http_reply_access allow all
icp_access allow localnet
icp_access deny all
visible_hostname proxy-server
EOF
systemctl restart squid
```

## 5. Konfiguracja reguł zapory (Firewall)

1. Przejdź do "VPC Network" > "Firewall"
2. Kliknij "Create Firewall Rule"
3. Skonfiguruj:
   - Nadaj nazwę (np. "allow-proxy")
   - Wybierz sieć VPC
   - Kierunek ruchu: "Ingress"
   - Action on match: "Allow"
   - Targets: "All instances in the network"
   - Source filter: "IP ranges"
   - Source IP ranges: `0.0.0.0/0` (lub preferowane zakresy)
   - Specified protocols and ports: "tcp:3128" (port dla Squid)
4. Kliknij "Create"

## 6. Użycie proxy w kodzie Python

```python
import requests

# Konfiguracja proxy
proxy_ip = "WEWNĘTRZNY_IP_VM"  # Wewnętrzny adres IP maszyny VM
proxy_port = "3128"  # Port Squid

proxies = {
    'http': f'http://{proxy_ip}:{proxy_port}',
    'https': f'http://{proxy_ip}:{proxy_port}'
}

# Przykładowe zapytanie przez proxy
response = requests.get('https://ifconfig.me', proxies=proxies)
print(response.text)  # Powinno pokazać IP zewnętrzne Cloud NAT
```

## 7. Koszty

- VM e2-micro: ~$6-8 miesięcznie
- Cloud NAT: Opłata podstawowa (~$0.05/h) + opłata za przetworzony ruch (~$0.045/GB)
- Całkowity szacowany koszt: ~$10-15 miesięcznie dla niskiego ruchu

## 8. Bezpieczeństwo

- Rozważ dodanie uwierzytelniania do serwera proxy
- Ogranicz reguły zapory do konkretnych adresów IP, z których będziesz się łączyć
- Regularnie aktualizuj oprogramowanie proxy 