"""Token verifier implementation using OAuth 2.0 Token Introspection (RFC 7662)."""

import logging
from typing import Any

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.shared.auth_utils import check_resource_allowed, resource_url_from_server_url

logger = logging.getLogger(__name__)


class IntrospectionTokenVerifier(TokenVerifier):
    """Token verifier that uses OAuth 2.0 Token Introspection (RFC 7662).
    """

    def __init__(
        self,
        introspection_endpoint: str,
        server_url: str,
        client_id: str,
        client_secret: str,
    ):
        self.introspection_endpoint = introspection_endpoint
        self.server_url = server_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.resource_url = resource_url_from_server_url(server_url)

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token via introspection endpoint."""
        import httpx

        # --- 新增的打印点 1: 打印传入的原始令牌 ---
        # print("--- RAW TOKEN RECEIVED BY VERIFIER ---")
        # print(token)
        # print("------------------------------------")
        
        if not self.introspection_endpoint.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            return None

        timeout = httpx.Timeout(10.0, connect=5.0)
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)

        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            verify=True,
        ) as client:
            try:
                form_data = {
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
                headers = {"Content-Type": "application/x-www-form-urlencoded"}

                # --- 你已有的打印点: 打印将要发送的请求 ---
                # print("--- DEBUG: Introspection Request ---")
                # print(f"URL: {self.introspection_endpoint}")
                # print(f"Headers: {headers}")
                # print(f"Data: {form_data}")
                # print("------------------------------------")

                response = await client.post(
                    self.introspection_endpoint,
                    data=form_data,
                    headers=headers,
                )
                
                # --- 新增的打印点 2: 打印收到的原始响应 ---
                # print("--- DEBUG: Introspection Response ---")
                # print(f"Status Code: {response.status_code}")
                # try:
                #     # 尝试解析为JSON并打印
                #     response_data = response.json()
                #     print(f"Response JSON: {response_data}")
                # except Exception as json_error:
                #     # 如果不是JSON，打印原始文本
                #     print(f"Response Text: {response.text}")
                #     print(f"JSON Parsing Error: {json_error}")
                # print("-------------------------------------")


                if response.status_code != 200:
                    print("DEBUG: Introspection failed due to non-200 status code.")
                    return None

                data = response.json()
                if not data.get("active", False):
                    print("DEBUG: Introspection successful, but token is NOT active.")
                    return None

                if not self._validate_resource(data):
                    print("DEBUG: Token is active, but resource/audience validation failed.")
                    return None

                # 如果一切正常，也会打印一条成功日志
                print("DEBUG: Token is active and resource validation successful. Proceeding.")
                return AccessToken(
                    token=token,
                    client_id=data.get("client_id", "unknown"),
                    scopes=data.get("scope", "").split() if data.get("scope") else [],
                    expires_at=data.get("exp"),
                    # resource=data.get("aud"),  # Include resource in token
                    resource=self.resource_url, # <--- 直接使用我们自己的resource_url
                )

            except Exception as e:
                print(f"DEBUG: An exception occurred during token verification: {e}")
                return None

    def _validate_resource(self, token_data: dict[str, Any]) -> bool:
        """Validate token was issued for this resource server.

        Rules:
        - Reject if 'aud' missing.
        - Accept if any audience entry matches the derived resource URL.
        - Supports string or list forms per JWT spec.
        """
        if not self.server_url or not self.resource_url:
            return False

        aud: list[str] | str | None = token_data.get("aud")
        if isinstance(aud, list):
            return any(self._is_valid_resource(a) for a in aud)
        if isinstance(aud, str):
            return self._is_valid_resource(aud)
        return False

    def _is_valid_resource(self, resource: str) -> bool:
        """Check if the given resource matches our server."""
        return check_resource_allowed(self.resource_url, resource)