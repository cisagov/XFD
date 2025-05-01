"""DmzSync API."""
# Standard Python Libraries

# Third-Party Libraries
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from fastapi import HTTPException
from xfd_mini_dl.models import Organization, ShodanAssets, ShodanVulns

from ..auth import is_global_write_admin


# POST: /dmz_sync/shodan_sync
def dmz_shodan_sync(shodan_data, current_user):
    """Return ASM asset data based on the passed org."""

    def serialize_page_objects(objects):
        return [
            {
                **{
                    field.name: getattr(obj, field.name)
                    for field in obj._meta.get_fields()
                    if field.name
                    not in [
                        "organization",
                        "data_source",
                        "ip",
                    ]  # Exclude all relationships since these will need to be reconnected
                },
                "organization_acronym": obj.organization.acronym
                if obj.organization
                else None,
                "data_source_name": obj.data_source.name if obj.data_source else None,
            }
            for obj in objects
        ]

    def get_paginated_queryset(
        model_cls,
        org_acronym,
        timestamp_field,
        since_date,
        page_size,
        page_num,
        ordering_field,
    ):  # pylint: disable=R0913
        queryset = model_cls.objects.filter(organization__acronym=org_acronym)

        if since_date:
            queryset = queryset.filter(
                Q(**{"{}__gte".format(timestamp_field): since_date})
            )

        queryset = queryset.order_by(ordering_field)
        paginator = Paginator(queryset, page_size)

        try:
            page = paginator.page(page_num)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = []
        return paginator, page

    try:
        if not is_global_write_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        data = shodan_data.dict() if hasattr(shodan_data, "dict") else shodan_data
        acronym = data.get("acronym")
        page_size = data.get("page_size")
        page_num = data.get("page")
        since_date = data.get("since_date")

        if not since_date:
            raise HTTPException(status_code=400, detail="since_date is required.")

        try:
            organization = Organization.objects.get(acronym=acronym)
        except Organization.DoesNotExist:
            raise HTTPException(status_code=404, detail="Parent organization not found")

        # ShodanAssets
        asset_paginator, asset_page = get_paginated_queryset(
            ShodanAssets,
            organization.acronym,
            "timestamp",
            since_date,
            page_size,
            page_num,
            "shodan_asset_uid",
        )
        shodan_assets_data = (
            serialize_page_objects(asset_page.object_list) if asset_page else []
        )

        # ShodanVulns
        vuln_paginator, vuln_page = get_paginated_queryset(
            ShodanVulns,
            organization.acronym,
            "timestamp",
            since_date,
            page_size,
            page_num,
            "shodan_vuln_uid",
        )
        shodan_vulns_data = (
            serialize_page_objects(vuln_page.object_list) if vuln_page else []
        )

        return {
            "total_pages": max(asset_paginator.num_pages, vuln_paginator.num_pages),
            "current_page": page_num,
            "data": {
                "shodan_assets": shodan_assets_data,
                "shodan_vulns": shodan_vulns_data,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        # TODO: CRASM-2568 - Create a unified logger in python backend
        print("Unexpected error in dmz_shodan_sync: {}".format(e))
        raise HTTPException(status_code=500, detail=str(e))
