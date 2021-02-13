# Dynamic DNS Web Service

This is a very basic dynamic DNS service.

## Install

This guide assumes the user is running on Debian 10. If you need to setup a DNS server, see the section on PowerDNS.


1. Create directory for the service. You could select something different, but you will need to modify the service file.

mkdir -p /opt/ddns/app
cd /opt/ddns

2. Create a dedicated Python virtual environment

apt-get install python3-venv
pythons3 -m venv .venv
source /opt/ddns/.venv/bin/activate
pip install uvicorn FastAPI dnspython

3. Copy the example config file

cp /opt/ddns/app/ddns.ini_example /opt/ddns/app/ddns.ini

4. Edit /opt/ddns/app/ddns.ini to specify zone, TSIG, etc.

5. Enable the service. The default service file uses SystemD sandboxing.

cp /opt/ddns/app/ddns.service /lib/systemd/system/
systemctl enable ddns
systemctl start ddns

## Proxy

The service should be run behind a reverse proxy, that provides SSL termination. Below is an example using nginx.

1. Install...

apt-get install nginx

2. Create / Request SSL Certs

3. Place the following template in /etc/nginx/sites-available/HOSTNAME

server {
  listen                80;
  server_name           ddns.server.example.org;
  rewrite     ^(.*)     https://$server_name$1 permanent;
}

server {
  listen                443;
  server_name           ddns.server.example.org;
  access_log            /var/log/nginx/ddns.access.log;
  error_log             /var/log/nginx/ddns.error.log error;

  ssl on;

  ssl_certificate       /etc/ssl/certs/ddns_cert.pem;
  ssl_certificate_key   /etc/ssl/private/ddns_key.pem;
  ssl_dhparam           /etc/ssl/private/dhparams.pem;

  # Enable SSL Session Caching
  ssl_session_cache shared:SSL:10m;

  ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
  ssl_ciphers 'HIGH:!aNULL';
  ssl_prefer_server_ciphers on;

  add_header Strict-Transport-Security "max-age=31536000" always;

  location / {
    proxy_pass        http://0.0.0.0:8000/;

    proxy_http_version 1.1;

    proxy_redirect    off;
    proxy_set_header  Host             $http_host;
    proxy_set_header  X-Real-IP        $remote_addr;
    proxy_set_header  X-Forwarded-For  $proxy_add_x_forwarded_for;
    proxy_set_header  X-Forwarded-Protocol $scheme;
  }

}

4. Enable the proxy...

cd /etc/nginx/sites-enabled
unlink default
ln -s /etc/nginx/sites-available/HOSTNAME

## PowerDNS

1. Install...

apt-get install pdns-server pdns-backend-sqlite3 sqlite3
apt-get remove pdns-backend-bind
apt-get purge pdns-backend-bind

2. Create a directory for storing the backend database.

mkdir /var/local/powerdns
chown pdns:pdns /var/local/powerdns

3. Populate the database with default schema.

cat /usr/share/pdns-backend-sqlite3/schema/schema.sqlite3.sql |sqlite3 /var/local/powerdns/powerdns.sqlite3

4. Enable the backend: /etc/powerdns/pdns.d/sqlite3.conf 

launch=gsqlite3
gsqlite3-database=/var/local/powerdns/powerdns.sqlite3

5. Restart PowerDNS

systemctl restart pdns

6. Create your zone

pdnsutil create-zone dyn.example.org

7. Generate a TSIG key

pdnsutil generate-tsig-key ddns hmac-sha1

8. Using the sqlite3 utility, you'll need to run the following queries:

insert into domainmetadata (domain_id, kind, content) values (1, 'TSIG-ALLOW-DNSUPDATE', 'ddns');
update records set content = 'dyn.example.org hostmaster.ddns.server.example.org 1 10800 3600 604800 3600' where id = 1;

9. In /etc/powerdns/pdns.conf, set updatedns to 'yes'.

10. Restart PowerDNS, again

systemctl restart pdns

