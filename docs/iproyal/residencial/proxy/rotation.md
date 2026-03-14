# Rotation

In the realm of proxy sessions, we offer two distinct types of rotation: 'Sticky' and 'Randomize'. Each type serves a different purpose, catering to the varying needs of our users.

### Sticky

This option allows you to maintain a consistent proxy for the duration of your session. With sticky sessions, you can configure a 'lifetime' parameter, which determines how long the same proxy will be used before it switches to a new one. This is particularly useful for tasks that require a sustained connection to the same IP address, such as maintaining a consistent session while accessing web resources that have session-based authentication or tracking.

1. The `_session-` key instructs our routing system to either create or resolve a unique session for the connection. The value assigned to this key must be a random alphanumeric string, precisely **8 characters** in length. This ensures the uniqueness and integrity of the session.
2. The `_lifetime-` key directs the router regarding the duration for which the session remains valid. The minimum duration is set at **1 second**, and the maximum extends to **7 days**. It is crucial to note the format here: only one unit of time can be specified. This parameter plays a pivotal role in defining the operational span of a sticky session, balancing between session stability and security needs.<br>

Examples:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-br_session-sgn34f3e_lifetime-10m@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_country-br_session-sgn34f3e_lifetime-10m';
$proxy = 'geo.iproyal.com:12321';
$url = 'http://example.com';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, "$username:$password");
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);

if (curl_errno($ch)) {
    echo 'Error:' . curl_error($ch);
} else {
    echo $response;
}

curl_close($ch);
?>
```

{% endtab %}

{% tab title="Python" %}

```python
import requests
from requests.auth import HTTPProxyAuth

username = 'username123'
password = 'password321_country-br_session-sgn34f3e_lifetime-10m'
proxy = 'geo.iproyal.com:12321'
url = 'http://example.com'

proxies = {
    'http': f'http://{proxy}',
    'https': f'http://{proxy}',
}

auth = HTTPProxyAuth(username, password)

response = requests.get(url, proxies=proxies, auth=auth)

print(response.text)
```

{% endtab %}

{% tab title="Node.js" %}

```javascript
const http = require('http');

const username = 'username123';
const password = 'password321_country-br_session-sgn34f3e_lifetime-10m';
const proxyHost = 'geo.iproyal.com';
const proxyPort = 12321;
const targetUrl = 'http://example.com';

const targetUrlObj = new URL(targetUrl);
const targetHost = targetUrlObj.host;
const targetPath = targetUrlObj.pathname;

const auth = 'Basic ' + Buffer.from(`${username}:${password}`).toString('base64');

const options = {
  host: proxyHost,
  port: proxyPort,
  method: 'GET',
  path: targetUrl,
  headers: {
    'Host': targetHost,
    'Proxy-Authorization': auth
  }
};

const req = http.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log(data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();
```

{% endtab %}
{% endtabs %}

### Randomize

Randomize sessions provide a new proxy with each request. This means that every time you make a request, it comes from a different IP address. This approach is ideal for tasks that require a high level of anonymity and reduced traceability, such as web scraping or accessing content without revealing a consistent identity.&#x20;

**To use this type of rotation, you don't need to add anything to the proxy string.**

**Note**: To reduce IP rotation and improve performance of your proxies, add the  `_forcerandom-1` tag to your proxy string. This will increase the pool of selected locations.&#x20;
