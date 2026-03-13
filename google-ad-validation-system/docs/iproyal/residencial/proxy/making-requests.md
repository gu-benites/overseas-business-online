# Making Requests

In this section, we'll show practical examples of using the proxy string we've created. We'll focus on setting up HTTP/HTTPS and SOCKS5 connections, illustrated through examples in various programming languages.

{% hint style="warning" %}
Keep in mind that the ports will differ depending on the protocol **(HTTP/SOCKS5)**.
{% endhint %}

### HTTP/HTTPS

{% tabs %}
{% tab title="cURL" %}

```bash
curl -v -x http://username123:password321_country-us_state-california@geo.iproyal.com:12321 -L https://ipv4.icanhazip.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php

$url = 'https://ipv4.icanhazip.com';
$proxy = 'geo.iproyal.com:12321';
$proxyAuth = 'username123:password321_country-us_state-california';

$ch = curl_init();

curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $proxyAuth);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);

$response = curl_exec($ch);
curl_close($ch);

echo $response;

?>
```

{% endtab %}

{% tab title="JS" %}

```javascript
const axios = require('axios');

const url = 'https://ipv4.icanhazip.com';
const proxyOptions = {
  host: 'geo.iproyal.com',
  port: 12321,
  auth: {
    username: 'username123',
    password: 'password321_country-us_state-california'
  }
};

axios.get(url, { proxy: proxyOptions })
  .then(response => {
    console.log(response.data);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

url = 'https://ipv4.icanhazip.com'
proxy = 'geo.iproyal.com:12321'
proxy_auth = 'username123:password321_country-us_state-california'
proxies = {
    'http': f'http://{proxy_auth}@{proxy}',
    'https': f'http://{proxy_auth}@{proxy}'
}

response = requests.get(url, proxies=proxies)
print(response.text)
```

{% endtab %}
{% endtabs %}

### SOCKS5

{% tabs %}
{% tab title="cURL" %}

```bash
curl -v -x socks5://username123:password321_country-us_state-california@geo.iproyal.com:32325 -L https://ipv4.icanhazip.com
```

{% endtab %}

{% tab title="PHP" %}

<pre class="language-php"><code class="lang-php"><strong>&#x3C;?php
</strong>
$url = 'https://ipv4.icanhazip.com';
$proxy = 'geo.iproyal.com:32325';
$proxyAuth = 'username123:password321_country-us_state-california';

$ch = curl_init();

curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, $proxyAuth);
curl_setopt($ch, CURLOPT_PROXYTYPE, CURLPROXY_SOCKS5);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);

$response = curl_exec($ch);
curl_close($ch);

echo $response;

?>
</code></pre>

{% endtab %}

{% tab title="JS" %}

```javascript
const axios = require('axios');
const SocksProxyAgent = require('socks-proxy-agent');

const url = 'https://ipv4.icanhazip.com';
const socksProxy = 'socks5://username123:password321_country-us_state-california@geo.iproyal.com:32325';
const agent = new SocksProxyAgent(socksProxy);

axios.get(url, { httpAgent: agent, httpsAgent: agent })
  .then(response => {
    console.log(response.data);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

{% endtab %}

{% tab title="Python" %}

```python
import requests

url = 'https://ipv4.icanhazip.com'
socks5_proxy = 'socks5://username123:password321_country-us_state-california@geo.iproyal.com:32325'
proxies = {
    'http': socks5_proxy,
    'https': socks5_proxy
}

response = requests.get(url, proxies=proxies)
print(response.text)
```

{% endtab %}
{% endtabs %}
