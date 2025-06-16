"""Helper functions to save Assets to the mdl."""
# Standard Python Libraries
import datetime
import hashlib
import ipaddress

# Third-Party Libraries
from xfd_mini_dl.models import Ip, IpsSubs


def find_smaller_cidr(original_network, new_network):
    """Given two Cidr blocks identify which is smaller."""
    # Convert CIDR blocks to network objects
    og_net = ipaddress.IPv4Network(original_network, strict=False)
    new_net = ipaddress.IPv4Network(new_network, strict=False)

    # Compare the number of addresses in each network
    size_og = og_net.num_addresses
    size_new = new_net.num_addresses

    # Determine the smaller network
    if size_og < size_new:
        return "og"
    elif size_og > size_new:
        return "new"
    else:
        return "same"


def create_or_update_ip(create_defaults, update_dict, linked_sub=None):
    """Create or update an IP based on provided create and update dictionaries."""
    ip_hash = hashlib.sha256(create_defaults.get("ip").encode("utf-8")).hexdigest()
    create_defaults["ip_hash"] = ip_hash
    ip_object, created = Ip.objects.get_or_create(
        ip=create_defaults.get("ip"),
        organization=create_defaults.get("organization"),
        defaults=create_defaults,
    )
    if not created:
        for key, value in update_dict.items():
            if key == "origin_cidr":
                if ip_object.origin_cidr is None:
                    ip_object.origin_cidr = value
                    continue
                if value.id == ip_object.origin_cidr.id:
                    continue
                if ip_object.origin_cidr.retired is True:
                    ip_object.origin_cidr = value
                    continue

                result = find_smaller_cidr(ip_object.origin_cidr.network, value.network)
                if result == "og":
                    continue
                if result == "new":
                    current_alerts = set(ip_object.conflict_alerts)
                    current_alerts.add(
                        "IP also associated with larger cidr {cidr}, cidr_id:{id}".format(
                            cidr=ip_object.origin_cidr.network,
                            id=ip_object.origin_cidr.id,
                        )
                    )
                    ip_object.conflict_alerts = list(current_alerts)
                    ip_object.origin_cidr = value
                else:
                    current_alerts = set(ip_object.conflict_alerts)
                    current_alerts.add(
                        "IP also associated with same sized cidr {cidr}, cidr_id:{id}".format(
                            cidr=value.network, id=value.id
                        )
                    )
                    ip_object.conflict_alerts = list(current_alerts)
            else:
                setattr(ip_object, key, value)
        ip_object.save()

    if linked_sub:
        IpsSubs.objects.update_or_create(
            ip=ip_object,
            sub_domain=linked_sub,
            defaults={
                "last_seen": datetime.datetime.now(datetime.timezone.utc),
                "current": True,
            },
        )

    return ip_object
