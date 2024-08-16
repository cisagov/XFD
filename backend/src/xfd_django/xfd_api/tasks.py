import os
from cgi import print_form
from lib2to3.pgen2.tokenize import printtoken

import redis
import django
from django.db.models import Count
from xfd_api.models import Service
from django.conf import settings  # Import settings after setting DJANGO_SETTINGS_MODULE

# Set the Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xfd_django.settings')

# Initialize Django
django.setup()

def populate_Statscache(event, context):
    try:
        # Connect to Redis Elasticache
        redis_client = redis.StrictRedis(host=settings.ELASTICACHE_ENDPOINT,
                                         port=6379, db=0)

        # Fetch data from Django models
        services = list(
            Service.objects.filter(id__isnull=False)
            .annotate(value=Count('id'))
            .select_related('domainId')
            .order_by('-value')
        )

        # Populate Elasticache with data
        for item in services:
            the_id = str(item.id)  # Convert UUID to string
            redis_client.set(the_id, item.value)  # Store the 'value' in Redis

        return {"status": "success", "message": "Cache populated successfully."}

    except redis.RedisError as redis_error:
        return {"status": "error",
                "message": "Failed to populate cache due to Redis error."}

    except django.db.DatabaseError as db_error:
        return {"status": "error",
                "message": "Failed to populate cache due to database error."}

    except Exception as e:
        return {"status": "error",
                "message": "An unexpected error occurred while populating the cache."}
    
##Use the following for elasticache testing.
# def retrieve_Statscache():
#     # Connect to Redis Elasticache
#     redis_client = redis.StrictRedis(host=settings.ELASTICACHE_ENDPOINT, port=6379, db=0)
#
#     # Fetch data keys from Redis (assuming you know the keys or have stored them)
#     service_ids = Service.objects.values_list('id', flat=True)  # Assuming you want all service IDs
#     retrieved_data = {}
#
#     for service_id in service_ids:
#         key = str(service_id)
#         value = redis_client.get(key)  # Retrieve the value for this key
#         if value:
#             retrieved_data[key] = value.decode('utf-8')  # Decode from bytes to string if necessary
#     print(retrieved_data)
#     return retrieved_data
