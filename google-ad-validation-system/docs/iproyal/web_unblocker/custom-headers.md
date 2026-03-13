# Custom Headers

Web Unblocker supports the use of custom HTTP headers, allowing you to tailor requests for specific use cases.&#x20;

### **Allowed Headers (Forwarded As-Is)**

These headers are allowed and passed through the unblocker unchanged:

* Cookie
* User-Agent
* Accept-Language
* Accept-Encoding
* Custom headers (e.g., X-My-Header)
* Other headers not [listed as blocked](#blocked-hop-by-hop-headers)

Example usage:

```
curl -x <http://unblocker.example> \\
     --proxy-user user:pass \\
     -H 'Cookie: user=hello; theme=dark' \\
     -H 'X-My-Header: custom-value' \\
     <https://httpbin.org/headers>
```

### **User-Agent Rules**

If your client:

* Uses `User-Agent: curl/... or User-Agent: wget/...`
* Or sends no `User-Agent` at all

Then the unblocker will replace it with a randomized browser User-Agent, such as:

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)
Chrome/134.0.0.0 Safari/537.3
```

### **Blocked (Hop-by-Hop) Headers**

The unblocker removes these headers:

* Connection
* Keep-Alive
* Proxy-Authenticate
* Proxy-Authorization
* Proxy-Connection
* TE
* Trailer
* Transfer-Encoding
* Upgrade
* X-Render-JS

### **Ignored by Chromium Engine (if triggered)**

When Chromium is triggered by the unblocker, it additionaly ignores the following headers:

* Content-Length
* Host
* Cookie2
* Keep-Alive
* Set-Cookie
* Origin
* Referer
* Any `Sec-Fetch-*` header

Chromium will also override the Accept header with the following:

```
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,
        image/avif,image/webp,image/apng,*/*;q=0.8
```

So you may expect this even you explicitly pass “application/json”.

[See Chromium documentation](https://github.com/chromium/chromium/blob/main/services/network/public/cpp/header_util.cc) for more information.
