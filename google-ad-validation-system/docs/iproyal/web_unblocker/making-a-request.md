# Making A Request

The Web Unblocker functions as an HTTP proxy and performs a Man-in-the-Middle (MITM) operation on traffic. This allows it to intercept and modify requests in order to bypass anti-scraping protections.

Due to the MITM mechanism and the required SSL handling, it is not recommended to use the unblocker in browsers or with tools like Playwright.

By the nature of the tool, we currently support only **GET** requests.

**Example requests:**

{% tabs %}
{% tab title="cURL" %}
{% code overflow="wrap" %}

```
curl -k -v -x http://unblocker.iproyal.com:12323 --proxy-user username:password -L https://ipv4.icanhazip.com
```

{% endcode %}
{% endtab %}

{% tab title="PHP" %}

```php
<?php

declare(strict_types=1);

$url = 'https://ipv4.icanhazip.com';
$proxy = 'http://unblocker.iproyal.com:12323';
$proxyAuth = 'username:password';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $proxyAuth);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

$response = curl_exec($ch);
curl_close($ch);

echo $response;
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

url = 'https://ipv4.icanhazip.com'
proxy = 'unblocker.iproyal.com:12323'
proxy_auth = 'username:password'
proxies = {
   'http': f'http://{proxy_auth}@{proxy}',
   'https': f'http://{proxy_auth}@{proxy}'
}

response = requests.get(
   url,
   proxies=proxies,
   verify=False,
   allow_redirects=True,
   timeout=30,
)
print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```
const { fetch, ProxyAgent } = require('undici');

const url = 'https://ipv4.icanhazip.com';
const client = new ProxyAgent(
  'http://username:password@unblocker.iproyal.com:12323'
);

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

(async () => {
  try {
    const response = await fetch(url, {
      redirect: 'follow',
      dispatcher: client,
      headers: {
        'user-agent': 'undici-proxy-test'
      }
    });
    const text = await response.text();
    if (!response.ok) {
      console.error(`HTTP ${response.status} ${response.statusText}`);
    }
    console.log(text.trim());
  } catch (error) {
    console.error('Fetch failed:', error);
  }
})();
```

{% endtab %}

{% tab title="Java" %}

```java
import javax.net.ssl.*;
import java.io.*;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

public class Main {
    private static final String PROXY_HOST = "unblocker.iproyal.com";
    private static final int    PROXY_PORT = 12323;
    private static final String USERNAME   = "username";
    private static final String PASSWORD   = "password";

    private static final String TARGET_HOST = "ipv4.icanhazip.com";
    private static final int    TARGET_PORT = 443;

    private static final boolean INSECURE_TRUST_ALL = true;

    public static void main(String[] args) {
        try {
            System.out.println(fetchIpThroughProxy());
        } catch (Exception e) {
            System.err.println("ERROR: " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }

    private static String fetchIpThroughProxy() throws Exception {
        final String basic = Base64.getEncoder()
                .encodeToString((USERNAME + ":" + PASSWORD).getBytes(StandardCharsets.ISO_8859_1));

        try (Socket proxy = new Socket()) {
            proxy.connect(new InetSocketAddress(PROXY_HOST, PROXY_PORT), 15_000);
            proxy.setSoTimeout(15_000);

            try (var out = new BufferedWriter(new OutputStreamWriter(proxy.getOutputStream(), StandardCharsets.ISO_8859_1));
                 var in  = new BufferedInputStream(proxy.getInputStream())) {

                out.write("CONNECT " + TARGET_HOST + ":" + TARGET_PORT + " HTTP/1.1\r\n");
                out.write("Host: " + TARGET_HOST + ":" + TARGET_PORT + "\r\n");
                out.write("Proxy-Authorization: Basic " + basic + "\r\n");
                out.write("Proxy-Connection: Keep-Alive\r\n\r\n");
                out.flush();

                final String status = readLine(in);
                if (status == null || !status.startsWith("HTTP/1.1 200")) {
                    throw new IOException("CONNECT failed: " + status);
                }
                drainHeaders(in);

                SSLSocket ssl = (SSLSocket) sslFactory().createSocket(proxy, TARGET_HOST, TARGET_PORT, true);
                SSLParameters params = ssl.getSSLParameters();
                params.setServerNames(java.util.List.of(new SNIHostName(TARGET_HOST)));
                ssl.setSSLParameters(params);
                ssl.startHandshake();

                try (var httpsOut = new BufferedWriter(new OutputStreamWriter(ssl.getOutputStream(), StandardCharsets.ISO_8859_1));
                     var httpsIn  = new BufferedInputStream(ssl.getInputStream())) {

                    httpsOut.write("GET / HTTP/1.1\r\n");
                    httpsOut.write("Host: " + TARGET_HOST + "\r\n");
                    httpsOut.write("User-Agent: JavaRawProxy\r\n");
                    httpsOut.write("Connection: close\r\n\r\n");
                    httpsOut.flush();

                    drainHeaders(httpsIn);
                    return readBody(httpsIn).trim();
                }
            }
        }
    }

    private static SSLSocketFactory sslFactory() throws Exception {
        if (!INSECURE_TRUST_ALL) return (SSLSocketFactory) SSLSocketFactory.getDefault();
        TrustManager[] trustAll = new TrustManager[]{ new X509TrustManager() {
            public void checkClientTrusted(java.security.cert.X509Certificate[] c, String a) {}
            public void checkServerTrusted(java.security.cert.X509Certificate[] c, String a) {}
            public java.security.cert.X509Certificate[] getAcceptedIssuers() { return new java.security.cert.X509Certificate[0]; }
        }};
        SSLContext ctx = SSLContext.getInstance("TLS");
        ctx.init(null, trustAll, new java.security.SecureRandom());
        return ctx.getSocketFactory();
    }

    private static void drainHeaders(InputStream in) throws IOException {
        String line;
        while ((line = readLine(in)) != null && !line.isEmpty()) {}
    }

    private static String readBody(InputStream in) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        byte[] tmp = new byte[4096];
        int n;
        while ((n = in.read(tmp)) != -1) buf.write(tmp, 0, n);
        return buf.toString(StandardCharsets.ISO_8859_1);
    }

    private static String readLine(InputStream in) throws IOException {
        StringBuilder sb = new StringBuilder();
        int prev = -1, cur;
        while ((cur = in.read()) != -1) {
            if (prev == '\r' && cur == '\n') { sb.setLength(sb.length() - 1); break; }
            sb.append((char) cur); prev = cur;
        }
        return (sb.length() == 0 && cur == -1) ? null : sb.toString();
    }
}
```

{% endtab %}

{% tab title="Go" %}

```go
package main

import (
    "crypto/tls"
    "encoding/base64"
    "fmt"
    "io"
    "net/http"
    "net/url"
    "time"
)

func main() {
    proxyUser := "username"
    proxyPass := "password"
    proxyStr := "http://unblocker.iproyal.com:12323"

    target := "https://ipv4.icanhazip.com"

    proxyURL, err := url.Parse(proxyStr)
    if err != nil {
        panic(err)
    }
    proxyURL.User = url.UserPassword(proxyUser, proxyPass)

    basic := "Basic " + base64.StdEncoding.EncodeToString([]byte(proxyUser+":"+proxyPass))

    tr := &http.Transport{
        Proxy: http.ProxyURL(proxyURL),

        TLSClientConfig: &tls.Config{InsecureSkipVerify: true},

        ProxyConnectHeader: http.Header{
            "Proxy-Authorization": []string{basic},
        },
    }

    client := &http.Client{
        Transport: tr,
        Timeout:   30 * time.Second,
    }

    resp, err := client.Get(target)
    if err != nil {
        fmt.Println("Request error:", err)
        return
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("HTTP %d\n%s\n", resp.StatusCode, string(body))
}
```

{% endtab %}

{% tab title="C#" %}

```csharp
using System.Net;
using System.Net.Sockets;
using System.Net.Security;
using System.Text;

class Program
{
    static async Task Main()
    {
        var url = new Uri("https://ipv4.icanhazip.com");
        var proxy = new Uri("http://unblocker.iproyal.com:12323");
        const string proxyUser = "username";
        const string proxyPass = "password";

        using var client = CreateHttpClient(proxy, proxyUser, proxyPass);
        var ip = (await client.GetStringAsync(url)).Trim();
        Console.WriteLine(ip);
    }

    private static HttpClient CreateHttpClient(Uri proxyUri, string user, string pass)
    {
        var handler = new SocketsHttpHandler
        {
            AllowAutoRedirect = true,
            AutomaticDecompression = DecompressionMethods.All,
            SslOptions = new SslClientAuthenticationOptions
            {
                RemoteCertificateValidationCallback = static (_, _, _, _) => true
            },
            ConnectCallback = async (ctx, ct) =>
            {
                var tcp = new TcpClient();
                await tcp.ConnectAsync(proxyUri.Host, proxyUri.Port);
                var stream = tcp.GetStream();

                var auth = Convert.ToBase64String(Encoding.ASCII.GetBytes($"{user}:{pass}"));
                string host = ctx.DnsEndPoint.Host;
                int port = ctx.DnsEndPoint.Port;

                var request =
                    $"CONNECT {host}:{port} HTTP/1.1\r\n" +
                    $"Host: {host}:{port}\r\n" +
                    $"Proxy-Authorization: Basic {auth}\r\n" +
                    "\r\n";

                var bytes = Encoding.ASCII.GetBytes(request);
                await stream.WriteAsync(bytes, 0, bytes.Length, ct);
                await stream.FlushAsync(ct);

                using var reader = new StreamReader(stream, Encoding.ASCII, detectEncodingFromByteOrderMarks: false, bufferSize: 4096, leaveOpen: true);
                var status = await reader.ReadLineAsync();
                if (status is null || !status.Contains(" 200 "))
                    throw new IOException($"Proxy CONNECT failed: {status}");
                
                while (!string.IsNullOrEmpty(await reader.ReadLineAsync())) { }
                return stream;
            }
        };

        var client = new HttpClient(handler)
        {
            Timeout = TimeSpan.FromSeconds(30)
        };
        client.DefaultRequestVersion = HttpVersion.Version11;
        return client;
    }
}
```

{% endtab %}
{% endtabs %}

{% hint style="warning" %}
To use the Web Unblocker, you **must disable HTTPS certificate verification.**
{% endhint %}

#### Response Codes

Error codes, often HTTP status codes, indicate problems encountered while accessing a website.

Common errors include 404 (Not Found), 403 (Forbidden), 502 (Bad Gateway), and 503 (Service Unavailable). These codes help identify whether the issue is with the client (4xx), the server (5xx), or a redirection (3xx).&#x20;

| **Response Code** | **Explanation**                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------- |
| 200               | Request was successful.                                                                  |
| 301/302           | The page redirected.                                                                     |
| 403               | The request was blocked.                                                                 |
| 404               | The URL doesn’t exist.                                                                   |
| 429               | Rate limit is reached. We currently allow up to 200 active connections at the same time. |
| 500               | The target server had a problem.                                                         |
| 502               | A gateway or proxy server failed to get a valid response.                                |
| 503               | The server is overloaded or down.                                                        |
| 504               | The server took too long to respond.                                                     |
