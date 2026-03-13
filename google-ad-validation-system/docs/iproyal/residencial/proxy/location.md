# Location

Location targeting is arguably the most crucial aspect of configuring a proxy. Users frequently need to access a proxy server in a specific location for various purposes. IPRoyal offers extensive possibilities in this regard, enabling users to target a region, country, state, or city and even a specific internet service provider (ISP) within that location. We will explore these options in greater detail in the subsequent paragraphs, focusing on the comprehensive location-targeting capabilities provided by IPRoyal within this section.

### Region

`_region-` is the key for region configuration. Adding this value will tell our router to filter proxies that are located in this region.&#x20;

Example:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_region-europe@geo.iproyal.com:12321 -L https://google.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_region-europe';
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
password = 'password321_region-europe'
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
const password = 'password321_region-europe';
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

<details>

<summary>Supported region values</summary>

* `africa`
* `arabstates`
* `asiapacific`
* `europe`
* `middleeast`
* `northamerica`
* `southlatinamerica`

</details>

### Country

`_country-` is the key for country configuration. The value of this parameter is a two letter country code ([ISO 3166-1 alpha-2 format](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)).

You can select more than one country. When resolving a proxy with this configuration, our router will randomly select one of the countries you had set as a value for the country key.

Examples:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-dk,it,ie@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_country-dk,it,ie';
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
password = 'password321_country-dk,it,ie'
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
const password = 'password321_country-dk,it,ie';
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

### City

`_city-` is the key to target a city. The value should be a name of the city.

{% hint style="warning" %}
Additionally, it's essential to specify the country when targeting a specific city, as multiple countries may have cities with the same name.
{% endhint %}

Example:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-de_city-berlin@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321';
$country = 'country-de';
$city = 'city-berlin';
$proxy = 'geo.iproyal.com:12321';
$url = 'http://example.com';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, "$username:$password");
$headers = [
    "X-Country: $country",
    "X-City: $city"
];
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
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
password = 'password321_country-de_city-berlin'
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
const password = 'password321_country-de_city-berlin';
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

### State

`_state-` is used to target a state in the **US**. The value should be the name of the state.

{% hint style="warning" %}
Be sure to select the **US** as a country.
{% endhint %}

Example:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-us_state-iowa@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_country-us_state-iowa';
$proxy = 'geo.iproyal.com:12321';
$url = 'http://example.com';

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_PROXY, $proxy);
curl_setopt($ch, CURLOPT_PROXYUSERPWD, "$username:$password");
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
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
password = 'password321_country-us_state-iowa'
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
const password = 'password321_country-us_state-iowa';
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

### ISP

{% hint style="info" %}
Available only with verified ID and after spending $1,000 or more.
{% endhint %}

`_isp-` is used to target a specific **ISP** (Internet service provider) in a location. The value should be a concatenated name of the provider.

{% hint style="warning" %}
Be sure to chain it to a city. A single ISP is often present in many cities or even countries.
{% endhint %}

Example:

{% tabs %}
{% tab title="cURL" %}

```
curl -v -x http://username123:password321_country-gb_city-birmingham_isp-skyuklimited@geo.iproyal.com:12321 -L http://example.com
```

{% endtab %}

{% tab title="PHP" %}

```php
<?php
$username = 'username123';
$password = 'password321_country-gb_city-birmingham_isp-skyuklimited';
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
password = 'password321_country-gb_city-birmingham_isp-skyuklimited'
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
const password = 'password321_country-gb_city-birmingham_isp-skyuklimited';
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
