# Standard Python Libraries
import json
import os

# Third-Party Libraries
from authlib.integrations.requests_client import OAuth2Session

# import time
# import secrets
import jwt
import requests

# from authlib.jose import jwt


# discovery_url = os.environ.get('LOGIN_GOV_BASE_URL') + '/.well-known/openid-configuration'

# try:
#     jwk_set = {
#         "keys": [json.loads(os.environ.get('LOGIN_GOV_JWT_KEY', '{}'))]
#     }
# except Exception:
#     jwk_set = {
#         "keys": [{}]
#     }

# client_options = {
#     'client_id': os.environ.get('LOGIN_GOV_ISSUER'),
#     'token_endpoint_auth_method': 'private_key_jwt',
#     'id_token_signed_response_alg': 'RS256',
#     'key': 'client_id',
#     'redirect_uris': [os.environ.get('LOGIN_GOV_REDIRECT_URI')],
#     'token_endpoint': os.environ.get('LOGIN_GOV_BASE_URL') + '/api/openid_connect/token'
# }
discovery_url = os.getenv("LOGIN_GOV_BASE_URL") + "/.well-known/openid-configuration"
client_options = {
    "client_id": os.getenv("LOGIN_GOV_ISSUER"),
    "token_endpoint_auth_method": "private_key_jwt",
    "id_token_signed_response_alg": "RS256",
    "key": "client_id",
    "redirect_uris": [os.getenv("LOGIN_GOV_REDIRECT_URI")],
    "token_endpoint": os.getenv("LOGIN_GOV_BASE_URL") + "/api/openid_connect/token",
}

jwk_set = {"keys": [json.loads(os.getenv("LOGIN_GOV_JWT_KEY", "{}"))]}


# def random_string(length):
#     return secrets.token_hex(length // 2)


# async def login():
#     discovery_doc = await get_well_known_config(discovery_url)
#     client = OAuth2Session(client_id=client_options['client_id'])
#     nonce = random_string(32)
#     state = random_string(32)
#     url = client.create_authorization_url(
#         discovery_doc['authorization_endpoint'],
#         response_type='code',
#         acr_values='http://idmanagement.gov/ns/assurance/ial/1',
#         scope='openid email',
#         redirect_uri=client_options['redirect_uris'][0],
#         nonce=nonce,
#         state=state,
#         prompt='select_account'
#     )[0]
#     return {"url": url, "state": state, "nonce": nonce}


# async def callback(body):
#     discovery_doc = await get_well_known_config(discovery_url)
#     client = OAuth2Session(client_id=client_options['client_id'])

#     private_key = os.getenv('PRIVATE_KEY')
#     client_assertion = jwt.encode(
#         {'alg': 'RS256'},
#         {'iss': client_options['client_id'], 'sub': client_options['client_id'], 'aud': discovery_doc['token_endpoint'], 'exp': int(time.time()) + 300},
#         private_key
#     )

#     token_response = client.fetch_token(
#         discovery_doc['token_endpoint'],
#         code=body['code'],
#         client_assertion_type='urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
#         client_assertion=client_assertion
#     )


#     # Make a request to the userinfo endpoint
#     userinfo_response = client.get(discovery_doc['userinfo_endpoint'], headers={'Authorization': f"Bearer {token_response['access_token']}"})
#     user_info = userinfo_response.json()
#     return user_info
async def get_discovery_doc(discovery_url):
    response = requests.get(discovery_url)
    response.raise_for_status()
    return response.json()


async def login():
    discovery_doc = await get_discovery_doc(discovery_url)
    client = OAuth2Session(client_id=client_options["client_id"])
    nonce = os.urandom(16).hex()
    state = os.urandom(16).hex()
    authorization_url, state = client.create_authorization_url(
        discovery_doc["authorization_endpoint"],
        response_type="code",
        scope="openid email",
        redirect_uri=client_options["redirect_uris"][0],
        nonce=nonce,
        state=state,
        prompt="select_account",
    )
    return {"url": authorization_url, "state": state, "nonce": nonce}


async def callback(body):
    discovery_doc = await get_discovery_doc(discovery_url)
    client = OAuth2Session(client_id=client_options["client_id"])
    token_response = client.fetch_token(
        discovery_doc["token_endpoint"],
        code=body["code"],
        client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        client_assertion=jwt.encode({"alg": "RS256"}, jwk_set, "private"),
    )
    user_info = client.get(
        discovery_doc["userinfo_endpoint"], token=token_response["access_token"]
    ).json()
    return user_info
