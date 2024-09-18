from django.shortcuts import render
from django.conf import settings
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Security,
    UploadFile,
    status,
)
from fastapi_limiter import FastAPILimiter
from pydantic import BaseModel, UUID4, Field, ConfigDict
from uuid import UUID
from redis import asyncio as aioredis
from . import schemas
from typing import Any, List, Optional, Union
import uuid
from .auth import get_current_active_user
from .models import ApiKey, Organization, User, Domain


api_router = APIRouter()

async def default_identifier(request):
    """Return default identifier."""
    return request.headers.get("X-Real-IP", request.client.host)


async def get_redis_client(request: Request):
    return request.app.state.redis

# Healthcheck endpoint
@api_router.get("/healthcheck")
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok2"}


@api_router.get("/apikeys")
async def get_api_keys():
    """
    Get all API keys.

    Returns:
        list: A list of all API keys.
    """
    try:
        api_keys = ApiKey.objects.all()
        # return api_keys
        return [
            {
                "id": api_key.id,
                "created_at": api_key.createdat,
                "updated_at": api_key.updatedat,
                "last_used": api_key.lastused,
                "hashed_key": api_key.hashedkey,
                "last_four": api_key.lastfour,
                "user_id": api_key.userid.id if api_key.userid else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# @api_router.get("/organizations")
# async def get_organizations(current_user: User = Depends(get_current_active_user)):
#     """
#     Get all organizations.
#     Returns:
#         list: A list of all organizations.
#     """
#     try:
#         organizations = Organization.objects.all()
#         return [
#             {
#                 "id": organization.id,
#                 "name": organization.name,
#                 "acronym": organization.acronym,
#                 "root_domains": organization.rootdomains,
#                 "ip_blocks": organization.ipblocks,
#                 "is_passive": organization.ispassive,
#                 "country": organization.country,
#                 "state": organization.state,
#                 "region_id": organization.regionid,
#                 "state_fips": organization.statefips,
#                 "state_name": organization.statename,
#                 "county": organization.county,
#                 "county_fips": organization.countyfips,
#                 "type": organization.type,
#                 "parent_id": organization.parentid.id if organization.parentid else None,
#                 "created_by_id": organization.createdbyid.id if organization.createdbyid else None,
#                 "created_at": organization.createdat,
#                 "updated_at": organization.updatedat,
#             }
#             for organization in organizations
#         ]
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))














# @api_router.post(
#     "/breachcomp_credsbydate",
#     dependencies=[
#         Depends(get_api_key)
#     ],  # Depends(RateLimiter(times=200, seconds=60))],
#     response_model=schemas.VwCredsbydateTaskResp,
#     tags=["Get the entire vw_breachcomp_credsbydate view."],
# )
# def credsbydate_view(tokens: dict = Depends(get_api_key)):
#     """Call API endpoint to get the entire credsbydate view."""
#     # Check for API key
#     LOGGER.info(f"The api key submitted {tokens}")
#     if tokens:
#         try:
#             userapiTokenverify(theapiKey=tokens)
#             # If API key valid, create task for query
#             task = credsbydate_view_task.delay()
#             # Return the new task id w/ "Processing" status
#             return {"task_id": task.id, "status": "Processing"}
#         except ObjectDoesNotExist:
#             LOGGER.info("API key expired please try again")
#     else:
#         return {"message": "No api key was submitted"}
#
#
# @api_router.get(
#     "/stats/",
#     dependencies=[
#         # Depends(get_api_key)
#     ],  # Depends(RateLimiter(times=200, seconds=60))],
#     response_model=schemas.Stats,
#     tags=["Retrieve Stats view query."],
# )
# async def credsbydate_view_task_status(
#     # task_id: str, tokens: dict = Depends(get_api_keys)
# ):
#     """Get task status for credsbydate_view."""
#     # Check for API key
#     # LOGGER.info(f"The api key submitted {tokens}")
#     # if tokens:
#     try:
#         # userapiTokenverify(theapiKey=tokens)
#         # Retrieve task status
#         task = credsbydate_view_task.AsyncResult(task_id)
#         # Return appropriate message for status
#         if task.state == "SUCCESS":
#             return {
#                 "task_id": task_id,
#                 "status": "Completed",
#                 "result": task.result,
#             }
#         elif task.state == "PENDING":
#             return {"task_id": task_id, "status": "Pending"}
#         elif task.state == "FAILURE":
#             return {
#                 "task_id": task_id,
#                 "status": "Failed",
#                 "error": str(task.result),
#             }
#         else:
#             return {"task_id": task_id, "status": task.state}
#     except ObjectDoesNotExist:
#         LOGGER.info("API key expired please try again")
#     # else:
#     #     return {"message": "No api key was submitted"}



@api_router.get(
    "/stats/",
    response_model=List[schemas.Stats],  # Expecting a list of Stats objects
    tags=["Retrieve Stats view query."],
)
async def get_Stats(domain_id: str, redis_client=Depends(get_redis_client)):
    """Retrieve Stats from Elasticache."""
    try:
        # Retrieve all service data from Redis
        service_ids = await redis_client.keys("*")  # Adjust the pattern if needed
        services_data = []

        for service_id in service_ids:
            service_data = await redis_client.get(service_id)
            if service_data:
                services_data.append({
                    "id": service_id,  # Ensure this is a valid UUID string
                    "value": int(service_data)  # Convert the value to an integer
                })

        if not services_data:
            raise HTTPException(status_code=404, detail="No stats data found in cache.")

        return services_data

    except aioredis.RedisError as redis_error:
        raise HTTPException(status_code=500, detail=f"Redis error: {redis_error}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# @api_router.get(
#     "/ports/",
#     response_model=List[schemas.Ports],  # Expecting a list of Stats objects
#     tags=["Retrieve Stats view query."],
# )
# async def get_Ports(domain_id: str, redis_client=Depends(get_redis_client)):
#     """Retrieve Stats from Elasticache."""
#     try:
#         # Retrieve all service data from Redis
#         ports_ids = await redis_client.keys("*")  # Adjust the pattern if needed
#         ports_data = []
#
#         for ports_id in ports_ids:
#             ports_data = await redis_client.get(ports_id)
#             if ports_data:
#                 ports_data.append({
#                     "id": ports_id,  # Ensure this is a valid UUID string
#                     "value": int(ports_data)  # Convert the value to an integer
#                 })
#
#         if not ports_data:
#             raise HTTPException(status_code=404, detail="No stats data found in cache.")
#
#         return ports_data
#
#     except aioredis.RedisError as redis_error:
#         raise HTTPException(status_code=500, detail=f"Redis error: {redis_error}")
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@api_router.get(
    "/domain/{domain_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Domain,
    tags=["Get domain by id"],
)
async def get_domain_by_id(domain_id: str):
    """
    Get domain by id.
    Returns:
        object: a single Domain object.
    """
    try:
        # Fetch the Domain object
        # domain = Domain.objects.filter('organizationId').get(
        #     id=domain_id)
        domain = Domain.objects.get(id=domain_id)


        return domain  # Return the mapped Pydantic model instance

    except Domain.DoesNotExist:
        raise HTTPException(status_code=404, detail="Domain not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
