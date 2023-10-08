#!/usr/bin/env python3
# encoding: utf-8
"""
Gandi v5 LiveDNS - DynDNS Update via REST API and CURL/requests

@author: cave
License GPLv3
https://www.gnu.org/licenses/gpl-3.0.html

Created on 13 Aug 2017
http://doc.livedns.gandi.net/
http://doc.livedns.gandi.net/#api-endpoint -> https://dns.gandi.net/api/v5/
"""

import argparse
import config
import json
import requests


def get_dyn_ip(ifconfig_provider):
    """find out own IPv4 at home <-- this is the dynamic IP which changes more or less frequently
    similar to curl ifconfig.me/ip, see example.config.py for details to ifconfig providers
    """
    r = requests.get(ifconfig_provider)
    ip = r.content.strip().decode("utf8")
    print(f"Current external IP: {ip}")
    return ip


def get_uuid():
    """
    find out ZONE UUID from domain
    Info on domain "DOMAIN"
    GET /domains/<DOMAIN>:

    """
    url = config.api_endpoint + "/domains/" + config.domain
    u = requests.get(url, headers={"X-Api-Key": config.api_secret})
    json_object = json.loads(u._content)
    if u.status_code == 200:
        return json_object["zone_uuid"]
    else:
        print(f"Error: HTTP Status Code {u.status_code} when trying to get Zone UUID")
        print(json_object["message"])
        exit()


def get_dns_ip(uuid):
    """find out IP from first Subdomain DNS-Record
    List all records with name "NAME" and type "TYPE" in the zone UUID
    GET /zones/<UUID>/records/<NAME>/<TYPE>:

    The first subdomain from config.subdomain will be used to get
    the actual DNS Record IP
    """

    url = (
        config.api_endpoint
        + "/zones/"
        + uuid
        + "/records/"
        + config.subdomains[0]
        + "/A"
    )
    headers = {"X-Api-Key": config.api_secret}
    u = requests.get(url, headers=headers)
    if u.status_code == 200:
        json_object = json.loads(u._content)
        remote_ip = json_object["rrset_values"][0].strip()
        print(f"IP from DNS ({config.subdomains[0]}): {remote_ip}")
        return remote_ip
    else:
        print(
            f"Error: HTTP Status Code {u.status_code} when trying to get IP from subdomain {config.subdomains[0]}"
        )
        print(u._content)
        exit()


def update_records(uuid, dynIP, subdomain):
    """ update DNS Records for Subdomains
        Change the "NAME"/"TYPE" record from the zone UUID
        PUT /zones/<UUID>/records/<NAME>/<TYPE>:
        curl -X PUT -H "Content-Type: application/json" \
                    -H 'X-Api-Key: XXX' \
                    -d '{"rrset_ttl": 10800,
                         "rrset_values": ["<VALUE>"]}' \
                    https://dns.gandi.net/api/v5/zones/<UUID>/records/<NAME>/<TYPE>
    """
    url = config.api_endpoint + "/zones/" + uuid + "/records/" + subdomain + "/A"
    payload = {"rrset_ttl": config.ttl, "rrset_values": [dynIP]}
    headers = {"Content-Type": "application/json", "X-Api-Key": config.api_secret}
    u = requests.put(url, data=json.dumps(payload), headers=headers)
    json_object = json.loads(u._content)

    if u.status_code == 201:
        print(
            f"Status Code: {u.status_code}, {json_object['message']}, IP updated for {subdomain}"
        )
        return True
    else:
        print(
            f"Error: HTTP Status Code {u.status_code} when trying to update IP from subdomain {subdomain}"
        )
        print(json_object["message"])
        exit()


def main(force_update, verbosity, dry_run):
    if verbosity:
        print("verbosity turned on - not implemented by now")

    # get zone ID from Account
    uuid = get_uuid()

    # compare dynIP and DNS IP
    dynIP = get_dyn_ip(config.ifconfig)
    dnsIP = get_dns_ip(uuid)

    if force_update:
        print("Going to update/create the DNS Records for the subdomains")
        for sub in config.subdomains:
            update_records(uuid, dynIP, sub)
    else:
        if not dry_run:
            if dynIP == dnsIP:
                print("IP Address Match - no further action")
            else:
                print(
                    f"IP Address Mismatch - going to update the DNS Records for the subdomains with new IP {dynIP}"
                )
                for sub in config.subdomains:
                    update_records(uuid, dynIP, sub)
        else:
            print("Dry run, no changes made.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "-n", "--dry-run", help="just print current local and dns IPs, but do nothing", action="store_true"
    )
    parser.add_argument(
        "-f", "--force", help="force an update/create", action="store_true"
    )
    args = parser.parse_args()
    main(args.force, args.verbose, args.dry_run)
