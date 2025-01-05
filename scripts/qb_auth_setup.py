"""One-time QuickBooks OAuth 2.0 setup.

Starts a local HTTP server, opens the browser to the Intuit authorization page,
catches the callback with the auth code, and exchanges it for access/refresh tokens.
"""

import http.server
import webbrowser
from urllib.parse import urlparse, parse_qs

from quickbooks.auth import get_authorization_url, exchange_code_for_tokens


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    auth_code = None
    realm_id = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            CallbackHandler.realm_id = params.get("realmId", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this window.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error = params.get("error", ["Unknown error"])[0]
            self.wfile.write(f"<h1>Authorization failed</h1><p>{error}</p>".encode())

    def log_message(self, format, *args):
        pass


def main():
    print("QuickBooks OAuth 2.0 Setup")
    print("=" * 40)

    auth_url = get_authorization_url()
    print(f"\nOpening browser for authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
    print("Waiting for authorization callback on http://localhost:8080/callback ...")
    server.handle_request()

    if CallbackHandler.auth_code:
        print("\nExchanging authorization code for tokens...")
        tokens = exchange_code_for_tokens(CallbackHandler.auth_code, CallbackHandler.realm_id)
        print("Tokens stored successfully!")
        print(f"Realm ID: {CallbackHandler.realm_id}")
        print(f"Token expires in: {tokens.get('expires_in', 'unknown')} seconds")
    else:
        print("\nAuthorization failed — no auth code received.")


if __name__ == "__main__":
    main()
