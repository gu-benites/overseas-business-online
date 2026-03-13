# JavaScript Rendering

By default, the Web Unblocker attempts to load websites using a simple HTTP request. It checks the HTTP response code, and if the response is successful (e.g., status code `200`), the body is returned to the client.

However, some websites return a `200 OK` status while still serving a placeholder or error message indicating that **JavaScript is disabled**. In such cases, no actual page content is rendered or visible.

To handle this, the web unblocker offers **on-demand JavaScript rendering** using a special `render` flag. This instructs the unblocker to fully render the page in a headless browser before returning the response, allowing access to JavaScript-dependent content.

#### **How to Use the `render` Flag**

You can enable rendering by appending `_render-1` to the password in your proxy credentials. For example:

```
curl -x http://username:password_render-1@unblocker.iproyal.com:12323 https://example.com -k -v
```

**Use Cases**

* Accessing sites that require JavaScript to display content
* Bypassing anti-bot pages that rely on JavaScript
* Scraping modern web apps with dynamic front-ends

**Notes**

* Rendering may increase response times due to the overhead of launching a headless browser.
* Use rendering only when needed, as most sites can still be accessed with basic HTTP requests.
