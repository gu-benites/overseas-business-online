# Skipping Static ISP

{% hint style="info" %}
To enable this feature, please contact support.
{% endhint %}

When enabled, this option instructs our router to skip static proxies.

To enable this feature, you will need to add the `_skipispstatic-` key with value **1**.

Example:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-br_skipispstatic-1@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_country-br_skipispstatic-1';
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
password = 'password321_country-br_skipispstatic-1'
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
const password = 'password321_country-br_skipispstatic-1';
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
