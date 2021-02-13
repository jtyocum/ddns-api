import os
import configparser
from fastapi import FastAPI, Query, Header
import dns.tsigkeyring
import dns.update
import dns.query


config = configparser.ConfigParser()
config.read(os.path.dirname(os.path.abspath(__file__)) + "/ddns.ini")
dns_server = config["DEFAULT"]["dns_server"]
tsig_key_name = config["DEFAULT"]["tsig_key_name"]
tsig_key = config["DEFAULT"]["tsig_key"]
dns_zone = config["DEFAULT"]["dns_zone"]
shared_key = config["DEFAULT"]["shared_key"]

tags_metadata = [
    {
        "name": "ddns",
        "description": "Update a dynamic DNS record.",
    },
]

app = FastAPI(
    title="Dynamic DNS Update Service",
    description="A basic dynamic DNS update service",
    version="0.1.0",
    openapi_tags=tags_metadata,
)


def update_dns_rr(hostname, ipaddr):
    try:
        keyring = dns.tsigkeyring.from_text({tsig_key_name: tsig_key})
        update = dns.update.Update(dns_zone, keyring=keyring, keyalgorithm="hmac-sha1")
        update.replace(hostname, 60, "A", ipaddr)
        dns.query.tcp(update, dns_server)
        return {"status": "success"}
    except:
        return {"status": "failed"}


@app.get("/ddns", tags=["ddns"])
async def get_ddns(
    client_shared_key: str = Query(
        ...,
        min_length=8,
        max_length=32,
        regex="^[a-zA-Z0-9\-]+$",
    ),
    client_hostname: str = Query(
        ..., min_length=8, max_length=16, regex="^[a-zA-Z0-9\-]+$"
    ),
    x_forwarded_for: str = Header(...),
):

    if client_shared_key == shared_key:
        return update_dns_rr(client_hostname, x_forwarded_for)
    else:
        return {"status": "key error"}
